"""Cleanup and maintenance tasks"""
import asyncio
from datetime import datetime
from modules.context import conversation_context
from config.settings import CONTEXT_CLEANUP_INTERVAL, CONTEXT_CLEANUP_AGE

async def cleanup_old_context():
    """Periodic cleanup of old context data"""
    while True:
        await asyncio.sleep(CONTEXT_CLEANUP_INTERVAL)
        
        current_time = datetime.now().timestamp()
        
        # Clean up old conversation context
        for room_id in list(conversation_context.topics.keys()):
            # Decay all topic scores
            for topic in conversation_context.topics[room_id]:
                conversation_context.topics[room_id][topic] *= 0.5
            
            # Remove topics with very low scores
            conversation_context.topics[room_id] = {
                topic: score 
                for topic, score in conversation_context.topics[room_id].items() 
                if score > 0.1
            }
        
        # Clear very old important messages
        for room_id in conversation_context.important_messages:
            cutoff_time = current_time - CONTEXT_CLEANUP_AGE
            conversation_context.important_messages[room_id] = [
                msg for msg in conversation_context.important_messages[room_id]
                if msg['timestamp'] > cutoff_time
            ]
        
        print(f"[CLEANUP] Context cleanup completed at {datetime.now()}")
