"""Conversation context management"""
from collections import defaultdict, deque
from datetime import datetime
from utils.helpers import get_display_name
from config.settings import (
    MAX_ROOM_HISTORY, MAX_IMPORTANT_MESSAGES,
    ENABLE_TOPIC_TRACKING, ENABLE_USER_INTERESTS,
    ENABLE_IMPORTANCE_DETECTION, ENABLE_CONVERSATION_FLOW
)

# Store recent messages for context
room_message_history = defaultdict(lambda: deque(maxlen=MAX_ROOM_HISTORY))

class ConversationContext:
    def __init__(self):
        self.topics = defaultdict(lambda: defaultdict(float))  # room_id -> topic -> relevance_score
        self.user_interests = defaultdict(lambda: defaultdict(list))  # room_id -> user -> interests
        self.conversation_threads = defaultdict(list)  # room_id -> list of conversation threads
        self.important_messages = defaultdict(list)  # room_id -> list of important messages
        
    def update_context(self, room_id, message_data):
        """Update conversation context with new message"""
        sender = message_data['sender']
        body = message_data['body'].lower()
        
        # Only track topics if enabled
        if ENABLE_TOPIC_TRACKING:
            # Extract topics from message
            tech_topics = {
                'python': ['python', 'pip', 'django', 'flask', 'pandas', 'numpy'],
                'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
                'linux': ['linux', 'ubuntu', 'debian', 'arch', 'kernel', 'bash'],
                'security': ['security', 'encryption', 'vpn', 'tor', 'privacy', 'hack'],
                'crypto': ['bitcoin', 'monero', 'ethereum', 'blockchain', 'defi'],
                'ai': ['ai', 'machine learning', 'neural', 'gpt', 'llm', 'deepseek'],
                'networking': ['network', 'tcp', 'udp', 'http', 'dns', 'firewall'],
                'database': ['database', 'sql', 'mongodb', 'redis', 'postgresql'],
            }
            
            # Update topic scores
            for topic, keywords in tech_topics.items():
                if any(keyword in body for keyword in keywords):
                    self.topics[room_id][topic] += 1.0
                    # Decay older topics
                    for t in self.topics[room_id]:
                        if t != topic:
                            self.topics[room_id][t] *= 0.95
        
        # Only track user interests if enabled
        if ENABLE_USER_INTERESTS and ENABLE_TOPIC_TRACKING:
            # Track user interests (requires topic tracking to be enabled)
            tech_topics = {
                'python': ['python', 'pip', 'django', 'flask', 'pandas', 'numpy'],
                'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
                'linux': ['linux', 'ubuntu', 'debian', 'arch', 'kernel', 'bash'],
                'security': ['security', 'encryption', 'vpn', 'tor', 'privacy', 'hack'],
                'crypto': ['bitcoin', 'monero', 'ethereum', 'blockchain', 'defi'],
                'ai': ['ai', 'machine learning', 'neural', 'gpt', 'llm', 'deepseek'],
                'networking': ['network', 'tcp', 'udp', 'http', 'dns', 'firewall'],
                'database': ['database', 'sql', 'mongodb', 'redis', 'postgresql'],
            }
            
            for topic, keywords in tech_topics.items():
                if any(keyword in body for keyword in keywords):
                    if topic not in self.user_interests[room_id][sender]:
                        self.user_interests[room_id][sender].append(topic)
        
        # Only detect important messages if enabled
        if ENABLE_IMPORTANCE_DETECTION:
            # Mark important messages (questions, problems, announcements)
            importance_indicators = ['?', 'help', 'error', 'problem', 'issue', 'important', 'announcement', 'urgent']
            if any(indicator in body for indicator in importance_indicators):
                self.important_messages[room_id].append({
                    'sender': sender,
                    'body': message_data['body'],
                    'timestamp': message_data['timestamp'],
                    'type': 'question' if '?' in body else 'issue' if any(word in body for word in ['error', 'problem']) else 'announcement'
                })
                # Keep only last N important messages
                self.important_messages[room_id] = self.important_messages[room_id][-MAX_IMPORTANT_MESSAGES:]
    
    def get_room_context(self, room_id, lookback_messages=30):
        """Get comprehensive room context"""
        if room_id not in room_message_history:
            return None
        
        messages = list(room_message_history[room_id])[-lookback_messages:]
        if not messages:
            return None
        
        context = {
            'message_count': len(messages),
            'unique_participants': len(set(msg['sender'] for msg in messages))
        }
        
        # Only include topic analysis if enabled
        if ENABLE_TOPIC_TRACKING:
            # Get top topics
            top_topics = sorted(self.topics[room_id].items(), key=lambda x: x[1], reverse=True)[:5]
            context['top_topics'] = top_topics
        
        # Only include user expertise if enabled
        if ENABLE_USER_INTERESTS:
            # Get active users and their expertise
            user_expertise = {}
            for user, interests in self.user_interests[room_id].items():
                if interests:
                    user_expertise[get_display_name(user)] = interests[:3]  # Top 3 interests per user
            context['user_expertise'] = user_expertise
        
        # Only include important messages if enabled
        if ENABLE_IMPORTANCE_DETECTION:
            # Get recent important messages
            recent_important = self.important_messages[room_id][-5:]
            context['recent_important'] = recent_important
        
        # Only analyze conversation flow if enabled
        if ENABLE_CONVERSATION_FLOW:
            # Analyze conversation flow
            conversation_flow = self.analyze_conversation_flow(messages)
            context['conversation_flow'] = conversation_flow
        
        return context
    
    def analyze_conversation_flow(self, messages):
        """Analyze how conversation is flowing"""
        if not ENABLE_CONVERSATION_FLOW:
            return 'normal'
            
        if len(messages) < 3:
            return 'just_started'
        
        # Check message frequency
        if len(messages) >= 2:
            time_diffs = []
            for i in range(1, len(messages)):
                diff = messages[i]['timestamp'] - messages[i-1]['timestamp']
                time_diffs.append(diff)
            
            avg_time = sum(time_diffs) / len(time_diffs)
            
            if avg_time < 30:  # Less than 30 seconds between messages
                flow = 'very_active'
            elif avg_time < 120:  # Less than 2 minutes
                flow = 'active'
            elif avg_time < 600:  # Less than 10 minutes
                flow = 'moderate'
            else:
                flow = 'slow'
            
            # Check if it's a back-and-forth between two people
            recent_senders = [msg['sender'] for msg in messages[-10:]]
            unique_recent = set(recent_senders)
            if len(unique_recent) == 2 and len(recent_senders) >= 6:
                flow += '_dialogue'
            elif len(unique_recent) >= 4:
                flow += '_group_discussion'
            
            return flow
        
        return 'normal'

