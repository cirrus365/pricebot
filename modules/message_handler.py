"""Message handling and processing"""
import re
import html
import time
import json
import os
from datetime import datetime
from asyncio import Queue, QueueFull
from nio import MatrixRoom, RoomMessageText
from config.settings import KNOWN_BOTS, MAX_QUEUE_SIZE, FILTERED_WORDS, ENABLE_PRICE_TRACKING, BOT_USERNAME
from utils.helpers import extract_urls_from_message, filter_bot_triggers
from utils.formatting import extract_code_from_response
from modules.context import room_message_history, conversation_context
from modules.reactions import maybe_react
from modules.web_search import fetch_url_content
from modules.llm import get_llm_reply_with_retry
from modules.price_tracker import price_tracker
from modules.stock_tracker import stock_tracker
from modules.stats_tracker import stats_tracker

# Create a request queue to prevent overload
request_queue = Queue(maxsize=MAX_QUEUE_SIZE)

# Track processed events to avoid duplicates
PROCESSED_EVENTS_FILE = ".processed_events.json"
processed_events = set()
bot_start_time = time.time()

def load_processed_events():
    """Load processed event IDs from file"""
    global processed_events
    if os.path.exists(PROCESSED_EVENTS_FILE):
        try:
            with open(PROCESSED_EVENTS_FILE, 'r') as f:
                data = json.load(f)
                # Only keep events from the last 24 hours to prevent file from growing too large
                current_time = time.time()
                processed_events = set(
                    event_id for event_id, timestamp in data.items()
                    if current_time - timestamp < 86400  # 24 hours
                )
                save_processed_events()  # Clean up old entries
        except Exception as e:
            print(f"[WARNING] Could not load processed events: {e}")
            processed_events = set()

def save_processed_events():
    """Save processed event IDs to file"""
    try:
        current_time = time.time()
        # Convert set to dict with timestamps, only keeping recent events
        events_dict = {}
        for event_id in processed_events:
            events_dict[event_id] = current_time
        
        # Also load existing file to preserve timestamps
        if os.path.exists(PROCESSED_EVENTS_FILE):
            try:
                with open(PROCESSED_EVENTS_FILE, 'r') as f:
                    existing = json.load(f)
                    # Merge, keeping existing timestamps where available
                    for event_id, timestamp in existing.items():
                        if event_id in processed_events and current_time - timestamp < 86400:
                            events_dict[event_id] = timestamp
            except:
                pass
        
        # Save to file
        with open(PROCESSED_EVENTS_FILE, 'w') as f:
            json.dump(events_dict, f)
    except Exception as e:
        print(f"[WARNING] Could not save processed events: {e}")

def mark_event_processed(event_id):
    """Mark an event as processed"""
    processed_events.add(event_id)
    save_processed_events()

# Load processed events on module import
load_processed_events()

async def get_replied_to_event(client, room_id, reply_to_event_id):
    """Fetch the event that was replied to"""
    try:
        response = await client.room_get_event(room_id, reply_to_event_id)
        return response
    except Exception as e:
        print(f"Error fetching replied-to event: {e}")
        return None

async def send_formatted_message(client, room_id, reply_text):
    """Send a message with proper code formatting"""
    # Extract code blocks and text parts
    message_parts = extract_code_from_response(reply_text)
    
    # Build formatted body
    formatted_body = ""
    plain_body = ""
    
    for part in message_parts:
        if part['type'] == 'text':
            # Format text with inline code support
            text = part['content']
            formatted_text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
            # Handle bold formatting
            formatted_text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', formatted_text)
            formatted_body += f"<p>{formatted_text}</p>"
            plain_body += text + "\n\n"
            
        elif part['type'] == 'code':
            language = part['language']
            code = html.escape(part['content'])
            
            # Add language label if specified
            if language and language != 'text':
                formatted_body += f"<p><strong>{language}:</strong></p>"
                plain_body += f"{language}:\n"
            
            formatted_body += f'<pre><code class="language-{language}">{code}</code></pre>'
            plain_body += f"```{language}\n{part['content']}\n```\n\n"
    
    # Send formatted message
    content = {
        "msgtype": "m.text",
        "body": plain_body.strip(),
        "format": "org.matrix.custom.html",
        "formatted_body": formatted_body.strip()
    }
    
    result = await client.room_send(
        room_id=room_id,
        message_type="m.room.message",
        content=content
    )
    
    # Track sent message
    stats_tracker.record_message_sent(room_id)
    
    return result

