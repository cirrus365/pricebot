"""
Matrix integration for Chatbot
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
    MatrixRoom,
    JoinResponse
)
from config.settings import (
    HOMESERVER, USERNAME, PASSWORD, BOT_USERNAME, ENABLE_MEME_GENERATION,
    ENABLE_PRICE_TRACKING, ENABLE_STOCK_MARKET, INTEGRATIONS, LLM_PROVIDER, OPENROUTER_MODEL,
    OLLAMA_MODEL, MAX_ROOM_HISTORY, MAX_CONTEXT_LOOKBACK, OLLAMA_KEEP_ALIVE
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
world_clock = None
price_tracker = None
settings_manager = None

def initialize_handlers():
    """Initialize handlers after module is loaded to avoid circular imports"""
    global message_callback, mark_event_processed, invite_callback, joined_rooms
    global cleanup_old_context, meme_generator, stats_tracker, stock_tracker, world_clock, price_tracker
    global settings_manager
    
    from modules.message_handler import message_callback as mc, mark_event_processed as mep
    from modules.invite_handler import invite_callback as ic, joined_rooms as jr
    from modules.cleanup import cleanup_old_context as coc
    from modules.meme_generator import meme_generator as mg
    from modules.stats_tracker import stats_tracker as st
    from modules.stock_tracker import stock_tracker as stk
    from modules.world_clock import world_clock as wc
    from modules.price_tracker import price_tracker as pt
    from modules.settings_manager import settings_manager as sm
    
    message_callback = mc
    mark_event_processed = mep
    invite_callback = ic
    joined_rooms = jr
    cleanup_old_context = coc
    meme_generator = mg
    stats_tracker = st
    stock_tracker = stk
    world_clock = wc
    price_tracker = pt
    settings_manager = sm

async def maintain_connection_health(client):
    """Maintain connection health and preload models"""
    last_activity = time.time()
    last_model_warm = time.time()
    
    while True:
        try:
            await asyncio.sleep(120)  # Check every 2 minutes
            current_time = time.time()
            time_since_activity = current_time - last_activity
            time_since_warm = current_time - last_model_warm
            
            # If no activity for 4 minutes, do a lightweight sync to keep connection alive
            if time_since_activity > 240:
                logger.debug("Performing keep-alive sync...")
                try:
                    sync_response = await client.sync(timeout=5000, full_state=False)
                    if sync_response:
                        last_activity = current_time
                        logger.debug("Keep-alive sync successful")
                except Exception as e:
                    logger.warning(f"Keep-alive sync failed: {e}")
                    # Try to recover connection
                    try:
                        await client.sync(timeout=10000, full_state=False)
                        last_activity = current_time
                    except:
                        logger.error("Failed to recover connection")
                    
            # For Ollama: Send a tiny request every 3 minutes to keep model warm
            if LLM_PROVIDER == "ollama" and time_since_warm > 180:  # 3 minutes
                logger.debug("Warming up Ollama model...")
                try:
                    from modules.llm import call_ollama_api
                    # Send minimal request to keep model loaded in memory
                    warm_messages = [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Reply with just 'ok'"}
                    ]
                    result = await call_ollama_api(warm_messages, temperature=0.1)
                    if result:
                        last_model_warm = current_time
                        logger.debug("Ollama model warmed up successfully")
                except Exception as e:
                    logger.debug(f"Ollama warm-up failed (non-critical): {e}")
                    
        except Exception as e:
            logger.error(f"Connection health monitor error: {e}")
            # Don't crash the monitor, just continue
            await asyncio.sleep(60)

async def process_message(client, room, event):
    """Process a message"""
    # Ignore own messages
    if event.sender == client.user_id:
        return
        
    # Mark command events as processed to prevent duplicate handling
    if event.body.strip().startswith('?'):
        mark_event_processed(event.event_id)
    
    # Check if it's a help command
    if event.body.strip() == '?help':
        await handle_help_command(client, room, event)
    # Check if it's a clock command
    elif event.body.startswith('?clock'):
        await handle_clock_command(client, room, event)
    # Check if it's a price command
    elif event.body.startswith('?price'):
        await handle_price_command(client, room, event)
    # Check if it's a meme command
    elif event.body.startswith('?meme'):
        await handle_meme_command(client, room, event)
    # Check if it's a stats command
    elif event.body.strip() == '?stats':
        await handle_stats_command(client, room, event)
    # Check if it's a stonks command
    elif event.body.startswith('?stonks'):
        await handle_stonks_command(client, room, event)
    # Check if it's a setting command
    elif event.body.startswith('?setting'):
        await handle_setting_command(client, room, event)
    else:
        await message_callback(client, room, event)

async def send_message(client, room_id: str, content: dict):
    """Send a message to a Matrix room"""
    try:
        response = await client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=content
        )
        
        if response:
            logger.debug(f"Message sent to room {room_id}")
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")

async def run_matrix_bot():
    """Run the Matrix bot"""
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
    
    # Set up client configuration
    config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        encryption_enabled=False,
    )
    
    # Create client
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
        
        async def wrapped_invite_callback(room, event):
            await invite_callback(client, room, event)
        
        # Add event callbacks
        client.add_event_callback(wrapped_message_callback, RoomMessageText)
        client.add_event_callback(wrapped_invite_callback, InviteMemberEvent)
        
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
        
        # Start connection health monitor
        asyncio.create_task(maintain_connection_health(client))
        
        print("=" * 50)
        print(f"🤖 {BOT_USERNAME.capitalize()} Bot - Matrix Integration Active!")
        print("=" * 50)
        print(f"✅ Identity: {USERNAME}")
        print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
        print(f"🔑 Device ID: {response.device_id}")
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
        print("🕐 Clock: ?clock <city/country> for world time")
        print("💰 Price: ?price <crypto> [currency] for crypto/fiat prices")
        print("📊 Stocks: ?stonks <ticker> for stock market data")
        print("⚙️ Settings: ?setting to manage bot configuration (authorized users only)")
        if settings_manager.is_meme_enabled():
            print("🎨 Meme generation: ?meme <topic> to create memes")
        else:
            print("🎨 Meme generation: DISABLED (enable with ?setting meme on)")
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
        print("🔌 Connection keepalive: Active monitoring to prevent timeouts")
        if LLM_PROVIDER == "ollama":
            print(f"🔥 Ollama model warming: Every 3 minutes (keep-alive: {OLLAMA_KEEP_ALIVE})")
        print("=" * 50)
        
        # Sync forever with longer timeout for better stability
        await client.sync_forever(
            timeout=60000,  # 60 seconds instead of 30
            full_state=False  # Don't request full state on every sync
        )
            
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
• `?setting` - Manage bot configuration (authorized users only)
• `{BOT_USERNAME} <message>` - Chat with me by mentioning my name
• Reply to any of my messages to continue the conversation
• `{BOT_USERNAME} !reset` - Clear conversation context for this room
• `{BOT_USERNAME} summary` - Get a comprehensive analysis of recent chat

**Time & Date:**
• `?clock <city/country>` - Get current time for a location
• `?clock` - Get current UTC time
• Examples: `?clock paris`, `?clock tokyo`, `?clock usa`

**Price & Finance:**
• `?price <crypto> [currency]` - Get cryptocurrency prices
• `?price <from_currency> <to_currency>` - Get fiat exchange rates
• Examples: `?price xmr usd`, `?price btc`, `?price usd aud`

**Stock Market:**
• `?stonks <ticker>` - Get detailed stock information
• `?stonks` - Get global market summary
• Examples: `?stonks AAPL`, `?stonks MSFT`, `?stonks TSLA`

**Settings Management (Authorized Users Only):**
• `?setting help` - Show settings help and available options
• `?setting list` - Display current settings values
• `?setting <name> <value>` - Update a setting

**Fun & Utility:**"""
        
        if settings_manager.is_meme_enabled():
            help_text += "\n• `?meme <topic>` - Generate a meme with AI-generated captions"
        
        help_text += f"""
• `{BOT_USERNAME} search <query>` - Search the web for current information

**Features:**
• 🔗 **URL Analysis** - Share any URL and I'll read and discuss it
• 📝 **Code Support** - I can help with programming questions and format code properly
• 👀 **Smart Reactions** - I'll react with emojis to certain keywords
• 🧠 **Context Aware** - I remember the last 100 messages in each room
• 🔍 **Auto Search** - I'll automatically search for current events when needed
• 📊 **Stock Market** - Real-time stock prices and market data
• 🕐 **World Clock** - Get time for any city or country
• ⚙️ **Live Settings** - Authorized users can update settings without restart

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

async def handle_clock_command(client, room, event):
    """Handle world clock command for Matrix"""
    try:
        # Track command usage
        stats_tracker.record_command_usage('?clock')
        stats_tracker.record_feature_usage('world_clock')
        
        # Send typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Parse the command
        parts = event.body.strip().split(maxsplit=1)
        location = parts[1] if len(parts) > 1 else ""
        
        # Get time for location
        response = await world_clock.handle_clock_command(location)
        
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
            }
        )
        
        # Track sent message
        stats_tracker.record_message_sent(room.room_id)
        
    except Exception as e:
        logger.error(f"Error handling clock command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't get the time for that location. Please try again."
            }
        )
    finally:
        await client.room_typing(room.room_id, typing_state=False)

async def handle_price_command(client, room, event):
    """Handle price command for Matrix"""
    try:
        # Check if price tracking is enabled using environment variable directly
        if not ENABLE_PRICE_TRACKING:
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": "Price tracking feature is not enabled. Please set ENABLE_PRICE_TRACKING=true in your .env file and restart the bot."
                }
            )
            return
        
        # Track command usage
        stats_tracker.record_command_usage('?price')
        stats_tracker.record_feature_usage('price_tracking')
        
        # Send typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Parse the command - remove the ?price prefix
        parts = event.body.strip().split(maxsplit=1)
        query = parts[1] if len(parts) > 1 else "XMR"  # Default to XMR if no argument
        
        # Get price response
        response = await price_tracker.get_price_response(query)
        
        if not response:
            # If the price tracker couldn't parse it, provide help
            response = """💰 **Price Command Usage**