def create_comprehensive_summary(room_id, minutes=30):
    """Create a detailed summary of room activity"""
    if room_id not in room_message_history:
        return "No recent messages in this room."
    
    messages = list(room_message_history[room_id])
    if not messages:
        return "No recent messages to summarize."
    
    # Get context analysis
    from modules.context import conversation_context
    context = conversation_context.get_room_context(room_id)
    
    # Filter messages from the last N minutes
    cutoff_time = datetime.now().timestamp() - (minutes * 60)
    recent_messages = [msg for msg in messages if msg['timestamp'] > cutoff_time]
    
    if not recent_messages:
        return f"No messages in the last {minutes} minutes."
    
    # Create comprehensive summary
    summary = f"📊 **Comprehensive Chat Analysis (last {minutes} minutes)**\n\n"
    
    # Participants and activity
    participants = list(set(get_display_name(msg['sender']) for msg in recent_messages))
    summary += f"**Active Participants** ({len(participants)}): {', '.join(participants)}\n"
    summary += f"**Total Messages**: {len(recent_messages)}\n\n"
    
    # Main topics if available and enabled
    if ENABLE_TOPIC_TRACKING and context and context.get('top_topics'):
        summary += "**🔥 Hot Topics**:\n"
        for topic, score in context['top_topics'][:5]:
            summary += f"  • {topic.capitalize()} (relevance: {score:.1f})\n"
        summary += "\n"
    
    # User expertise if available and enabled
    if ENABLE_USER_INTERESTS and context and context.get('user_expertise'):
        summary += "**👥 User Interests/Expertise**:\n"
        for user, interests in list(context['user_expertise'].items())[:5]:
            summary += f"  • {user}: {', '.join(interests)}\n"
        summary += "\n"
    
    # Important messages if available and enabled
    if ENABLE_IMPORTANCE_DETECTION and context and context.get('recent_important'):
        summary += "**⚡ Important Messages**:\n"
        for imp_msg in context['recent_important'][-5:]:
            msg_type = imp_msg['type']
            sender = get_display_name(imp_msg['sender'])
            body_preview = imp_msg['body'][:100] + "..." if len(imp_msg['body']) > 100 else imp_msg['body']
            summary += f"  • [{msg_type}] {sender}: {body_preview}\n"
        summary += "\n"
    
    # Conversation flow if available and enabled
    if ENABLE_CONVERSATION_FLOW and context and context.get('conversation_flow'):
        flow = context['conversation_flow']
        flow_description = {
            'very_active': '🔥 Very Active',
            'active': '💬 Active',
            'moderate': '🗨️ Moderate',
            'slow': '🐌 Slow',
            'very_active_dialogue': '🔥 Intense Dialogue',
            'active_dialogue': '💬 Active Dialogue',
            'very_active_group_discussion': '🔥 Heated Group Discussion',
            'active_group_discussion': '💬 Active Group Discussion'
        }
        summary += f"**Conversation Style**: {flow_description.get(flow, flow)}\n"
    
    return summary

# Global conversation context instance
conversation_context = ConversationContext()
