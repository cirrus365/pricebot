"""
Matrix integration for Price Tracker & World Clock Bot
"""
import asyncio
import logging
import time
from pathlib import Path
from nio import (
    AsyncClient, 
    AsyncClientConfig,
    LoginResponse, 
    RoomMessageText, 
    MatrixRoom
)
from config.settings import (
    HOMESERVER, USERNAME, PASSWORD, BOT_USERNAME,
    ENABLE_PRICE_TRACKING, ENABLE_STOCK_MARKET,
    MATRIX_SYNC_TIMEOUT, MATRIX_REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

# Track processed events to avoid duplicates
processed_events = set()
bot_start_time = time.time()

# Import price, stock trackers, and world clock
price_tracker = None
stock_tracker = None
world_clock = None

def initialize_handlers():
    """Initialize handlers after module is loaded to avoid circular imports"""
    global price_tracker, stock_tracker, world_clock
    
    from modules.price_tracker import price_tracker as pt
    from modules.stock_tracker import stock_tracker as stk
    from modules.world_clock import world_clock as wc
    
    price_tracker = pt
    stock_tracker = stk
    world_clock = wc

def mark_event_processed(event_id):
    """Mark an event as processed"""
    processed_events.add(event_id)

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

async def handle_help_command(client, room, event):
    """Handle help command for Matrix"""
    try:
        help_text = f"""📚 **Price Tracker & World Clock Bot - Available Commands**

**Price Commands:**
• `?price <crypto>` - Get cryptocurrency price (default: USD)
• `?price <crypto> <currency>` - Get crypto price in specific currency
• `?price <from> <to>` - Get exchange rate between currencies
• `?xmr` - Quick Monero price check

**Stock Commands:**
• `?stonks <ticker>` - Get stock information
• `?stonks` - Get market summary

**World Clock:**
• `?clock <city/country>` - Get current time for a location
• `?clock` - Show current UTC time

**Other Commands:**
• `?help` - Show this help message

Examples:
• `?price btc` - Bitcoin price in USD
• `?price eth eur` - Ethereum price in EUR
• `?price usd aud` - USD to AUD exchange rate
• `?stonks AAPL` - Apple stock info
• `?clock paris` - Current time in Paris
• `?clock tokyo, new york` - Multiple locations"""

        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": help_text.replace("**", ""),
                "format": "org.matrix.custom.html",
                "formatted_body": help_text.replace("**", "<strong>").replace("**", "</strong>")
                                           .replace("\n", "<br/>")
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling help command: {e}")

async def handle_price_command(client, room, event):
    """Handle price command for Matrix"""
    try:
        if not ENABLE_PRICE_TRACKING:
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": "Price tracking is disabled."
                }
            )
            return
        
        parts = event.body.strip().split(maxsplit=1)
        query = parts[1] if len(parts) > 1 else "XMR"
        
        response = await price_tracker.get_price_response(f"price {query}")
        
        if not response:
            response = "Usage: ?price <crypto> [currency] or ?price <from> <to>"
        
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": response.replace("**", ""),
                "format": "org.matrix.custom.html",
                "formatted_body": response.replace("**", "<strong>").replace("**", "</strong>")
                                         .replace("\n", "<br/>")
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling price command: {e}")

async def handle_xmr_command(client, room, event):
    """Handle XMR price command for Matrix"""
    try:
        if not ENABLE_PRICE_TRACKING:
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": "Price tracking is disabled."
                }
            )
            return
        
        response = await price_tracker.get_price_response("price XMR")
        
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": response.replace("**", ""),
                "format": "org.matrix.custom.html",
                "formatted_body": response.replace("**", "<strong>").replace("**", "</strong>")
                                         .replace("\n", "<br/>")
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling XMR command: {e}")

async def handle_stonks_command(client, room, event):
    """Handle stock market command for Matrix"""
    try:
        if not ENABLE_STOCK_MARKET:
            await send_message(
                client,
                room.room_id,
                {
                    "msgtype": "m.text",
                    "body": "Stock tracking is disabled."
                }
            )
            return
        
        parts = event.body.strip().split()
        
        if len(parts) == 1:
            response = await stock_tracker.get_market_summary()
        else:
            ticker = parts[1]
            response = await stock_tracker.get_stock_info(ticker)
        
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": response.replace("**", ""),
                "format": "org.matrix.custom.html",
                "formatted_body": response.replace("**", "<strong>").replace("**", "</strong>")
                                         .replace("\n", "<br/>")
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling stonks command: {e}")

