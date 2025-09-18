"""
Matrix integration for Chatbot with E2EE support
"""
import asyncio
import logging
import time
import os
from pathlib import Path
from nio import (
    AsyncClient, 
    AsyncClientConfig,
    LoginResponse, 
    RoomMessageText, 
    InviteMemberEvent,
    MegolmEvent,
    EncryptionError,
    MatrixRoom,
    JoinResponse
)
from config.settings import (
    HOMESERVER, USERNAME, PASSWORD, BOT_USERNAME, ENABLE_MEME_GENERATION,
    ENABLE_PRICE_TRACKING, INTEGRATIONS, LLM_PROVIDER, OPENROUTER_MODEL,
    OLLAMA_MODEL, MAX_ROOM_HISTORY, MAX_CONTEXT_LOOKBACK, ENABLE_MATRIX_E2EE,
    MATRIX_STORE_PATH
)

logger = logging.getLogger(__name__)

# Global variables to store callbacks - will be imported later to avoid circular imports
message_callback = None
mark_event_processed = None
invite_callback = None
joined_rooms = None
cleanup_old_context = None
meme_generator = None
stats_tracker = None
stock_tracker = None

def initialize_handlers():
    """Initialize handlers after module is loaded to avoid circular imports"""
    global message_callback, mark_event_processed, invite_callback, joined_rooms
    global cleanup_old_context, meme_generator, stats_tracker, stock_tracker
    
    from modules.message_handler import message_callback as mc, mark_event_processed as mep
    from modules.invite_handler import invite_callback as ic, joined_rooms as jr
    from modules.cleanup import cleanup_old_context as coc
    from modules.meme_generator import meme_generator as mg
    from modules.stats_tracker import stats_tracker as st
    from modules.stock_tracker import stock_tracker as stk
    
    message_callback = mc
    mark_event_processed = mep
    invite_callback = ic
    joined_rooms = jr
    cleanup_old_context = coc
    meme_generator = mg
    stats_tracker = st
    stock_tracker = stk

async def handle_encrypted_message(client, room: MatrixRoom, event):
    """Handle encrypted messages when E2EE is enabled"""
    try:
        # Check if it's an encryption error
        if isinstance(event, EncryptionError):
            logger.warning(f"Failed to decrypt message in {room.room_id}: {event.description}")
            return
        
        # For MegolmEvent, the decrypted content is in the source attribute
        if hasattr(event, 'source') and event.source.get("content", {}).get("msgtype") == "m.text":
            body = event.source["content"].get("body", "")
            
            # Ignore own messages
            if event.sender == client.user_id:
                return
            
            # Create a pseudo RoomMessageText event with the decrypted content
            class DecryptedMessage:
                def __init__(self, event_id, sender, body, server_timestamp):
                    self.event_id = event_id
                    self.sender = sender
                    self.body = body
                    self.server_timestamp = server_timestamp
                    self.source = event.source
            
            decrypted_msg = DecryptedMessage(
                event_id=event.event_id,
                sender=event.sender,
                body=body,
                server_timestamp=event.server_timestamp
            )
            
            logger.debug(f"Received encrypted message from {event.sender}: {body}")
            
            # Process the decrypted message
            await process_message(client, room, decrypted_msg)
            
    except Exception as e:
        logger.error(f"Error handling encrypted message: {e}")

async def process_message(client, room, event):
    """Process a message (encrypted or unencrypted)"""
    # Ignore own messages
    if event.sender == client.user_id:
        return
        
    # Mark command events as processed to prevent duplicate handling
    if event.body.strip().startswith('?'):
        mark_event_processed(event.event_id)
    
    # Check if it's a help command
    if event.body.strip() == '?help':
        await handle_help_command(client, room, event)
    # Check if it's a meme command
    elif event.body.startswith('?meme ') and ENABLE_MEME_GENERATION:
        await handle_meme_command(client, room, event)
    # Check if it's a stats command
    elif event.body.strip() == '?stats':
        await handle_stats_command(client, room, event)
    # Check if it's a stonks command
    elif event.body.startswith('?stonks'):
        await handle_stonks_command(client, room, event)
    else:
        await message_callback(client, room, event)

