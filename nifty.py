#!/usr/bin/env python3
"""
Nifty Bot - A Matrix chatbot with personality
Main entry point for the application
"""
import asyncio
from nio import AsyncClient, LoginResponse, RoomMessageText, InviteMemberEvent
from config.settings import HOMESERVER, USERNAME, PASSWORD
from modules.message_handler import message_callback
from modules.invite_handler import invite_callback, joined_rooms
from modules.cleanup import cleanup_old_context

async def main():
    """Main bot initialization and event loop"""
    client = AsyncClient(HOMESERVER, USERNAME)
    
    # Login
    response = await client.login(PASSWORD)
    if not isinstance(response, LoginResponse):
        print(f"Failed to login: {response}")
        return
    
    print(f"Logged in as {client.user_id}")
    
    # Get list of joined rooms
    print("Getting list of joined rooms...")
    joined_rooms_response = await client.joined_rooms()
    if hasattr(joined_rooms_response, 'rooms'):
        for room_id in joined_rooms_response.rooms:
            joined_rooms.add(room_id)
            print(f"Already in room: {room_id}")
    
    # Create wrapped callbacks that include the client
    async def wrapped_message_callback(room, event):
        await message_callback(client, room, event)
    
    async def wrapped_invite_callback(room, event):
        await invite_callback(client, room, event)
    
    # Add event callbacks
    client.add_event_callback(wrapped_message_callback, RoomMessageText)
    client.add_event_callback(wrapped_invite_callback, InviteMemberEvent)
    
    # Do an initial sync to get the latest state
    print("Performing initial sync...")
    sync_response = await client.sync(timeout=30000, full_state=True)
    print(f"Initial sync completed. Next batch: {sync_response.next_batch}")
    
    # Start cleanup task
    asyncio.create_task(cleanup_old_context())
    
    print("=" * 50)
    print("🤖 Nifty Bot is running!")
    print("=" * 50)
    print("✅ Identity: @nifty:matrix.stargazypie.xyz")
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
    try:
        await client.sync_forever(timeout=30000, full_state=False)
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt - shutting down...")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
