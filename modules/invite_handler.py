"""Room invite handling"""
from nio import MatrixRoom, InviteMemberEvent
from config.settings import ENABLE_AUTO_INVITE, ALLOWED_INVITE_USERS

# Store joined rooms
joined_rooms = set()

async def invite_callback(client, room: MatrixRoom, event: InviteMemberEvent):
    """Handle room invites"""
    print(f"[INVITE] Received invite to room {room.room_id} from {event.sender}")
    
    # Only process invites for our user
    if event.state_key != client.user_id:
        return
    
    # Check if auto-invite is disabled
    if not ENABLE_AUTO_INVITE:
        print(f"[INVITE] Auto-invite is disabled. Ignoring invite from {event.sender}")
        return
    
    # Check if there's a whitelist of allowed users
    if ALLOWED_INVITE_USERS:
        # Strip whitespace from allowed users
        allowed_users = [user.strip() for user in ALLOWED_INVITE_USERS]
        if event.sender not in allowed_users:
            print(f"[INVITE] User {event.sender} is not in the allowed invite list. Ignoring invite.")
            return
        else:
            print(f"[INVITE] User {event.sender} is in the allowed invite list.")
    
    # Accept the invite
    print(f"[INVITE] Accepting invite to room {room.room_id}")
    result = await client.join(room.room_id)
    
    if hasattr(result, 'room_id'):
        print(f"[INVITE] Successfully joined room {room.room_id}")
        joined_rooms.add(room.room_id)
        
        # Send a greeting message
        await client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": "Hey! I'm Nifty! 👋 Thanks for inviting me! Just say 'nifty' followed by your message to chat, or reply to any of my messages! 🚀\n\nI specialize in:\n• 💻 Programming & debugging\n• 🐧 Linux/Unix systems\n• 🌐 Web dev & networking\n• 🔒 Security & cryptography\n• 🤖 General tech support\n• 📱 Mobile dev tips\n• 🎮 Gaming & internet culture\n\nCommands:\n• `nifty !reset` - Clear my context\n• `nifty summary` - Get a detailed chat analysis\n• Share URLs and I'll read and analyze them!\n\nI also react to messages with emojis when appropriate! 😊 Let's build something cool! 💪"
            }
        )
    else:
        print(f"[INVITE] Failed to join room: {result}")