async def send_message(client, room_id: str, content: dict):
    """Send a message to a Matrix room with E2EE support"""
    try:
        # Always use ignore_unverified_devices when E2EE is enabled
        response = await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=content,
            ignore_unverified_devices=True  # This is the key parameter
        )
        
        if response:
            logger.debug(f"Message sent to room {room_id}")
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # If first attempt fails, try again with more aggressive settings
        if "not verified" in str(e).lower() or "blacklisted" in str(e).lower():
            try:
                logger.info("Retrying with ignore_unverified_devices=True")
                response = await client.room_send(
                    room_id=room_id,
                    message_type="m.room.message",
                    content=content,
                    ignore_unverified_devices=True
                )
            except Exception as retry_error:
                logger.error(f"Retry failed: {retry_error}")

async def run_matrix_bot():
    """Run the Matrix bot with optional E2EE support"""
    # Initialize handlers first
    initialize_handlers()
    
    # Check for required Matrix credentials
    if not all([HOMESERVER, USERNAME, PASSWORD]):
        logger.error("Matrix credentials not configured. Please set MATRIX_HOMESERVER, MATRIX_USERNAME, and MATRIX_PASSWORD in .env file")
        print("\n❌ ERROR: Matrix credentials missing!")
        print("Please configure the following in your .env file:")
        print("  - MATRIX_HOMESERVER")
        print("  - MATRIX_USERNAME")
        print("  - MATRIX_PASSWORD")
        return
    
    # Set up store path for E2EE if enabled
    store_path = None
    config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        encryption_enabled=ENABLE_MATRIX_E2EE,
    )
    
    if ENABLE_MATRIX_E2EE:
        store_path = Path(MATRIX_STORE_PATH).absolute()
        store_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"E2EE enabled, using store path: {store_path}")
        
        # Check if libolm is installed
        try:
            import olm
            logger.info("libolm is installed and available")
        except ImportError:
            logger.error("E2EE is enabled but libolm is not installed!")
            print("\n❌ ERROR: E2EE requires libolm to be installed!")
            print("Please install it using:")
            print("  Ubuntu/Debian: sudo apt-get install libolm-dev")
            print("  Fedora: sudo dnf install libolm-devel")
            print("  macOS: brew install libolm")
            print("  Then: pip install 'matrix-nio[e2e]'")
            return
    
    # Create client with appropriate configuration
    if ENABLE_MATRIX_E2EE:
        client = AsyncClient(
            HOMESERVER, 
            USERNAME,
            store_path=str(store_path),
            config=config
        )
        # Set to ignore unverified devices globally
        client.trust_unverified_devices = True
    else:
        client = AsyncClient(
            HOMESERVER, 
            USERNAME,
            config=config
        )
    
    try:
        # Login
        response = await client.login(PASSWORD, device_name=f"{BOT_USERNAME}-bot")
        if not isinstance(response, LoginResponse):
            logger.error(f"Failed to login to Matrix: {response}")
            return
        
        logger.info(f"Matrix: Logged in as {client.user_id} with device {response.device_id}")
        
        # Setup E2EE if enabled
        if ENABLE_MATRIX_E2EE:
            # Set the client to trust unverified devices
            client.trust_unverified_devices = True
            
            # Upload keys if needed
            if client.should_upload_keys:
                await client.keys_upload()
                logger.info("E2EE: Keys uploaded")
            
            # Do an initial sync to get device lists and rooms
            await client.sync(timeout=30000, full_state=True)
            logger.info("E2EE: Initial sync complete")
            
            # Trust all devices (for bot operation)
            logger.info("E2EE: Configured to ignore unverified devices for bot operation")
        
        # Get list of joined rooms
        logger.info("Matrix: Getting list of joined rooms...")
        joined_rooms_response = await client.joined_rooms()
        if hasattr(joined_rooms_response, 'rooms'):
            for room_id in joined_rooms_response.rooms:
                joined_rooms.add(room_id)
                stats_tracker.record_room_join(room_id)
                logger.info(f"Matrix: Already in room: {room_id}")
        
        # Create wrapped callbacks that include the client
        async def wrapped_message_callback(room, event):
            # Ignore own messages
            if event.sender == client.user_id:
                return
            await process_message(client, room, event)
        
        async def wrapped_encrypted_callback(room, event):
            await handle_encrypted_message(client, room, event)
        
        async def wrapped_invite_callback(room, event):
            await invite_callback(client, room, event)
        
        # Add event callbacks
        client.add_event_callback(wrapped_message_callback, RoomMessageText)
        client.add_event_callback(wrapped_invite_callback, InviteMemberEvent)
        
        # Add encrypted message callbacks if E2EE is enabled
        if ENABLE_MATRIX_E2EE:
            client.add_event_callback(wrapped_encrypted_callback, MegolmEvent)
            client.add_event_callback(wrapped_encrypted_callback, EncryptionError)
            logger.info("E2EE: Encrypted message handlers registered")
        
        # Do an initial sync to get the latest state
        logger.info("Matrix: Performing initial sync...")
        sync_filter = {
            "room": {
                "timeline": {
                    "limit": 1  # Only get the most recent message per room on startup
                }
            }
        }
        sync_response = await client.sync(timeout=30000, full_state=True, sync_filter=sync_filter)
        logger.info(f"Matrix: Initial sync completed. Next batch: {sync_response.next_batch}")
        
        # Mark all messages from initial sync as processed to avoid responding to old messages
        if hasattr(sync_response, 'rooms') and hasattr(sync_response.rooms, 'join'):
            for room_id, room_data in sync_response.rooms.join.items():
                if hasattr(room_data, 'timeline') and hasattr(room_data.timeline, 'events'):
                    for event in room_data.timeline.events:
                        if hasattr(event, 'event_id'):
                            mark_event_processed(event.event_id)
                            logger.debug(f"Marked initial sync event as processed: {event.event_id}")
        
        # Start cleanup task
        asyncio.create_task(cleanup_old_context())
        
        print("=" * 50)
        print(f"🤖 {BOT_USERNAME.capitalize()} Bot - Matrix Integration Active!")
        print("=" * 50)
        print(f"✅ Identity: {USERNAME}")
        print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
        if ENABLE_MATRIX_E2EE:
            print("🔐 E2EE: ENABLED - Supporting encrypted rooms")
            print(f"🔑 Store Path: {store_path}")
            print(f"🔑 Device ID: {response.device_id}")
            print("✅ Auto-ignoring unverified devices for bot operation")
        else:
            print("🔓 E2EE: DISABLED - Only unencrypted rooms supported")
        print("✅ Listening for messages in all joined rooms")
        print("✅ Auto-accepting room invites")
        print(f"📝 Trigger: Say '{BOT_USERNAME}' anywhere in a message")
        print("💬 Or reply directly to any of my messages")
        print("❌ Random responses: DISABLED")
        print("👀 Emoji reactions: ENABLED (various triggers)")
        print(f"🧹 Reset: '{BOT_USERNAME} !reset' to clear context")
        print(f"📊 Summary: '{BOT_USERNAME} summary' for comprehensive chat analysis")
        print("📚 Help: ?help to see all available commands")
        print("📈 Stats: ?stats to see bot statistics")
        print("💰 Price: ?price <crypto> [currency] for crypto/fiat prices")
        print("📊 Stocks: ?stonks <ticker> for stock market data")
        if ENABLE_MEME_GENERATION:
            print("🎨 Meme generation: ?meme <topic> to create memes")
        print("🧠 Optimized Context: Tracking 100 messages (reduced for performance)")
        print("📈 Context Features: Topic tracking, user expertise, important messages")
        print("💻 Technical expertise: Programming, Linux, Security, etc.")
        print("🔗 URL Analysis: Share URLs and I'll read and discuss them!")
        print("📝 Code Formatting: Proper syntax highlighting for all languages")
        print("🔍 Web search: Powered by Jina.ai - Smart detection for current info")
        print("🎯 Personality: Professional, helpful, witty, context-aware")
        print("⏱️ Timeouts: 30s for LLM, 15s for search, 20s for URL fetching")
        print("🔄 Retry logic: 3 attempts with exponential backoff")
        print("🧹 Auto-cleanup: Hourly context cleanup to maintain performance")
        print("📉 Reduced context: Optimized for faster response times")
        print("🔁 Duplicate prevention: Won't respond to old messages on restart")
        print("=" * 50)
        
        # Sync forever
        await client.sync_forever(timeout=30000, full_state=True)
            
    except Exception as e:
        logger.error(f"Matrix bot error: {e}")
        raise
    finally:
        await client.close()

