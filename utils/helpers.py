"""Helper utility functions"""
import re
from urllib.parse import quote, urlparse

def get_display_name(user_id):
    """Extract display name from user ID"""
    # Remove the @ and domain parts
    if '@' in user_id:
        name = user_id.split(':')[0][1:]  # Remove @ and everything after :
        return name
    return user_id

def extract_urls_from_message(message):
    """Extract all URLs from a message"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+(?:[.,!?;](?=\s|$))?'
    urls = re.findall(url_pattern, message)
    return [url.rstrip('.,!?;') for url in urls]
