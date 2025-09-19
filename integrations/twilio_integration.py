"""
Twilio integration for Nifty bot
Handles WhatsApp, Messenger, and Instagram messaging via Twilio
"""
import logging
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional, Dict
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from config.settings import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER,
    TWILIO_MESSENGER_PAGE_ID, TWILIO_INSTAGRAM_ACCOUNT_ID,
    TWILIO_WEBHOOK_BASE_URL, TWILIO_WEBHOOK_PORT,
    WHATSAPP_ALLOWED_NUMBERS, MESSENGER_ALLOWED_USERS, INSTAGRAM_ALLOWED_USERS,
    INTEGRATIONS, MAX_ROOM_HISTORY, ENABLE_PRICE_TRACKING, ENABLE_MEME_GENERATION,
    BOT_USERNAME
)
from modules.llm import get_llm_reply
from modules.price_tracker import price_tracker
from modules.stock_tracker import stock_tracker
from modules.web_search import search_with_jina, needs_web_search
from modules.meme_generator import meme_generator
from modules.world_clock import world_clock
from modules.settings_manager import settings_manager
from utils.helpers import extract_urls_from_message, detect_code_in_message

logger = logging.getLogger(__name__)

# Message history storage
message_history = defaultdict(lambda: deque(maxlen=MAX_ROOM_HISTORY))

# Rate limiting
last_message_time = defaultdict(lambda: datetime.min)
RATE_LIMIT_SECONDS = 2