async def handle_help_command(client, room, event):
    """Handle help command for Matrix"""
    try:
        # Track command usage
        stats_tracker.record_command_usage('?help')
        
        # Build help message
        help_text = f"""📚 **{BOT_USERNAME.capitalize()} Bot - Available Commands**

**General Commands:**
• `?help` - Show this help message
• `?stats` - Show bot statistics and enabled features
• `{BOT_USERNAME} <message>` - Chat with me by mentioning my name
• Reply to any of my messages to continue the conversation
• `{BOT_USERNAME} !reset` - Clear conversation context for this room
• `{BOT_USERNAME} summary` - Get a comprehensive analysis of recent chat

**Price & Finance:**
• `?price <crypto> [currency]` - Get cryptocurrency prices
• `?price <from_currency> <to_currency>` - Get fiat exchange rates
• Examples: `?price xmr usd`, `?price btc`, `?price usd aud`

**Stock Market:**
• `?stonks <ticker>` - Get detailed stock information
• `?stonks` - Get global market summary
• Examples: `?stonks AAPL`, `?stonks MSFT`, `?stonks TSLA`

**Fun & Utility:**"""
        
        if ENABLE_MEME_GENERATION:
            help_text += "\n• `?meme <topic>` - Generate a meme with AI-generated captions"
        
        help_text += f"""
• `{BOT_USERNAME} search <query>` - Search the web for current information

**Features:**
• 🔗 **URL Analysis** - Share any URL and I'll read and discuss it
• 📝 **Code Support** - I can help with programming questions and format code properly
• 👀 **Smart Reactions** - I'll react with emojis to certain keywords
• 🧠 **Context Aware** - I remember the last 100 messages in each room
• 🔍 **Auto Search** - I'll automatically search for current events when needed
• 📊 **Stock Market** - Real-time stock prices and market data"""

        if ENABLE_MATRIX_E2EE:
            help_text += "\n• 🔐 **E2EE Support** - I work in both encrypted and unencrypted rooms"

        help_text += """

**Tips:**
• I'm particularly knowledgeable about programming, Linux, security, and privacy
• I can analyze technical documentation and help with coding problems
• Share URLs to articles or documentation for me to analyze
• I maintain conversation context and can reference earlier messages

Need more help? Just ask me anything!"""

        # Send help message with formatting
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": help_text.replace("**", "").replace("•", "-"),  # Plain text fallback
                "format": "org.matrix.custom.html",
                "formatted_body": help_text.replace("**", "<strong>").replace("**", "</strong>")
                                           .replace("•", "•")
                                           .replace("\n", "<br/>")
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling help command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't display the help message. Please try again."
            }
        )

