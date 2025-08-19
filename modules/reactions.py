"""Message reaction handling"""
import random
from config.personality import REACTION_TRIGGERS, REACTION_CHANCES, DEFAULT_REACTION_CHANCE

async def maybe_react(client, room_id, event_id, message):
    """Send reaction to message if it contains trigger words"""
    message_lower = message.lower()
    
    for trigger, reactions in REACTION_TRIGGERS.items():
        if trigger in message_lower:
            chance = REACTION_CHANCES.get(trigger, DEFAULT_REACTION_CHANCE)
            
            if random.random() < chance:
                reaction = random.choice(reactions)
                try:
                    await client.room_send(
                        room_id=room_id,
                        message_type="m.reaction",
                        content={
                            "m.relates_to": {
                                "rel_type": "m.annotation",
                                "event_id": event_id,
                                "key": reaction
                            }
                        }
                    )
                except Exception as e:
                    print(f"Error sending reaction: {e}")
                break  # Only one reaction per message