class TwilioBot:
    """Twilio bot implementation for WhatsApp, Messenger, and Instagram"""
    
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.app = Flask(__name__)
        self.setup_routes()
        
    def setup_routes(self):
        """Setup Flask routes for Twilio webhooks"""
        
        @self.app.route('/whatsapp', methods=['POST'])
        async def whatsapp_webhook():
            """Handle incoming WhatsApp messages"""
            if not INTEGRATIONS.get('whatsapp', False):
                return Response(status=404)
            
            from_number = request.values.get('From', '')
            body = request.values.get('Body', '')
            
            # Check if number is allowed
            if not self.is_whatsapp_authorized(from_number):
                logger.warning(f"Unauthorized WhatsApp message from {from_number}")
                return Response(status=403)
            
            # Process message
            response = await self.handle_message(from_number, body, 'whatsapp')
            
            # Send response
            resp = MessagingResponse()
            resp.message(response)
            return Response(str(resp), mimetype='text/xml')
        
        @self.app.route('/messenger', methods=['POST'])
        async def messenger_webhook():
            """Handle incoming Messenger messages"""
            if not INTEGRATIONS.get('messenger', False):
                return Response(status=404)
            
            # Parse Messenger webhook data
            data = request.get_json()
            if not data or 'entry' not in data:
                return Response(status=400)
            
            for entry in data['entry']:
                for messaging_event in entry.get('messaging', []):
                    sender_id = messaging_event['sender']['id']
                    
                    # Check if user is allowed
                    if not self.is_messenger_authorized(sender_id):
                        logger.warning(f"Unauthorized Messenger message from {sender_id}")
                        continue
                    
                    if 'message' in messaging_event:
                        text = messaging_event['message'].get('text', '')
                        if text:
                            # Process message
                            response = await self.handle_message(sender_id, text, 'messenger')
                            # Send response via Twilio
                            self.send_messenger_message(sender_id, response)
            
            return Response(status=200)
        
        @self.app.route('/instagram', methods=['POST'])
        async def instagram_webhook():
            """Handle incoming Instagram messages"""
            if not INTEGRATIONS.get('instagram', False):
                return Response(status=404)
            
            # Parse Instagram webhook data (similar to Messenger)
            data = request.get_json()
            if not data or 'entry' not in data:
                return Response(status=400)
            
            for entry in data['entry']:
                for messaging_event in entry.get('messaging', []):
                    sender_id = messaging_event['sender']['id']
                    
                    # Check if user is allowed
                    if not self.is_instagram_authorized(sender_id):
                        logger.warning(f"Unauthorized Instagram message from {sender_id}")
                        continue
                    
                    if 'message' in messaging_event:
                        text = messaging_event['message'].get('text', '')
                        if text:
                            # Process message
                            response = await self.handle_message(sender_id, text, 'instagram')
                            # Send response via Twilio
                            self.send_instagram_message(sender_id, response)
            
            return Response(status=200)
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return Response("OK", status=200)
    
    def is_whatsapp_authorized(self, phone_number: str) -> bool:
        """Check if WhatsApp number is authorized"""
        if not WHATSAPP_ALLOWED_NUMBERS:
            return True  # Allow all if no restrictions set
        
        # Clean the phone number
        clean_number = phone_number.replace('whatsapp:', '').strip()
        return clean_number in WHATSAPP_ALLOWED_NUMBERS
    
    def is_messenger_authorized(self, user_id: str) -> bool:
        """Check if Messenger user is authorized"""
        if not MESSENGER_ALLOWED_USERS:
            return True  # Allow all if no restrictions set
        return user_id in MESSENGER_ALLOWED_USERS
    
    def is_instagram_authorized(self, user_id: str) -> bool:
        """Check if Instagram user is authorized"""
        if not INSTAGRAM_ALLOWED_USERS:
            return True  # Allow all if no restrictions set
        return user_id in INSTAGRAM_ALLOWED_USERS
    
    def store_message(self, chat_id: str, username: str, message: str, platform: str):
        """Store message in history"""
        message_history[f"{platform}:{chat_id}"].append({
            'username': username,
            'message': message,
            'timestamp': datetime.now()
        })
    
    def get_conversation_context(self, chat_id: str, platform: str) -> str:
        """Get recent conversation context"""
        history = message_history[f"{platform}:{chat_id}"]
        if not history:
            return ""
        
        context_messages = []
        for msg in list(history)[-10:]:  # Last 10 messages
            context_messages.append(f"{msg['username']}: {msg['message']}")
        
        return "\n".join(context_messages)
    
    async def handle_message(self, sender_id: str, message: str, platform: str) -> str:
        """Process incoming message and generate response"""
        
        # Rate limiting
        now = datetime.now()
        last_time = last_message_time[f"{platform}:{sender_id}"]
        if (now - last_time).total_seconds() < RATE_LIMIT_SECONDS:
            return "Please wait a moment before sending another message."
        last_message_time[f"{platform}:{sender_id}"] = now
        
        # Store the message
        self.store_message(sender_id, sender_id, message, platform)
        
        try:
            # Check for clock command
            if message.startswith('?clock'):
                location = message[6:].strip() if len(message) > 6 else ""
                return await world_clock.handle_clock_command(location)
            
            # Check for meme command
            if message.startswith('?meme '):
                if not settings_manager.is_meme_enabled():
                    return "Meme generation feature is not enabled. An authorized user can enable it with: ?setting meme on"
                # Convert ?meme to !meme for the meme generator
                meme_command = message.replace('?meme', '!meme', 1)
                meme_url, caption = await meme_generator.handle_meme_command(meme_command)
                if meme_url:
                    # For platforms that support images, return URL with caption
                    return f"{caption}\n\nView meme: {meme_url}"
                else:
                    return caption or "Failed to generate meme."
            
            # Check for other commands
            if message.startswith('?'):
                return await self.handle_command(message, sender_id, platform)
            
            # Get conversation context
            context = self.get_conversation_context(sender_id, platform)
            
            # Check if web search is needed
            search_results = None
            if await needs_web_search(message):
                search_results = await search_with_jina(message)
            
            # Generate response
            response = await get_llm_reply(
                prompt=message,
                context=context,
                room_id=f"{platform}:{sender_id}",
                url_contents=search_results
            )
            
            # Store bot response
            self.store_message(sender_id, BOT_USERNAME.capitalize(), response, platform)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling {platform} message: {e}")
            return "Sorry, I encountered an error processing your message."
    
    async def handle_command(self, command: str, sender_id: str, platform: str) -> str:
        """Handle bot commands"""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd in ['?help', '?start']:
            return self.get_help_text(platform)
        
        elif cmd == '?clock':
            location = ' '.join(cmd_parts[1:]) if len(cmd_parts) > 1 else ""
            return await world_clock.handle_clock_command(location)
        
        elif cmd == '?price':
            if not settings_manager.get_setting_value('price_tracking'):
                return "Price tracking feature is not enabled. An authorized user can enable it with: ?setting price_tracking on"
            if len(cmd_parts) > 1:
                query = ' '.join(cmd_parts[1:])
                price_response = await price_tracker.get_price_response(f"price {query}")
                return price_response or f"Could not fetch price for {query}"
            else:
                return "Usage: ?price <crypto> [currency] or ?price <from> <to>\nExamples: ?price xmr usd, ?price btc, ?price usd aud"
        
        elif cmd == '?stonks':
            if not settings_manager.get_setting_value('stock_tracking'):
                return "Stock tracking feature is not enabled. An authorized user can enable it with: ?setting stock_tracking on"
            if len(cmd_parts) > 1:
                ticker = cmd_parts[1]
                stock_response = await stock_tracker.get_stock_info(ticker)
                # Clean up formatting for plain text
                stock_response = stock_response.replace("**", "").replace("_", "")
                return stock_response
            else:
                market_summary = await stock_tracker.get_market_summary()
                market_summary = market_summary.replace("**", "").replace("_", "")
                return market_summary
        
        elif cmd == '?stats':
            history_key = f"{platform}:{sender_id}"
            message_count = len(message_history[history_key])
            return f"📊 Stats:\n• Messages in history: {message_count}\n• Platform: {platform.title()}"
        
        elif cmd == '?reset':
            message_history[f"{platform}:{sender_id}"].clear()
            return "✅ Conversation history cleared!"
        
        else:
            return f"Unknown command: {cmd}. Type ?help for available commands."
    
    def get_help_text(self, platform: str) -> str:
        """Get platform-specific help text"""
        base_help = (
            f"👋 Hello! I'm {BOT_USERNAME.capitalize()}, your AI assistant on {platform.title()}!\n\n"
            "Available commands:\n"
            "?help - Show this help message\n"
            "?clock <city/country> - Get world time\n"
            "?clock - Get current UTC time\n"
            "?stats - Show conversation statistics\n"
            "?reset - Clear conversation history\n"
        )
        
        if settings_manager.get_setting_value('price_tracking'):
            base_help += "?price <crypto> [currency] - Get cryptocurrency price\n"
            base_help += "?price <from> <to> - Get exchange rate\n"
        
        if settings_manager.get_setting_value('stock_tracking'):
            base_help += "?stonks <ticker> - Get stock market data\n"
            base_help += "?stonks - Get global market summary\n"
        
        if settings_manager.is_meme_enabled():
            base_help += "?meme <topic> - Generate a meme with AI captions\n"
        
        base_help += "\nJust send me a message to chat!"
        
        return base_help
    
    def send_messenger_message(self, recipient_id: str, message: str):
        """Send message via Messenger using Twilio"""
        try:
            self.client.messages.create(
                body=message,
                from_=f"messenger:{TWILIO_MESSENGER_PAGE_ID}",
                to=f"messenger:{recipient_id}"
            )
        except Exception as e:
            logger.error(f"Error sending Messenger message: {e}")
    
    def send_instagram_message(self, recipient_id: str, message: str):
        """Send message via Instagram using Twilio"""
        try:
            self.client.messages.create(
                body=message,
                from_=f"instagram:{TWILIO_INSTAGRAM_ACCOUNT_ID}",
                to=f"instagram:{recipient_id}"
            )
        except Exception as e:
            logger.error(f"Error sending Instagram message: {e}")
    
    def run(self):
        """Run the Flask app"""
        self.app.run(
            host='0.0.0.0',
            port=TWILIO_WEBHOOK_PORT,
            debug=False
        )