async def message_callback(client, room: MatrixRoom, event: RoomMessageText):
    """Handle incoming messages"""
    print(f"[DEBUG] Message callback triggered!")
    print(f"[DEBUG] Room ID: {room.room_id}")
    print(f"[DEBUG] Sender: {event.sender}, Bot ID: {client.user_id}")
    print(f"[DEBUG] Message: {event.body}")
    print(f"[DEBUG] Event ID: {event.event_id}")
    
    # Check if we've already processed this event
    if event.event_id in processed_events:
        print(f"[DEBUG] Already processed event {event.event_id}, skipping")
        return
    
    # Check if message is from before bot started (with 5 second grace period)
    # This prevents responding to old messages on startup
    message_timestamp = event.server_timestamp / 1000 if event.server_timestamp else time.time()
    if message_timestamp < (bot_start_time - 5):
        print(f"[DEBUG] Message from before bot startup, marking as processed and skipping")
        mark_event_processed(event.event_id)
        return
    
    # Mark this event as processed immediately to prevent duplicates
    mark_event_processed(event.event_id)
    
    # Track received message (before filtering)
    stats_tracker.record_message_received(room.room_id, event.sender, event.body)
    
    # Ignore our own messages
    if event.sender == client.user_id:
        print("[DEBUG] Ignoring own message")
        return
    
    # Ignore messages from other known bots
    if any(event.sender.startswith(bot) for bot in KNOWN_BOTS):
        print("[DEBUG] Ignoring message from another bot")
        return
    
    # Store this message in room history
    message_data = {
        'sender': event.sender,
        'body': event.body,
        'timestamp': event.server_timestamp / 1000 if event.server_timestamp else datetime.now().timestamp(),
        'event_id': event.event_id
    }
    room_message_history[room.room_id].append(message_data)
    
    # Update conversation context
    conversation_context.update_context(room.room_id, message_data)
    
    # Maybe react to the message
    await maybe_react(client, room.room_id, event.event_id, event.body)
    
    # Check if message starts with ? for commands - handle them directly here
    if event.body.strip().startswith('?'):
        command_parts = event.body.strip().split()
        command = command_parts[0].lower()
        
        # Track command usage
        stats_tracker.record_command_usage(command)
        
        # Import command handlers to avoid circular imports
        from integrations.matrix_integration import (
            handle_help_command, handle_clock_command, handle_price_command,
            handle_meme_command, handle_stats_command, handle_stonks_command,
            handle_setting_command, handle_sys_command
        )
        
        # Handle commands directly
        if command == '?help':
            await handle_help_command(client, room, event)
            return
        elif command == '?clock':
            await handle_clock_command(client, room, event)
            return
        elif command == '?price':
            await handle_price_command(client, room, event)
            return
        elif command == '?meme':
            await handle_meme_command(client, room, event)
            return
        elif command == '?stats':
            await handle_stats_command(client, room, event)
            return
        elif command == '?stonks':
            await handle_stonks_command(client, room, event)
            return
        elif command == '?setting':
            await handle_setting_command(client, room, event)
            return
        elif command == '?sys':
            await handle_sys_command(client, room, event)
            return
        
        # Unknown command - don't process further
        return
    
    # Check if this is a reply to a message
    is_reply = False
    replied_to_bot = False
    previous_message = None
    
    if hasattr(event, 'source') and event.source.get('content', {}).get('m.relates_to', {}).get('m.in_reply_to'):
        is_reply = True
        reply_to_event_id = event.source['content']['m.relates_to']['m.in_reply_to']['event_id']
        print(f"[DEBUG] This is a reply to event: {reply_to_event_id}")
        
        # Fetch the replied-to event
        replied_event = await get_replied_to_event(client, room.room_id, reply_to_event_id)
        if replied_event and hasattr(replied_event, 'event'):
            replied_sender = replied_event.event.sender
            if replied_sender == client.user_id:
                replied_to_bot = True
                previous_message = replied_event.event.body
                print(f"[DEBUG] User is replying to bot's message: {previous_message[:50]}...")
    
    # Extract the bot's display name and username from its Matrix ID
    # client.user_id is like "@simpletest888:matrix.org"
    bot_localpart = client.user_id.split(':')[0][1:]  # Remove @ and domain to get "simpletest888"
    
    # Check for direct mention or reply
    # Check both the configured BOT_USERNAME and the actual Matrix username
    message_lower = event.body.lower()
    should_respond = (
        BOT_USERNAME in message_lower or 
        bot_localpart.lower() in message_lower or
        replied_to_bot
    )
    
    if should_respond:
        # Check for reset command
        if "!reset" in event.body.lower():
            # Clear the room's message history
            room_message_history[room.room_id].clear()
            
            await client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": f"✨ {BOT_USERNAME.capitalize()}'s context cleared! Fresh start! 🧹"
                }
            )
            return
        
        prompt = event.body
        
        # Extract URLs from message
        urls_in_message = extract_urls_from_message(event.body)
        url_contents = []
        
        if urls_in_message:
            print(f"[DEBUG] Found URLs in message: {urls_in_message}")
            stats_tracker.record_feature_usage('url_analysis')
            
            # Send typing notification while fetching URLs
            await client.room_typing(room.room_id, True)
            
            # Process URLs with timeout
            for url in urls_in_message[:3]:  # Limit to first 3 URLs
                content = await fetch_url_content(url)
                if content:
                    url_contents.append(content)
        
        print(f"Sending prompt to LLM: {prompt}")
        if replied_to_bot:
            print(f"With context from previous bot message")
        if url_contents:
            print(f"With {len(url_contents)} URL contents")
        
        # Send typing notification
        await client.room_typing(room.room_id, True)
        
        try:
            # Use the retry wrapper - pass client for context
            reply = await get_llm_reply_with_retry(
                prompt=prompt,
                previous_message=previous_message,
                room_id=room.room_id,
                url_contents=url_contents,
                client=client
            )
            
            # Track if web search was used (check for search indicators in response)
            if "searched for" in reply.lower() or "search results" in reply.lower():
                stats_tracker.record_feature_usage('web_search')
            
            # Final safety check
            if any(word.lower() in reply.lower() for word in FILTERED_WORDS):
                print("[WARNING] Reply contained filtered word, filtering again")
                reply = filter_bot_triggers(reply)
            
            print(f"LLM Reply (filtered): {reply}")
            
            # Stop typing notification
            await client.room_typing(room.room_id, False)
            
            # Send the formatted response
            response = await send_formatted_message(client, room.room_id, reply)
            
            # Store bot's message in history
            if hasattr(response, 'event_id'):
                bot_message_data = {
                    'sender': client.user_id,
                    'body': reply,
                    'timestamp': datetime.now().timestamp(),
                    'event_id': response.event_id
                }
                room_message_history[room.room_id].append(bot_message_data)
                
                # Update context with bot's message
                conversation_context.update_context(room.room_id, bot_message_data)
            
            print("[DEBUG] Message sent successfully!")
        except Exception as e:
            print(f"Error sending message: {e}")
            await client.room_typing(room.room_id, False)
            
            # Send error message
            await client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "Oops, something went wrong! Try again maybe? 🤷"
                }
            )
    else:
        if is_reply:
            print("Ignoring reply (not to bot's message)")
        else:
            print(f"Ignoring message (doesn't contain '{BOT_USERNAME}' or '{bot_localpart}')")
