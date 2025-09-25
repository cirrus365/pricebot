"""
Twilio integration for Price Tracker Bot
Handles WhatsApp, Messenger, and Instagram messaging via Twilio
"""
import logging
import asyncio
from datetime import datetime
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from config.settings import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER,
    TWILIO_MESSENGER_PAGE_ID, TWILIO_INSTAGRAM_ACCOUNT_ID,
    TWILIO_WEBHOOK_BASE_URL, TWILIO_WEBHOOK_PORT,
    WHATSAPP_ALLOWED_NUMBERS, MESSENGER_ALLOWED_USERS, INSTAGRAM_ALLOWED_USERS,
    INTEGRATIONS, ENABLE_PRICE_TRACKING, ENABLE_STOCK_MARKET, BOT_USERNAME
)

logger = logging.getLogger(__name__)

class TwilioBot:
    """Twilio bot implementation for WhatsApp, Messenger, and Instagram"""
    
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.app = Flask(__name__)
        # Import here to avoid circular imports
        from modules.price_tracker import price_tracker
        from modules.stock_tracker import stock_tracker
        self.price_tracker = price_tracker
        self.stock_tracker = stock_tracker
        self.setup_routes()
        
    def setup_routes(self):
        """Setup Flask routes for Twilio webhooks"""
        
        @self.app.route('/whatsapp', methods=['POST'])
        def whatsapp_webhook():
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
            response = asyncio.run(self.handle_message(body))
            
            # Send response
            resp = MessagingResponse()
            resp.message(response)
            return Response(str(resp), mimetype='text/xml')
        
        @self.app.route('/messenger', methods=['POST'])
        def messenger_webhook():
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
                            response = asyncio.run(self.handle_message(text))
                            # Send response via Twilio
                            self.send_messenger_message(sender_id, response)
            
            return Response(status=200)
        
        @self.app.route('/instagram', methods=['POST'])
        def instagram_webhook():
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
                            response = asyncio.run(self.handle_message(text))
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
    
    async def handle_message(self, message: str) -> str:
        """Process incoming message and generate response"""
        
        try:
            # Check for commands
            if message.startswith('?'):
                return await self.handle_command(message)
            else:
                return self.get_help_text()
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return "Sorry, I encountered an error processing your message."
    
    async def handle_command(self, command: str) -> str:
        """Handle bot commands"""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()
        
        if cmd in ['?help', '?start']:
            return self.get_help_text()
        
        elif cmd == '?price':
            if not ENABLE_PRICE_TRACKING:
                return "Price tracking feature is not enabled."
            if len(cmd_parts) > 1:
                query = ' '.join(cmd_parts[1:])
                price_response = await self.price_tracker.get_price_response(f"price {query}")
                return price_response or f"Could not fetch price for {query}"
            else:
                return "Usage: ?price <crypto> [currency] or ?price <from> <to>\nExamples: ?price xmr usd, ?price btc, ?price usd aud"
        
        elif cmd == '?xmr':
            if not ENABLE_PRICE_TRACKING:
                return "Price tracking feature is not enabled."
            price_response = await self.price_tracker.get_price_response("price XMR")
            return price_response or "Could not fetch XMR price"
        
        elif cmd == '?stonks':
            if not ENABLE_STOCK_MARKET:
                return "Stock tracking feature is not enabled."
            if len(cmd_parts) > 1:
                ticker = cmd_parts[1]
                stock_response = await self.stock_tracker.get_stock_info(ticker)
                # Clean up formatting for plain text
                stock_response = stock_response.replace("**", "").replace("_", "")
                return stock_response
            else:
                market_summary = await self.stock_tracker.get_market_summary()
                market_summary = market_summary.replace("**", "").replace("_", "")
                return market_summary
        
        else:
            return f"Unknown command: {cmd}. Type ?help for available commands."
    
    def get_help_text(self) -> str:
        """Get help text"""
        help_text = (
            f"👋 Hello! I'm {BOT_USERNAME.capitalize()}, your price tracking bot!\n\n"
            "Available commands:\n"
            "?help - Show this help message\n"
        )
        
        if ENABLE_PRICE_TRACKING:
            help_text += "?price <crypto> [currency] - Get cryptocurrency price\n"
            help_text += "?price <from> <to> - Get exchange rate\n"
            help_text += "?xmr - Quick Monero price check\n"
        
        if ENABLE_STOCK_MARKET:
            help_text += "?stonks <ticker> - Get stock market data\n"
            help_text += "?stonks - Get global market summary\n"
        
        return help_text
    
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
    
    if ENABLE_PRICE_TRACKING:
        logger.info("  Price queries: ?price <crypto> [currency] or ?price <from> <to>")
    
    if ENABLE_STOCK_MARKET:
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
