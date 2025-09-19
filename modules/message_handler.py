"""Message handling and processing"""
import re
import html
import time
import json
import os
import asyncio
from datetime import datetime
from nio import MatrixRoom, RoomMessageText
from config.settings import KNOWN_BOTS, FILTERED_WORDS, BOT_USERNAME, ENABLE_CONTEXT_ANALYSIS
from utils.helpers import extract_urls_from_message, filter_bot_triggers
from utils.formatting import extract_code_from_response
from modules.context import room_message_history
from modules.reactions import maybe_react
from modules.web_search import fetch_url_content
from modules.llm import get_llm_reply_with_retry
from modules.stats_tracker import stats_tracker

# Track processed events to avoid duplicates
processed_events = set()
bot_start_time = time.time()

def mark_event_processed(event_id):
    """Mark an event as processed"""
    processed_events.add(event_id)

async def get_replied_to_event(client, room_id, reply_to_event_id):
    """Fetch the event that was replied to"""
    try:
        response = await client.room_get_event(room_id, reply_to_event_id)
        return response
    except Exception as e:
        return None

async def send_formatted_message(client, room_id, reply_text):
    """Send a message with proper formatting"""
    # Simple formatting
    formatted_body = reply_text
    
    # Handle code blocks
    if "```" in reply_text:
        parts = extract_code_from_response(reply_text)
        formatted_body = ""
        plain_body = ""
        
        for part in parts:
            if part['type'] == 'text':
                text = part['content']
                formatted_body += f"<p>{html.escape(text)}</p>"
                plain_body += text + "\n"
            elif part['type'] == 'code':
                code = html.escape(part['content'])
                formatted_body += f'<pre><code>{code}</code></pre>'
                plain_body += f"```\n{part['content']}\n```\n"
        
        content = {
            "msgtype": "m.text",
            "body": plain_body.strip(),
            "format": "org.matrix.custom.html",
            "formatted_body": formatted_body.strip()
        }
    else:
        # Simple text message
        content = {
            "msgtype": "m.text",
            "body": reply_text
        }
    
    result = await client.room_send(
        room_id=room_id,
        message_type="m.room.message",
        content=content
    )
    
    stats_tracker.record_message_sent(room_id)
    return result

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
    
    # Track received message
    stats_tracker.record_message_received(room.room_id, event.sender, event.body)
    
    # Ignore our own messages
    if event.sender == client.user_id:
        return
    
    # Ignore other bots
    if any(event.sender.startswith(bot) for bot in KNOWN_BOTS):
        return
    
    # Store message in history if context is enabled
    if ENABLE_CONTEXT_ANALYSIS:
        message_data = {
            'sender': event.sender,
            'body': event.body,
            'timestamp': event.server_timestamp / 1000 if event.server_timestamp else datetime.now().timestamp(),
            'event_id': event.event_id
        }
        room_message_history[room.room_id].append(message_data)
    
    # Maybe react to the message
    await maybe_react(client, room.room_id, event.event_id, event.body)
    
    # Check if message starts with ? for commands
    if event.body.strip().startswith('?'):
        command_parts = event.body.strip().split()
        command = command_parts[0].lower()
        
        stats_tracker.record_command_usage(command)
        
        # Import command handlers
        from integrations.matrix_integration import (
            handle_help_command, handle_clock_command, handle_price_command,
            handle_meme_command, handle_stats_command, handle_stonks_command,
            handle_setting_command, handle_sys_command
        )
        
        # Handle commands
        if command == '?help':
            await handle_help_command(client, room, event)
        elif command == '?clock':
            await handle_clock_command(client, room, event)
        elif command == '?price':
            await handle_price_command(client, room, event)
        elif command == '?meme':
            await handle_meme_command(client, room, event)
        elif command == '?stats':
            await handle_stats_command(client, room, event)
        elif command == '?stonks':
            await handle_stonks_command(client, room, event)
        elif command == '?setting':
            await handle_setting_command(client, room, event)
        elif command == '?sys':
            await handle_sys_command(client, room, event)
        
        return
    
    # Check if this is a reply
    is_reply = False
    replied_to_bot = False
    previous_message = None
    
    if hasattr(event, 'source') and event.source.get('content', {}).get('m.relates_to', {}).get('m.in_reply_to'):
        is_reply = True
        reply_to_event_id = event.source['content']['m.relates_to']['m.in_reply_to']['event_id']
        
        replied_event = await get_replied_to_event(client, room.room_id, reply_to_event_id)
        if replied_event and hasattr(replied_event, 'event'):
            if replied_event.event.sender == client.user_id:
                replied_to_bot = True
                previous_message = replied_event.event.body
    
    # Check for bot mention or reply
    bot_localpart = client.user_id.split(':')[0][1:]
    message_lower = event.body.lower()
    should_respond = (
        BOT_USERNAME in message_lower or 
        bot_localpart.lower() in message_lower or
        replied_to_bot
    )
    
    if should_respond:
        # Start typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Check for reset command
        if "!reset" in event.body.lower():
            if ENABLE_CONTEXT_ANALYSIS:
                room_message_history[room.room_id].clear()
            
            await client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": f"✨ Context cleared!"
                }
            )
            # Stop typing indicator
            await client.room_typing(room.room_id, typing_state=False)
            return
        
        prompt = event.body
        
        # Check for URLs (simplified)
        url_contents = None
        urls = extract_urls_from_message(event.body)
        if urls and len(urls) > 0:
            stats_tracker.record_feature_usage('url_analysis')
            url_content = await fetch_url_content(urls[0])
            if url_content:
                url_contents = [url_content]
        
        # Get LLM reply
        try:
            reply = await get_llm_reply_with_retry(
                prompt=prompt,
                previous_message=previous_message,
                room_id=room.room_id if ENABLE_CONTEXT_ANALYSIS else None,
                url_contents=url_contents,
                client=client
            )
            
            # Send the response
            await send_formatted_message(client, room.room_id, reply)
            
            # Stop typing indicator after sending
            await client.room_typing(room.room_id, typing_state=False)
            
            # Store bot's message if context is enabled
            if ENABLE_CONTEXT_ANALYSIS and hasattr(reply, 'event_id'):
                bot_message_data = {
                    'sender': client.user_id,
                    'body': reply,
                    'timestamp': datetime.now().timestamp(),
                    'event_id': reply.event_id if hasattr(reply, 'event_id') else None
                }
                room_message_history[room.room_id].append(bot_message_data)
            
        except Exception as e:
            # Stop typing indicator on error
            await client.room_typing(room.room_id, typing_state=False)
            
            await client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "Sorry, something went wrong. Please try again."
                }
            )
