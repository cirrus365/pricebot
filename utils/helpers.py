"""Helper utility functions"""
import re
from urllib.parse import quote, urlparse
from config.settings import FILTERED_WORDS

def filter_bot_triggers(text):
    """Remove or replace words that might trigger other bots"""
    filtered_text = text
    
    for word in FILTERED_WORDS:
        # Replace any variation (case-insensitive) with a safe alternative
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        filtered_text = pattern.sub("[another bot]", filtered_text)
    
    return filtered_text

def get_display_name(user_id):
    """Extract display name from user ID"""
    # Remove the @ and domain parts
    if '@' in user_id:
        name = user_id.split(':')[0][1:]  # Remove @ and everything after :
        return name
    return user_id

def detect_language_from_url(url):
    """Detect programming language from file extension"""
    extensions = {
        '.py': 'python',
        '.js': 'javascript',
        '.rs': 'rust',
        '.c': 'c',
        '.cpp': 'cpp',
        '.java': 'java',
        '.sh': 'bash',
        '.go': 'go',
        '.rb': 'ruby'
    }
    
    for ext, lang in extensions.items():
        if url.endswith(ext):
            return lang
    return 'text'

def extract_urls_from_message(message):
    """Extract all URLs from a message"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+(?:[.,!?;](?=\s|$))?'
    urls = re.findall(url_pattern, message)
    return [url.rstrip('.,!?;') for url in urls]

def detect_code_in_message(message):
    """Detect if message contains code blocks or code-related content"""
    code_indicators = [
        '```',  # Code blocks
        '`',    # Inline code
        'def ', 'class ', 'function ', 'const ', 'let ', 'var ',  # Common keywords
        'import ', 'from ', 'export ',
        '()', '=>', '{}', '[]',  # Common syntax
        'error:', 'exception:', 'traceback:',  # Error messages
    ]
    return any(indicator in message.lower() for indicator in code_indicators)
