#!/usr/bin/env python3
"""
Nifty Bot - Multi-platform chatbot with Matrix and Discord support
Main entry point for the application
"""
import asyncio
import logging
import sys
from config.settings import (
    HOMESERVER, USERNAME, PASSWORD, INTEGRATIONS
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_matrix_bot():
    """Run the Matrix bot"""
    if not INTEGRATIONS.get('matrix', True):
        logger.info("Matrix integration disabled")
        return
    
    # Check for required Matrix credentials
    if not all([HOMESERVER, USERNAME, PASSWORD]):
        logger.error("Matrix credentials not configured. Please set MATRIX_HOMESERVER, MATRIX_USERNAME, and MATRIX_PASSWORD in .env file")
        print("\n❌ ERROR: Matrix credentials missing!")
        print("Please configure the following in your .env file:")
        print("  - MATRIX_HOMESERVER")
        print("  - MATRIX_USERNAME")
        print("  - MATRIX_PASSWORD")
        return
    
    from nio import AsyncClient, LoginResponse, RoomMessageText, InviteMemberEvent
    from modules.message_handler import message_callback
    from modules.invite_handler import invite_callback, joined_rooms
    from modules.cleanup import cleanup_old_context
        
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
        print("🤖 Nifty Bot - Matrix Integration Active!")
        print("=" * 50)
        print(f"✅ Identity: {USERNAME}")
        print("✅ Listening for messages in all joined rooms")
        print("✅ Auto-accepting room invites")
        print("📝 Trigger: Say 'nifty' anywhere in a message")
        print("💬 Or reply directly to any of my messages")
        print("❌ Random responses: DISABLED")
        print("👀 Emoji reactions: ENABLED (various triggers)")
        print("🧹 Reset: 'nifty !reset' to clear context")
        print("📊 Summary: 'nifty summary' for comprehensive chat analysis")
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

async def run_discord_bot():
    """Run the Discord bot"""
    if not INTEGRATIONS.get('discord', False):
        logger.info("Discord integration disabled")
        return
    
    # Check for required Discord credentials
    from config.settings import DISCORD_TOKEN
    if not DISCORD_TOKEN:
        logger.error("Discord token not configured. Please set DISCORD_TOKEN in .env file")
        print("\n❌ ERROR: Discord token missing!")
        print("Please configure DISCORD_TOKEN in your .env file")
        return
        
    try:
        from modules.discord_handler import run_discord_bot as start_discord
        
        print("=" * 50)
        print("🤖 Nifty Bot - Discord Integration Active!")
        print("=" * 50)
        print("✅ Discord bot starting...")
        print("📝 Commands: Use ! prefix (e.g., !help)")
        print("💬 Chat: Mention the bot or reply to its messages")
        print("💰 Price tracking: !price <crypto> or !xmr")
        print("🔍 Web search: Ask to search for anything")
        print("📊 Stats: !stats for bot statistics")
        print("=" * 50)
        
        await start_discord()
        
    except ImportError as e:
        logger.error(f"Discord integration not available: {e}")
        logger.info("Please install discord.py: pip install discord.py")
    except Exception as e:
        logger.error(f"Discord bot error: {e}")
        raise

async def main():
    """Main bot initialization and event loop"""
    tasks = []
    
    # Check which integrations are enabled
    matrix_enabled = INTEGRATIONS.get('matrix', True)
    discord_enabled = INTEGRATIONS.get('discord', False)
    
    print("\n" + "=" * 50)
    print("🚀 Nifty Bot Starting...")
    print("=" * 50)
    print(f"📡 Matrix Integration: {'✅ ENABLED' if matrix_enabled else '❌ DISABLED'}")
    print(f"💬 Discord Integration: {'✅ ENABLED' if discord_enabled else '❌ DISABLED'}")
    print("=" * 50 + "\n")
    
    # Start Matrix bot if enabled
    if matrix_enabled:
        logger.info("Starting Matrix integration...")
        tasks.append(asyncio.create_task(run_matrix_bot()))
    
    # Start Discord bot if enabled  
    if discord_enabled:
        logger.info("Starting Discord integration...")
        tasks.append(asyncio.create_task(run_discord_bot()))
    
    if not tasks:
        logger.error("No integrations enabled! Enable at least one integration in .env file.")
        print("\n❌ ERROR: No integrations enabled!")
        print("Please set ENABLE_MATRIX=true or ENABLE_DISCORD=true in your .env file")
        return
    
    # Wait for all tasks
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down...")
        print("\n\nShutting down Nifty Bot...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
