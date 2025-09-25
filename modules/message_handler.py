"""Message handling for Matrix price commands"""
import logging
import time
from nio import MatrixRoom, RoomMessageText
from config.settings import BOT_USERNAME, ENABLE_PRICE_TRACKING, ENABLE_STOCK_MARKET

logger = logging.getLogger(__name__)

# Track processed events to avoid duplicates
processed_events = set()
bot_start_time = time.time()

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

async def message_callback(client, room: MatrixRoom, event: RoomMessageText):
    """Handle incoming messages for price commands"""
    
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
        
        # Import command handlers
        from integrations.matrix_integration import (
            handle_help_command, handle_price_command, handle_xmr_command, handle_stonks_command
        )
        
        # Handle commands
        if command == '?help':
            await handle_help_command(client, room, event)
        elif command == '?price':
            await handle_price_command(client, room, event)
        elif command == '?xmr':
            await handle_xmr_command(client, room, event)
        elif command == '?stonks':
            await handle_stonks_command(client, room, event)
