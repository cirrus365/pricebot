"""Room invite handling"""
from nio import MatrixRoom, InviteMemberEvent
from config.settings import ALLOWED_INVITE_USERS, ENABLE_AUTO_INVITE

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
                "body": "👋 Price Tracker & World Clock Bot\n\n📚 Available Commands:\n• `?price <crypto>` - Get cryptocurrency price\n• `?price <from> <to>` - Get exchange rate\n• `?xmr` - Quick Monero price check\n• `?stonks <ticker>` - Get stock information\n• `?clock <location>` - Get time for a location\n• `?help` - Show all commands\n\nExamples: `?price btc`, `?clock paris`, `?stonks AAPL`"
            }
        )
    else:
        print(f"[INVITE] Failed to join room: {result}")
