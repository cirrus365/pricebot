"""
Telegram integration for Price Tracker Bot
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode, ChatAction
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, TELEGRAM_ALLOWED_GROUPS, BOT_USERNAME, ENABLE_PRICE_TRACKING, ENABLE_STOCK_MARKET

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot implementation for Price Tracker"""
    
    def __init__(self):
        self.application = None
        # Import here to avoid circular imports
        from modules.price_tracker import price_tracker
        from modules.stock_tracker import stock_tracker
        self.price_tracker = price_tracker
        self.stock_tracker = stock_tracker
        
    def is_authorized(self, update: Update) -> bool:
        """Check if user/group is authorized to use the bot"""
        user_id = str(update.effective_user.id) if update.effective_user else None
        chat_id = str(update.effective_chat.id) if update.effective_chat else None
        
        # If no restrictions are set, allow all
        if not TELEGRAM_ALLOWED_USERS and not TELEGRAM_ALLOWED_GROUPS:
            return True
            
        # Check if user is in allowed users
        if user_id and TELEGRAM_ALLOWED_USERS and user_id in TELEGRAM_ALLOWED_USERS:
            return True
            
        # Check if chat is in allowed groups
        if chat_id and TELEGRAM_ALLOWED_GROUPS and chat_id in TELEGRAM_ALLOWED_GROUPS:
            return True
            
        return False
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        welcome_message = (
            f"👋 Hey! I'm {BOT_USERNAME.capitalize()}, your price tracking bot!\n\n"
            "Here's what I can do:\n"
            "💰 /price <crypto> [currency] - Get prices\n"
            "📊 /stonks <ticker> - Get stock market data\n"
            "❓ /help - Show all commands\n\n"
            "Let's track some prices! 🚀"
        )
        
        await update.message.reply_text(welcome_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        help_text = (
            f"🤖 *{BOT_USERNAME.capitalize()} Bot Commands*\n\n"
            "*Price Commands:*\n"
            "💰 /price <crypto> [currency] - Get cryptocurrency price\n"
            "/price <from> <to> - Get exchange rate\n"
            "/xmr - Quick Monero price check\n\n"
            "*Stock Market:*\n"
            "📊 /stonks <ticker> - Get stock information\n"
            "/stonks - Get market summary\n\n"
            "*Other:*\n"
            "❓ /help - Show this message\n"
            "👋 /start - Welcome message\n"
            "🏓 /ping - Check bot status\n"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def stonks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stonks command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
        
        if not ENABLE_STOCK_MARKET:
            await update.message.reply_text("Stock tracking feature is not enabled.")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        if not context.args:
            # No ticker provided, show market summary
            response = await self.stock_tracker.get_market_summary()
        else:
            # Get stock info for the provided ticker
            ticker = context.args[0]
            response = await self.stock_tracker.get_stock_info(ticker)
        
        # Format response for Telegram markdown
        response = response.replace("**", "*")  # Convert bold markers
        response = response.replace("_", "")    # Remove italics to avoid conflicts
        
        # Split long messages if needed
        if len(response) > 4096:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
        
        if not ENABLE_PRICE_TRACKING:
            await update.message.reply_text("Price tracking feature is not enabled.")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        query = " ".join(context.args) if context.args else "XMR"
        response = await self.price_tracker.get_price_response(f"price {query}")
        
        if response:
            message = f"💰 *Price Information*\n\n{response}"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Couldn't fetch price for {query}")
            
    async def xmr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /xmr command - quick Monero price check"""
        if not ENABLE_PRICE_TRACKING:
            await update.message.reply_text("Price tracking feature is not enabled.")
            return
        
        context.args = ["XMR"]
        await self.price_command(update, context)
        
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ping command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        await update.message.reply_text("🏓 Pong! Bot is online and responsive!")
        
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ An error occurred. Please try again later.")

async def run_telegram_bot():
    """Run the Telegram bot"""
    # Check for required Telegram credentials
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Telegram bot token not configured. Please set TELEGRAM_BOT_TOKEN in .env file")
        print("\n❌ ERROR: Telegram bot token missing!")
        print("Please configure TELEGRAM_BOT_TOKEN in your .env file")
        print("Get your bot token from @BotFather on Telegram")
        return
        
    try:
        bot = TelegramBot()
        
        # Create application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        bot.application = application
        
        # Add command handlers
        application.add_handler(CommandHandler("start", bot.start_command))
        application.add_handler(CommandHandler("help", bot.help_command))
        application.add_handler(CommandHandler("price", bot.price_command))
        application.add_handler(CommandHandler("xmr", bot.xmr_command))
        application.add_handler(CommandHandler("stonks", bot.stonks_command))
        application.add_handler(CommandHandler("ping", bot.ping_command))
        
        # Add error handler
        application.add_error_handler(bot.error_handler)
        
        print("=" * 50)
        print(f"💰 Price Tracker Bot - Telegram Integration Active!")
        print("=" * 50)
        print("✅ Telegram bot starting...")
        print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
        print("📝 Commands: /help to see all commands")
        print("💰 Price tracking: /price <crypto> [currency] or /price <from> <to>")
        print("📊 Stock market: /stonks <ticker> for stock data")
        if TELEGRAM_ALLOWED_USERS:
            print(f"👤 Allowed users: {', '.join(TELEGRAM_ALLOWED_USERS)}")
        if TELEGRAM_ALLOWED_GROUPS:
            print(f"👥 Allowed groups: {', '.join(TELEGRAM_ALLOWED_GROUPS)}")
        print("=" * 50)
        
        # Start the bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        raise
