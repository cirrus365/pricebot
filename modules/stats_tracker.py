"""Statistics tracking for the bot"""
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class StatsTracker:
    """Track bot statistics including message volume, room participation, etc."""
    
    def __init__(self):
        # Message counters
        self.total_messages_processed = 0
        self.total_messages_sent = 0
        self.messages_by_room = defaultdict(int)
        self.messages_by_day = defaultdict(int)
        self.messages_by_hour = defaultdict(int)
        
        # Track messages for rolling windows
        self.recent_messages = deque(maxlen=1000)  # Keep last 1000 messages for analysis
        
        # Room tracking
        self.active_rooms = set()
        self.room_join_times = {}
        
        # Command usage
        self.command_usage = defaultdict(int)
        
        # Feature usage
        self.feature_usage = defaultdict(int)
        
        # Start time
        self.start_time = datetime.now()
        
    def record_message_received(self, room_id: str, sender: str, message: str):
        """Record an incoming message"""
        now = datetime.now()
        
        self.total_messages_processed += 1
        self.messages_by_room[room_id] += 1
        
        # Track by day and hour
        day_key = now.strftime("%Y-%m-%d")
        hour_key = now.hour
        self.messages_by_day[day_key] += 1
        self.messages_by_hour[hour_key] += 1
        
        # Add to recent messages
        self.recent_messages.append({
            'timestamp': now,
            'room_id': room_id,
            'sender': sender,
            'type': 'received'
        })
        
        # Track room activity
        self.active_rooms.add(room_id)
        
    def record_message_sent(self, room_id: str):
        """Record a sent message"""
        now = datetime.now()
        
        self.total_messages_sent += 1
        
        # Add to recent messages
        self.recent_messages.append({
            'timestamp': now,
            'room_id': room_id,
            'type': 'sent'
        })
        
    def record_command_usage(self, command: str):
        """Record command usage"""
        self.command_usage[command] += 1
        
    def record_feature_usage(self, feature: str):
        """Record feature usage (e.g., 'url_analysis', 'web_search', 'meme_generation')"""
        self.feature_usage[feature] += 1
        
    def record_room_join(self, room_id: str):
        """Record joining a room"""
        self.active_rooms.add(room_id)
        self.room_join_times[room_id] = datetime.now()
        
    def record_room_leave(self, room_id: str):
        """Record leaving a room"""
        self.active_rooms.discard(room_id)
        if room_id in self.room_join_times:
            del self.room_join_times[room_id]
            
    def get_uptime(self) -> str:
        """Get bot uptime as a formatted string"""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)
        
    def get_daily_stats(self) -> Dict:
        """Get statistics for the last 24 hours"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        # Count messages in last 24 hours
        recent_received = sum(1 for msg in self.recent_messages 
                            if msg['timestamp'] > last_24h and msg['type'] == 'received')
        recent_sent = sum(1 for msg in self.recent_messages 
                         if msg['timestamp'] > last_24h and msg['type'] == 'sent')
        
        # Get active rooms in last 24 hours
        recent_rooms = set(msg['room_id'] for msg in self.recent_messages 
                          if msg['timestamp'] > last_24h)
        
        return {
            'messages_received': recent_received,
            'messages_sent': recent_sent,
            'active_rooms': len(recent_rooms),
            'total_rooms': len(self.active_rooms)
        }
        
    def get_hourly_distribution(self) -> List[tuple]:
        """Get message distribution by hour"""
        # Sort hours and return top 5 most active
        sorted_hours = sorted(self.messages_by_hour.items(), key=lambda x: x[1], reverse=True)
        return sorted_hours[:5]
        
    def get_most_active_rooms(self, limit: int = 5) -> List[tuple]:
        """Get most active rooms"""
        sorted_rooms = sorted(self.messages_by_room.items(), key=lambda x: x[1], reverse=True)
        return sorted_rooms[:limit]
        
    def get_command_stats(self) -> Dict:
        """Get command usage statistics"""
        return dict(self.command_usage)
        
    def get_feature_stats(self) -> Dict:
        """Get feature usage statistics"""
        return dict(self.feature_usage)

# Global stats tracker instance
stats_tracker = StatsTracker()
