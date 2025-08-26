"""
Meme generation module for Nifty Bot
Uses Imgflip API to create memes with LLM-generated captions
"""
import logging
import random
import aiohttp
import asyncio
from typing import Optional, Dict, Tuple
from config.settings import IMGFLIP_USERNAME, IMGFLIP_PASSWORD, LLM_TIMEOUT
from modules.llm import get_llm_reply

logger = logging.getLogger(__name__)

# Popular meme templates with their Imgflip IDs
MEME_TEMPLATES = {
    'drake': {'id': '181913649', 'name': 'Drake Hotline Bling', 'boxes': 2},
    'distracted': {'id': '112126428', 'name': 'Distracted Boyfriend', 'boxes': 3},
    'expanding': {'id': '93895088', 'name': 'Expanding Brain', 'boxes': 4},
    'button': {'id': '119139145', 'name': 'Blank Nut Button', 'boxes': 2},
    'change': {'id': '129242436', 'name': 'Change My Mind', 'boxes': 2},
    'disaster': {'id': '97984', 'name': 'Disaster Girl', 'boxes': 2},
    'everywhere': {'id': '91538330', 'name': 'X, X Everywhere', 'boxes': 2},
    'aliens': {'id': '101470', 'name': 'Ancient Aliens', 'boxes': 2},
    'success': {'id': '61544', 'name': 'Success Kid', 'boxes': 2},
    'allthethings': {'id': '61533', 'name': 'X All The Things', 'boxes': 2},
    'doge': {'id': '8072285', 'name': 'Doge', 'boxes': 5},
    'badluck': {'id': '61585', 'name': 'Bad Luck Brian', 'boxes': 2},
    'onedoesnot': {'id': '61579', 'name': 'One Does Not Simply', 'boxes': 2},
    'picard': {'id': '1509839', 'name': 'Captain Picard Facepalm', 'boxes': 2},
    'interesting': {'id': '61532', 'name': 'The Most Interesting Man', 'boxes': 2},
    'twobuttons': {'id': '87743020', 'name': 'Two Buttons', 'boxes': 3},
    'scroll': {'id': '123999232', 'name': 'The Scroll Of Truth', 'boxes': 2},
    'panik': {'id': '226297822', 'name': 'Panik Kalm Panik', 'boxes': 3},
    'always': {'id': '252600902', 'name': 'Always Has Been', 'boxes': 2},
    'butterfly': {'id': '100777631', 'name': 'Is This A Pigeon', 'boxes': 3},
}

class MemeGenerator:
    """Handles meme generation using Imgflip API and LLM"""
    
    def __init__(self):
        self.imgflip_url = "https://api.imgflip.com/caption_image"
        self.session = None
        
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            
    async def generate_meme_captions(self, user_input: str, template_name: str, num_boxes: int) -> Optional[list]:
        """Use LLM to generate witty meme captions based on user input"""
        
        prompt = f"""Generate funny and witty meme captions for the "{template_name}" meme template based on this topic/text: "{user_input}"

This meme template needs exactly {num_boxes} caption(s).
Make the captions short, punchy, and meme-appropriate.
Match the typical format and humor style of this meme template.

Return ONLY the captions, one per line, no numbering or extra text.
Keep each caption under 50 characters if possible."""

        try:
            response = await get_llm_reply(prompt)
            if not response:
                return None
                
            # Parse the response into individual captions
            captions = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            # Ensure we have the right number of captions
            if len(captions) < num_boxes:
                # Pad with empty strings if not enough
                captions.extend([''] * (num_boxes - len(captions)))
            elif len(captions) > num_boxes:
                # Trim if too many
                captions = captions[:num_boxes]
                
            return captions
            
        except Exception as e:
            logger.error(f"Error generating meme captions: {e}")
            return None
            
    async def select_meme_template(self, user_input: str) -> Tuple[str, Dict]:
        """Select appropriate meme template based on user input or randomly"""
        
        # Keywords for template selection
        template_keywords = {
            'drake': ['prefer', 'better', 'vs', 'instead', 'choice'],
            'distracted': ['distracted', 'looking', 'ignore', 'attractive'],
            'expanding': ['smart', 'brain', 'intelligence', 'levels', 'progression'],
            'button': ['press', 'button', 'tempting', 'must'],
            'change': ['opinion', 'mind', 'convince', 'prove', 'wrong'],
            'success': ['success', 'win', 'achievement', 'finally'],
            'doge': ['wow', 'such', 'very', 'much', 'doge'],
            'panik': ['panic', 'calm', 'worry', 'relief', 'stress'],
            'always': ['always', 'been', 'truth', 'reveal'],
            'twobuttons': ['choose', 'decision', 'dilemma', 'both'],
        }
        
        # Check for keyword matches
        lower_input = user_input.lower()
        for template_key, keywords in template_keywords.items():
            if any(keyword in lower_input for keyword in keywords):
                return template_key, MEME_TEMPLATES[template_key]
                
        # Random selection if no keyword match
        template_key = random.choice(list(MEME_TEMPLATES.keys()))
        return template_key, MEME_TEMPLATES[template_key]
        
    async def create_meme(self, user_input: str) -> Optional[str]:
        """Create a meme based on user input"""
        
        # Check if credentials are configured
        if not IMGFLIP_USERNAME or not IMGFLIP_PASSWORD:
            logger.error("Imgflip credentials not configured")
            return None
            
        try:
            # Select meme template
            template_key, template_info = await self.select_meme_template(user_input)
            logger.info(f"Selected meme template: {template_info['name']}")
            
            # Generate captions using LLM
            captions = await self.generate_meme_captions(
                user_input, 
                template_info['name'],
                template_info['boxes']
            )
            
            if not captions:
                logger.error("Failed to generate captions")
                return None
                
            # Prepare API request data
            data = {
                'template_id': template_info['id'],
                'username': IMGFLIP_USERNAME,
                'password': IMGFLIP_PASSWORD,
            }
            
            # Add captions as text0, text1, etc.
            for i, caption in enumerate(captions):
                data[f'text{i}'] = caption
                
            # Make API request to Imgflip
            session = await self.get_session()
            async with session.post(self.imgflip_url, data=data) as response:
                if response.status != 200:
                    logger.error(f"Imgflip API error: {response.status}")
                    return None
                    
                result = await response.json()
                
                if result.get('success'):
                    meme_url = result['data']['url']
                    logger.info(f"Meme created successfully: {meme_url}")
                    return meme_url
                else:
                    logger.error(f"Imgflip API error: {result.get('error_message', 'Unknown error')}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error("Timeout creating meme")
            return None
        except Exception as e:
            logger.error(f"Error creating meme: {e}")
            return None
            
    async def handle_meme_command(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Handle meme command and return meme URL and caption text
        Returns: (meme_url, caption_text) or (None, error_message)
        """
        
        # Check if credentials are configured
        if not IMGFLIP_USERNAME or not IMGFLIP_PASSWORD:
            return None, "Meme generation is not configured. Please set IMGFLIP_USERNAME and IMGFLIP_PASSWORD."
            
        # Extract the meme topic/text from command
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            return None, "Please provide a topic or text for the meme. Usage: !meme <topic or text>"
            
        meme_topic = parts[1].strip()
        
        if not meme_topic:
            return None, "Please provide a topic or text for the meme. Usage: !meme <topic or text>"
            
        # Create the meme
        meme_url = await self.create_meme(meme_topic)
        
        if meme_url:
            caption = f"Here's your meme about: {meme_topic}"
            return meme_url, caption
        else:
            return None, "Sorry, I couldn't create a meme right now. Please try again later."

# Global instance
meme_generator = MemeGenerator()
