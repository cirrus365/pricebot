"""
Matrix integration for Nifty Bot
"""
import asyncio
import logging
from nio import AsyncClient, LoginResponse, RoomMessageText, InviteMemberEvent
from config.settings import HOMESERVER, USERNAME, PASSWORD, BOT_USERNAME, ENABLE_MEME_GENERATION
from modules.message_handler import message_callback
from modules.invite_handler import invite_callback, joined_rooms
from modules.cleanup import cleanup_old_context
from modules.meme_generator import meme_generator

logger = logging.getLogger(__name__)

async def run_matrix_bot():
    """Run the Matrix bot"""
    # Check for required Matrix credentials
    if not all([HOMESERVER, USERNAME, PASSWORD]):
        logger.error("Matrix credentials not configured. Please set MATRIX_HOMESERVER, MATRIX_USERNAME, and MATRIX_PASSWORD in .env file")
        print("\n❌ ERROR: Matrix credentials missing!")
        print("Please configure the following in your .env file:")
        print("  - MATRIX_HOMESERVER")
        print("  - MATRIX_USERNAME")
        print("  - MATRIX_PASSWORD")
        return
        
    client = AsyncClient(HOMESERVER, USERNAME)
    
    try:
        # Login
        response = await client.login(PASSWORD)
        if not isinstance(response, LoginResponse):
            logger.error(f"Failed to login to Matrix: {response}")
            return
        
        logger.info(f"Matrix: Logged in as {client.user_id}")
        
        # Get list of joined rooms
        logger.info("Matrix: Getting list of joined rooms...")
        joined_rooms_response = await client.joined_rooms()
        if hasattr(joined_rooms_response, 'rooms'):
            for room_id in joined_rooms_response.rooms:
                joined_rooms.add(room_id)
                logger.info(f"Matrix: Already in room: {room_id}")
        
        # Create wrapped callbacks that include the client
        async def wrapped_message_callback(room, event):
            # Check if it's a meme command
            if event.body.startswith('!meme ') and ENABLE_MEME_GENERATION:
                await handle_meme_command(client, room, event)
            else:
                await message_callback(client, room, event)
        
        async def wrapped_invite_callback(room, event):
            await invite_callback(client, room, event)
        
        # Add event callbacks
        client.add_event_callback(wrapped_message_callback, RoomMessageText)
        client.add_event_callback(wrapped_invite_callback, InviteMemberEvent)
        
        # Do an initial sync to get the latest state
        logger.info("Matrix: Performing initial sync...")
        sync_response = await client.sync(timeout=30000, full_state=True)
        logger.info(f"Matrix: Initial sync completed. Next batch: {sync_response.next_batch}")
        
        # Start cleanup task
        asyncio.create_task(cleanup_old_context())
        
        print("=" * 50)
        print(f"🤖 {BOT_USERNAME.capitalize()} Bot - Matrix Integration Active!")
        print("=" * 50)
        print(f"✅ Identity: {USERNAME}")
        print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
        print("✅ Listening for messages in all joined rooms")
        print("✅ Auto-accepting room invites")
        print(f"📝 Trigger: Say '{BOT_USERNAME}' anywhere in a message")
        print("💬 Or reply directly to any of my messages")
        print("❌ Random responses: DISABLED")
        print("👀 Emoji reactions: ENABLED (various triggers)")
        print(f"🧹 Reset: '{BOT_USERNAME} !reset' to clear context")
        print(f"📊 Summary: '{BOT_USERNAME} summary' for comprehensive chat analysis")
        if ENABLE_MEME_GENERATION:
            print("🎨 Meme generation: !meme <topic> to create memes")
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
        print("=" * 50)
        
        # Sync forever
        await client.sync_forever(timeout=30000, full_state=False)
            
    except Exception as e:
        logger.error(f"Matrix bot error: {e}")
        raise
    finally:
        await client.close()

async def handle_meme_command(client, room, event):
    """Handle meme generation command for Matrix"""
    try:
        # Send typing indicator
        await client.room_typing(room.room_id, typing_state=True)
        
        # Generate meme
        meme_url, caption = await meme_generator.handle_meme_command(event.body)
        
        if meme_url:
            # Send the meme as an image with caption
            content = {
                "body": caption,
                "msgtype": "m.image",
                "url": meme_url,
                "info": {
                    "mimetype": "image/jpeg"
                }
            }
            
            # For Matrix, we need to upload the image first or use the direct URL
            # Since Imgflip provides a direct URL, we can use it
            formatted_body = f"{caption}\n{meme_url}"
            
            await client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": formatted_body,
                    "format": "org.matrix.custom.html",
                    "formatted_body": f'<p>{caption}</p><img src="{meme_url}" alt="meme"/>'
                }
            )
        else:
            # Send error message
            await client.room_send(
                room_id=room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": caption or "Failed to generate meme"
                }
            )
            
    except Exception as e:
        logger.error(f"Error handling meme command: {e}")
        await client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": "Sorry, I couldn't create a meme right now. Please try again later."
            }
        )
    finally:
        await client.room_typing(room.room_id, typing_state=False)
