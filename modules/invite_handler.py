"""Room invite handling"""
from nio import MatrixRoom, InviteMemberEvent

# Store joined rooms
joined_rooms = set()

async def invite_callback(client, room: MatrixRoom, event: InviteMemberEvent):
    """Handle room invites"""
    print(f"[INVITE] Received invite to room {room.room_id} from {event.sender}")
    
    # Only process invites for our user
    if event.state_key != client.user_id:
        return
    
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