async def handle_meme_command(client, room, event):
    """Handle meme generation command for Matrix"""
    try:
        # Track command usage
        stats_tracker.record_command_usage('?meme')
        stats_tracker.record_feature_usage('meme_generation')
        
        # Send typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Generate meme - change the command prefix from ! to ?
        meme_input = event.body.replace('?meme', '!meme', 1)
        meme_url, caption = await meme_generator.handle_meme_command(meme_input)
        
        if meme_url:
            # Send the message with both caption and URL
            formatted_body = f"{caption}\n{meme_url}"
            
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": formatted_body,
                    "format": "org.matrix.custom.html",
                    "formatted_body": f'<p>{caption}</p><p><a href="{meme_url}">{meme_url}</a></p>'
                }
            )
            
            # Track sent message
            stats_tracker.record_message_sent(room.room_id)
        else:
            # Send error message
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": caption or "Failed to generate meme"
                }
            )
            
    except Exception as e:
        logger.error(f"Error handling meme command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't create a meme right now. Please try again later."
            }
        )
    finally:
        await client.room_typing(room.room_id, typing_state=False)

async def handle_stonks_command(client, room, event):
    """Handle stock market command for Matrix"""
    try:
        # Track command usage
        stats_tracker.record_command_usage('?stonks')
        stats_tracker.record_feature_usage('stock_tracking')
        
        # Send typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Parse the command
        parts = event.body.strip().split()
        
        if len(parts) == 1:
            # No ticker provided, show market summary
            response = await stock_tracker.get_market_summary()
        else:
            # Get stock info for the provided ticker
            ticker = parts[1]
            response = await stock_tracker.get_stock_info(ticker)
        
        # Send the response with formatting
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": response.replace("**", "").replace("•", "-"),  # Plain text fallback
                "format": "org.matrix.custom.html",
                "formatted_body": response.replace("**", "<strong>").replace("**", "</strong>")
                                         .replace("•", "•")
                                         .replace("\n", "<br/>")
                                         .replace("_", "<em>").replace("_", "</em>")
            }
        )
        
        # Track sent message
        stats_tracker.record_message_sent(room.room_id)
        
    except Exception as e:
        logger.error(f"Error handling stonks command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't fetch stock data right now. Please try again later."
            }
        )
    finally:
        await client.room_typing(room.room_id, typing_state=False)