**Cryptocurrency prices:**
• `?price btc` - Bitcoin in USD
• `?price xmr usd` - Monero in USD
• `?price eth eur` - Ethereum in EUR

**Fiat exchange rates:**
• `?price usd eur` - USD to EUR rate
• `?price 100 usd eur` - Convert 100 USD to EUR

**Supported cryptos:** BTC, ETH, XMR, LTC, DOGE, ADA, DOT, LINK, UNI, SOL, MATIC, AVAX, ATOM, XRP, BNB and more

**Supported fiats:** USD, EUR, GBP, JPY, CNY, INR, KRW, RUB, CAD, AUD, CHF, SEK, NOK, DKK, PLN, CZK, NZD, MXN, BRL, ZAR, HKD, SGD, THB, TRY and more"""
        
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
            }
        )
        
        # Track sent message
        stats_tracker.record_message_sent(room.room_id)
        
    except Exception as e:
        logger.error(f"Error handling price command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't fetch price data right now. Please try again later."
            }
        )
    finally:
        await client.room_typing(room.room_id, typing_state=False)

async def handle_meme_command(client, room, event):
    """Handle meme generation command for Matrix"""
    try:
        # Check if meme generation is enabled at runtime
        if not settings_manager.is_meme_enabled():
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": "Meme generation feature is not enabled. An authorized user can enable it with: ?setting meme on"
                }
            )
            return
        
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
        # Check if stock tracking is enabled using environment variable directly
        if not ENABLE_STOCK_MARKET:
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": "Stock tracking feature is not enabled. Please set ENABLE_STOCK_MARKET=true in your .env file and restart the bot."
                }
            )
            return
        
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

async def handle_setting_command(client, room, event):
    """Handle setting command for Matrix"""
    try:
        # Track command usage
        stats_tracker.record_command_usage('?setting')
        stats_tracker.record_feature_usage('settings_management')
        
        # Send typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Parse the command
        parts = event.body.strip().split(maxsplit=1)
        args = parts[1].split() if len(parts) > 1 else []
        
        # Get the user ID
        user_id = event.sender
        
        # Handle the setting command
        response = await settings_manager.handle_setting_command(args, user_id, 'matrix')
        
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
                                         .replace("`", "<code>").replace("`", "</code>")
            }
        )
        
        # Track sent message
        stats_tracker.record_message_sent(room.room_id)
        
    except Exception as e:
        logger.error(f"Error handling setting command: {e}")
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": "Sorry, I couldn't process the setting command. Please try again."
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
        else:
            features_list.append("❌ Price Tracking (disabled)")
        if settings_manager.is_meme_enabled():
            features_list.append("✅ Meme Generation")
        else:
            features_list.append("❌ Meme Generation (disabled)")
        if ENABLE_STOCK_MARKET:
            features_list.append("✅ Stock Market Data")
        else:
            features_list.append("❌ Stock Market Data (disabled)")
        features_list.append("✅ World Clock")
        features_list.append("✅ URL Analysis")
        if settings_manager.is_web_search_enabled():
            features_list.append("✅ Web Search")
        else:
            features_list.append("❌ Web Search (disabled)")
        features_list.append("✅ Code Formatting")
        features_list.append("✅ Emoji Reactions")
        features_list.append("✅ Settings Management")
        
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
            stats_text += f"\n• Keep-alive: {OLLAMA_KEEP_ALIVE}"
        
        # Add context configuration
        stats_text += f"\n\n**💾 Context Configuration:**"
        stats_text += f"\n• Room History: {MAX_ROOM_HISTORY} messages"
        stats_text += f"\n• Context Lookback: {MAX_CONTEXT_LOOKBACK} messages"
        
        # Add connection health status
        stats_text += f"\n\n**🔌 Connection Health:**"
        stats_text += f"\n• Keep-alive: Active (2-minute intervals)"
        if LLM_PROVIDER == "ollama":
            stats_text += f"\n• Model warming: Active (3-minute intervals)"

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
