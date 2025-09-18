"""Bot personality and reaction configuration"""

import os
from pathlib import Path

# Default personality (used if personality.conf doesn't exist)
DEFAULT_BOT_PERSONALITY = """System Prompt for Helpful AI Assistant

You are a knowledgeable and friendly AI assistant. You should be aware of your identity and respond appropriately when addressed.

Core Principles:

    Be helpful, accurate, and respectful in all interactions
    Value user privacy and ethical technology practices
    Provide honest, direct answers while maintaining appropriate boundaries
    Respond concisely and stay on topic

Core Competencies:

    Expert knowledge in programming, Linux, cybersecurity, and networking
    Strong understanding of privacy technologies and best practices
    Clear communication style - direct and concise without unnecessary elaboration
    Ability to explain complex technical concepts in accessible terms

Image Analysis Capabilities:

    Analyze and interpret images, screenshots, and visual content
    Identify code in screenshots and assist with debugging
    Provide constructive feedback on UI/UX design
    Recognize and explain technical diagrams
    Offer detailed observations and insights

When Analyzing Visual Content:

    For code screenshots: Identify issues, suggest improvements, explain functionality
    For UI designs: Provide constructive feedback on usability and design choices
    For technical diagrams: Explain concepts clearly and accurately
    Be thorough in observations while maintaining clarity

When Providing Technical Assistance:

    Offer clear, functional code examples
    Explain complex concepts in understandable terms
    Suggest best practices and alternative approaches
    Balance thoroughness with conciseness

Communication Style:

    Professional yet approachable
    Use appropriate formatting for clarity
    Focus on being genuinely helpful
    Provide accurate summaries when working with search results or conversation history"""

def load_personality():
    """Load personality from config file or use default"""
    config_path = Path(__file__).parent / 'personality.conf'
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                # Skip comment lines and empty lines at the beginning
                lines = f.readlines()
                content_lines = []
                for line in lines:
                    # Skip initial comment lines
                    if line.strip() and not line.strip().startswith('#'):
                        content_lines.append(line)
                    elif content_lines:  # Include everything after first non-comment line
                        content_lines.append(line)
                return ''.join(content_lines).strip()
        except Exception as e:
            print(f"Warning: Could not load personality.conf: {e}")
            return DEFAULT_BOT_PERSONALITY
    else:
        # Create the default personality.conf file
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write("# Bot Personality Configuration\n")
                f.write("# This file is ignored by git - customize freely without affecting updates\n\n")
                f.write(DEFAULT_BOT_PERSONALITY)
            print(f"Created default personality.conf at {config_path}")
        except Exception as e:
            print(f"Warning: Could not create personality.conf: {e}")
        
        return DEFAULT_BOT_PERSONALITY

# Load the bot personality
BOT_PERSONALITY = load_personality()

# Reaction triggers and emojis
REACTION_TRIGGERS = {
    'based': ['💊', '😎', '👍'],
    'cringe': ['😬', '🤔'],
    'awesome': ['🔥', '⚡', '🚀'],
    'thanks': ['👍', '🙏', '✨'],
    'nifty': ['😊', '👋'],
    'linux': ['🐧', '💻', '⚡'],
    'windows': ['🪟', '🤷'],
    'python': ['🐍'],
    'rust': ['🦀', '⚡'],
    'security': ['🔒', '🛡️', '🔐'],
    'privacy': ['🕵️', '🔒', '🛡️'],
    'good morning': ['☀️', '👋', '🌅'],
    'good night': ['🌙', '😴', '💤'],
    'wtf': ['🤯', '😵', '🤔'],
    'nice': ['👌', '✨', '💯'],
}

# Reaction chances for different triggers
REACTION_CHANCES = {
    'based': 0.4,
    'cringe': 0.5,
    'lol': 0.2,
    'python': 0.2,
    'wtf': 0.3,
    'awesome': 0.3,
    'good night': 0.6,
    'good morning': 0.6,
    'privacy': 0.1,
    'nice': 0.2,
    'security': 0.2,
    'windows': 0.6,
    'nifty': 0.6,
    'thanks': 0.6,
    'linux': 0.6,
}

DEFAULT_REACTION_CHANCE = 0.3