async def handle_stats_command(client, room, event):
    """Handle stats command for Matrix"""
    try:
        # Track command usage
        stats_tracker.record_command_usage('?stats')
        
        # Get statistics
        uptime = stats_tracker.get_uptime()
        daily_stats = stats_tracker.get_daily_stats()
        hourly_dist = stats_tracker.get_hourly_distribution()
        active_rooms = stats_tracker.get_most_active_rooms(3)
        command_stats = stats_tracker.get_command_stats()
        feature_stats = stats_tracker.get_feature_stats()
        
        # Build stats message
        stats_text = f"""📊 **{BOT_USERNAME.capitalize()} Bot Statistics**

**🕐 Uptime:** {uptime}

**📈 Activity (Last 24 Hours):**
• Messages Received: {daily_stats['messages_received']}
• Messages Sent: {daily_stats['messages_sent']}
• Active Rooms: {daily_stats['active_rooms']}/{daily_stats['total_rooms']}

**🏠 Room Participation:**
• Total Rooms: {len(stats_tracker.active_rooms)}
• Total Messages Processed: {stats_tracker.total_messages_processed}
• Total Messages Sent: {stats_tracker.total_messages_sent}"""

        if active_rooms:
            stats_text += "\n\n**🔥 Most Active Rooms:**"
            for i, (room_id, count) in enumerate(active_rooms, 1):
                # Truncate room ID for display
                display_id = room_id[:30] + "..." if len(room_id) > 30 else room_id
                stats_text += f"\n{i}. {display_id}: {count} messages"

        if hourly_dist:
            stats_text += "\n\n**⏰ Peak Activity Hours (UTC):**"
            for hour, count in hourly_dist[:3]:
                stats_text += f"\n• {hour:02d}:00 - {count} messages"

        if command_stats:
            stats_text += "\n\n**🎮 Command Usage:**"
            for cmd, count in sorted(command_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                stats_text += f"\n• {cmd}: {count} times"

        if feature_stats:
            stats_text += "\n\n**✨ Feature Usage:**"
            for feature, count in sorted(feature_stats.items(), key=lambda x: x[1], reverse=True):
                feature_name = feature.replace('_', ' ').title()
                stats_text += f"\n• {feature_name}: {count} times"

        # Add enabled integrations
        stats_text += "\n\n**🔌 Enabled Integrations:**"
        integrations_list = []
        
        # Check which integrations are enabled
        if INTEGRATIONS.get('matrix', False):
            integrations_list.append("✅ Matrix")
        if INTEGRATIONS.get('discord', False):
            integrations_list.append("✅ Discord")
        if INTEGRATIONS.get('telegram', False):
            integrations_list.append("✅ Telegram")
        if INTEGRATIONS.get('whatsapp', False):
            integrations_list.append("✅ WhatsApp")
        if INTEGRATIONS.get('messenger', False):
            integrations_list.append("✅ Messenger")
        if INTEGRATIONS.get('instagram', False):
            integrations_list.append("✅ Instagram")
        
        for integration in integrations_list:
            stats_text += f"\n• {integration}"

        # Add enabled features
        stats_text += "\n\n**🎯 Enabled Features:**"
        features_list = []
        
        if ENABLE_PRICE_TRACKING:
            features_list.append("✅ Price Tracking")
        if ENABLE_MEME_GENERATION:
            features_list.append("✅ Meme Generation")
        if ENABLE_MATRIX_E2EE:
            features_list.append("✅ E2EE Support")
        features_list.append("✅ Stock Market Data")
        features_list.append("✅ URL Analysis")
        features_list.append("✅ Web Search")
        features_list.append("✅ Code Formatting")
        features_list.append("✅ Emoji Reactions")
        
        for feature in features_list:
            stats_text += f"\n• {feature}"

        # Add LLM configuration
        stats_text += "\n\n**🧠 LLM Configuration:**"
        stats_text += f"\n• Provider: {LLM_PROVIDER.upper()}"
        if LLM_PROVIDER == "openrouter":
            model_name = OPENROUTER_MODEL.split('/')[-1] if '/' in OPENROUTER_MODEL else OPENROUTER_MODEL
            stats_text += f"\n• Model: {model_name}"
        elif LLM_PROVIDER == "ollama":
            stats_text += f"\n• Model: {OLLAMA_MODEL}"
        
        # Add context configuration
        stats_text += f"\n\n**💾 Context Configuration:**"
        stats_text += f"\n• Room History: {MAX_ROOM_HISTORY} messages"
        stats_text += f"\n• Context Lookback: {MAX_CONTEXT_LOOKBACK} messages"
        
        # Add E2EE status
        if ENABLE_MATRIX_E2EE:
            stats_text += f"\n\n**🔐 Encryption Status:**"
            stats_text += f"\n• E2EE: Enabled"
            stats_text += f"\n• Store Path: {MATRIX_STORE_PATH}"
            stats_text += f"\n• Device Status: Auto-ignoring unverified devices"

        # Send stats message with formatting
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": stats_text.replace("**", "").replace("•", "-"),  # Plain text fallback
                "format": "org.matrix.custom.html",
                "formatted_body": stats_text.replace("**", "<strong>").replace("**", "</strong>")
                                           .replace("•", "•")
                                           .replace("\n", "<br/>")
            }
        )
        
        # Track sent message
        stats_tracker.record_message_sent(room.room_id)
        
    except Exception as e:
        logger.error(f"Error handling stats command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't display the statistics. Please try again."
            }
        )