async def handle_clock_command(client, room, event):
    """Handle world clock command for Matrix"""
    try:
        parts = event.body.strip().split(maxsplit=1)
        query = parts[1] if len(parts) > 1 else ""
        
        response = await world_clock.handle_clock_command(query)
        
        await send_message(
            client,
            room.room_id,
            {
                "msgtype": "m.text",
                "body": response.replace("**", ""),
                "format": "org.matrix.custom.html",
                "formatted_body": response.replace("**", "<strong>").replace("**", "</strong>")
                                         .replace("\n", "<br/>")
            }
        )
        
    except Exception as e:
        logger.error(f"Error handling clock command: {e}")

async def message_callback(client, room: MatrixRoom, event: RoomMessageText):
    """Handle incoming messages"""
    
    # Check if already processed
    if event.event_id in processed_events:
        return
    
    # Check if message is from before bot started
    message_timestamp = event.server_timestamp / 1000 if event.server_timestamp else time.time()
    if message_timestamp < (bot_start_time - 5):
        mark_event_processed(event.event_id)
        return
    
    # Mark as processed
    mark_event_processed(event.event_id)
    
    # Ignore our own messages
    if event.sender == client.user_id:
        return
    
    # Check if message starts with ? for commands
    if event.body.strip().startswith('?'):
        command_parts = event.body.strip().split()
        command = command_parts[0].lower()
        
        # Handle commands
        if command == '?help':
            await handle_help_command(client, room, event)
        elif command == '?price':
            await handle_price_command(client, room, event)
        elif command == '?xmr':
            await handle_xmr_command(client, room, event)
        elif command == '?stonks':
            await handle_stonks_command(client, room, event)
        elif command == '?clock':
            await handle_clock_command(client, room, event)

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
        request_timeout=MATRIX_REQUEST_TIMEOUT,
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
        
        # Add event callbacks
        client.add_event_callback(lambda room, event: asyncio.create_task(message_callback(client, room, event)), RoomMessageText)
        
        # Do initial sync
        logger.info("Matrix: Performing initial sync...")
        sync_filter = {
            "room": {
                "timeline": {
                    "limit": 1  # Only get the most recent message per room
                }
            }
        }
        sync_response = await client.sync(timeout=MATRIX_SYNC_TIMEOUT, full_state=False, sync_filter=sync_filter)
        logger.info(f"Matrix: Initial sync completed. Next batch: {sync_response.next_batch}")
        
        # Mark all messages from initial sync as processed
        if hasattr(sync_response, 'rooms') and hasattr(sync_response.rooms, 'join'):
            for room_id, room_data in sync_response.rooms.join.items():
                if hasattr(room_data, 'timeline') and hasattr(room_data.timeline, 'events'):
                    for event in room_data.timeline.events:
                        if hasattr(event, 'event_id'):
                            mark_event_processed(event.event_id)
        
        print("=" * 50)
        print(f"💰 Price Tracker & World Clock Bot - Matrix Integration Active!")
        print("=" * 50)
        print(f"✅ Identity: {USERNAME}")
        print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
        print(f"🔑 Device ID: {response.device_id}")
        print("✅ Listening for commands in all joined rooms")
        print("📚 Commands:")
        print("  ?help - Show available commands")
        print("  ?price <crypto> [currency] - Get crypto/fiat prices")
        print("  ?xmr - Quick Monero price check")
        print("  ?stonks <ticker> - Get stock market data")
        print("  ?clock <location> - Get time for a location")
        print("=" * 50)
        
        # Sync forever
        await client.sync_forever(
            timeout=MATRIX_SYNC_TIMEOUT,
            full_state=False,
            since=sync_response.next_batch
        )
            
    except Exception as e:
        logger.error(f"Matrix bot error: {e}")
        raise
    finally:
        await client.close()