async def run_twilio_bot():
    """Run the Twilio bot for WhatsApp, Messenger, and Instagram"""
    
    # Check if credentials are configured
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("Twilio credentials not configured!")
        return
    
    # Check which platforms are enabled
    whatsapp_enabled = INTEGRATIONS.get('whatsapp', False)
    messenger_enabled = INTEGRATIONS.get('messenger', False)
    instagram_enabled = INTEGRATIONS.get('instagram', False)
    
    enabled_platforms = []
    if whatsapp_enabled:
        enabled_platforms.append("WhatsApp")
        if not TWILIO_WHATSAPP_NUMBER:
            logger.warning("WhatsApp enabled but TWILIO_WHATSAPP_NUMBER not configured")
    
    if messenger_enabled:
        enabled_platforms.append("Messenger")
        if not TWILIO_MESSENGER_PAGE_ID:
            logger.warning("Messenger enabled but TWILIO_MESSENGER_PAGE_ID not configured")
    
    if instagram_enabled:
        enabled_platforms.append("Instagram")
        if not TWILIO_INSTAGRAM_ACCOUNT_ID:
            logger.warning("Instagram enabled but TWILIO_INSTAGRAM_ACCOUNT_ID not configured")
    
    if not enabled_platforms:
        logger.error("No Twilio platforms enabled!")
        return
    
    logger.info(f"Starting Twilio bot for: {', '.join(enabled_platforms)}")
    logger.info(f"Webhook server will run on port {TWILIO_WEBHOOK_PORT}")
    logger.info(f"Configure your Twilio webhooks to:")
    if whatsapp_enabled:
        logger.info(f"  WhatsApp: {TWILIO_WEBHOOK_BASE_URL}/whatsapp")
    if messenger_enabled:
        logger.info(f"  Messenger: {TWILIO_WEBHOOK_BASE_URL}/messenger")
    if instagram_enabled:
        logger.info(f"  Instagram: {TWILIO_WEBHOOK_BASE_URL}/instagram")
    
    logger.info("  World clock: ?clock <city/country> for world time")
    
    if settings_manager.is_meme_enabled():
        logger.info("  Meme generation: ?meme <topic> command enabled")
    
    if settings_manager.get_setting_value('price_tracking'):
        logger.info("  Price queries: ?price <crypto> [currency] or ?price <from> <to>")
    
    if settings_manager.get_setting_value('stock_tracking'):
        logger.info("  Stock market: ?stonks <ticker> for stock data")
    
    # Create and run the bot
    bot = TwilioBot()
    
    # Run Flask in a separate thread to not block the async loop
    import threading
    flask_thread = threading.Thread(target=bot.run, daemon=True)
    flask_thread.start()
    
    # Keep the async task running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Twilio bot shutting down...")
        raise
