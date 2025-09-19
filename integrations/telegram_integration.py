"""
Telegram integration for Chatbot
"""
import logging
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, TELEGRAM_ALLOWED_GROUPS, BOT_USERNAME, ENABLE_MEME_GENERATION, ENABLE_PRICE_TRACKING
from config.personality import BOT_PERSONALITY
from modules.llm import get_llm_reply
from modules.price_tracker import price_tracker
from modules.stock_tracker import stock_tracker
from modules.web_search import search_with_jina, fetch_url_content
from modules.meme_generator import meme_generator
from modules.world_clock import world_clock
from modules.settings_manager import settings_manager
from utils.formatting import format_code_blocks
from utils.helpers import extract_urls_from_message, detect_code_in_message

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot implementation for Chatbot"""
    
    def __init__(self):
        self.conversation_history = {}  # chat_id -> list of messages
        self.max_history = 20
        self.application = None
        
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
        
    def store_message(self, chat_id: int, username: str, message: str):
        """Store message in conversation history"""
        if chat_id not in self.conversation_history:
            self.conversation_history[chat_id] = []
            
        self.conversation_history[chat_id].append({
            'username': username,
            'message': message
        })
        
        # Trim history
        if len(self.conversation_history[chat_id]) > self.max_history:
            self.conversation_history[chat_id] = self.conversation_history[chat_id][-self.max_history:]
            
    def get_conversation_context(self, chat_id: int) -> str:
        """Get conversation context for a chat"""
        if chat_id not in self.conversation_history:
            return ""
            
        context_messages = []
        for msg in self.conversation_history[chat_id][-10:]:  # Last 10 messages
            context_messages.append(f"{msg['username']}: {msg['message']}")
            
        return "\n".join(context_messages)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        welcome_message = (
            f"👋 Hey! I'm {BOT_USERNAME.capitalize()}, your digital assistant!\n\n"
            "Here's what I can do:\n"
            "💬 Just chat with me normally\n"
            "🕐 /clock <city/country> - Get world time\n"
            "💰 /price <crypto> [currency] - Get prices\n"
            "📊 /stonks <ticker> - Get stock market data\n"
            "🔍 /search <query> - Search the web\n"
        )
        
        if settings_manager.is_meme_enabled():
            welcome_message += "🎨 /meme <topic> - Generate memes with AI\n"
            
        welcome_message += (
            "⚙️ /setting - Manage bot settings\n"
            "📊 /stats - Bot statistics\n"
            "❓ /help - Show all commands\n\n"
            "Let's get started! Ask me anything! 🚀"
        )
        
        await update.message.reply_text(welcome_message)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        help_text = (
            f"🤖 *{BOT_USERNAME.capitalize()} Bot Commands*\n\n"
            "*Chat Commands:*\n"
            "💬 Just send me a message to chat!\n"
            "/reset - Clear conversation history\n\n"
            "*Time & Date:*\n"
            "🕐 /clock <city/country> - Get current time for a location\n"
            "/clock - Get current UTC time\n\n"
            "*Price Commands:*\n"
            "💰 /price <crypto> [currency] - Get cryptocurrency price\n"
            "/price <from> <to> - Get exchange rate\n"
            "/xmr - Quick Monero price check\n\n"
            "*Stock Market:*\n"
            "📊 /stonks <ticker> - Get detailed stock information\n"
            "/stonks - Get global market summary\n\n"
        )
        
        if settings_manager.is_meme_enabled():
            help_text += (
                "*Meme Generation:*\n"
                "🎨 /meme <topic> - Generate a meme with AI captions\n\n"
            )
            
        help_text += (
            "*Search & Info:*\n"
            "🔍 /search <query> - Search the web\n"
            "📊 /stats - Bot statistics\n"
            "🏓 /ping - Check bot latency\n\n"
            "*Settings:*\n"
            "⚙️ /setting - View all settings\n"
            "/setting <name> <value> - Change a setting\n"
            "/setting whitelist add/remove <username> - Manage whitelist\n\n"
            "*Other:*\n"
            "❓ /help - Show this message\n"
            "👋 /start - Welcome message\n"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def setting_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setting command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
        
        user_id = str(update.effective_user.id) if update.effective_user else None
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Handle setting command
        response = await settings_manager.handle_setting_command(
            args=context.args if context.args else [],
            user_id=user_id,
            platform='telegram'
        )
        
        # Format response for Telegram markdown
        response = response.replace("**", "*")  # Convert bold markers
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    async def clock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clock command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Get location from command arguments
        location = " ".join(context.args) if context.args else ""
        
        # Get time for location
        response = await world_clock.handle_clock_command(location)
        
        # Format response for Telegram markdown
        response = response.replace("**", "*")  # Convert bold markers
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    async def stonks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stonks command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
        
        # Check if stock tracking is enabled
        if not settings_manager.get_setting_value('stock_tracking'):
            await update.message.reply_text("Stock tracking feature is not enabled. An authorized user can enable it with: /setting stock_tracking on")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        if not context.args:
            # No ticker provided, show market summary
            response = await stock_tracker.get_market_summary()
        else:
            # Get stock info for the provided ticker
            ticker = context.args[0]
            response = await stock_tracker.get_stock_info(ticker)
        
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
        
    async def meme_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /meme command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        if not settings_manager.is_meme_enabled():
            await update.message.reply_text("Meme generation feature is not enabled. An authorized user can enable it with: /setting meme on")
            return
            
        if not context.args:
            await update.message.reply_text("Please provide a topic for the meme. Usage: `/meme <topic>`", parse_mode=ParseMode.MARKDOWN)
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        topic = " ".join(context.args)
        
        # Generate the meme
        meme_url, caption = await meme_generator.handle_meme_command(f"!meme {topic}")
        
        if meme_url:
            # Send the meme as a photo with caption
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=meme_url,
                    caption=f"🎨 {caption}\n\n_Topic: {topic}_",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                # Fallback to sending URL if photo fails
                logger.error(f"Failed to send photo: {e}")
                await update.message.reply_text(
                    f"🎨 {caption}\n\n[View Meme]({meme_url})\n\n_Topic: {topic}_",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(caption or "Failed to generate meme. Please try again.")
        
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
        
        # Check if price tracking is enabled
        if not settings_manager.get_setting_value('price_tracking'):
            await update.message.reply_text("Price tracking feature is not enabled. An authorized user can enable it with: /setting price_tracking on")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        query = " ".join(context.args) if context.args else "XMR"
        response = await price_tracker.get_price_response(f"price {query}")
        
        if response:
            message = f"💰 *Price Information*\n\n{response}"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Couldn't fetch price for {query}")
            
    async def xmr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /xmr command - quick Monero price check"""
        # Check if price tracking is enabled
        if not settings_manager.get_setting_value('price_tracking'):
            await update.message.reply_text("Price tracking feature is not enabled. An authorized user can enable it with: /setting price_tracking on")
            return
        
        context.args = ["XMR"]
        await self.price_command(update, context)
        
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
        
        if not settings_manager.is_web_search_enabled():
            await update.message.reply_text("Web search feature is not enabled. An authorized user can enable it with: /setting search on")
            return
            
        if not context.args:
            await update.message.reply_text("Please provide a search query. Example: /search Python tutorials")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        query = " ".join(context.args)
        search_results = await search_with_jina(query, num_results=3)
        
        if search_results:
            message = f"🔍 *Search Results for:* {query}\n\n{search_results}"
            # Split long messages
            if len(message) > 4096:
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ No search results found.")
            
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        stats_message = (
            f"📊 *{BOT_USERNAME.capitalize()} Bot Statistics*\n\n"
            f"💬 Active Chats: {len(self.conversation_history)}\n"
            f"📝 Total Messages Tracked: {sum(len(h) for h in self.conversation_history.values())}\n"
            f"🧠 Max History per Chat: {self.max_history} messages\n"
            f"✅ Bot Status: Online\n\n"
            f"*Features:*\n"
            f"• Meme Generation: {'✅ Enabled' if settings_manager.is_meme_enabled() else '❌ Disabled'}\n"
            f"• Web Search: {'✅ Enabled' if settings_manager.is_web_search_enabled() else '❌ Disabled'}\n"
            f"• Price Tracking: {'✅ Enabled' if settings_manager.get_setting_value('price_tracking') else '❌ Disabled'}\n"
            f"• Stock Tracking: {'✅ Enabled' if settings_manager.get_setting_value('stock_tracking') else '❌ Disabled'}\n"
            f"• Auto-Invite: {'✅ Enabled' if settings_manager.is_auto_invite_enabled() else '❌ Disabled'}\n\n"
            f"*LLM Settings:*\n"
            f"• Main Model: {settings_manager.get_setting_value('main_llm')}\n"
            f"• Fallback Model: {settings_manager.get_setting_value('fallback_llm') or 'None'}"
        )
        await update.message.reply_text(stats_message, parse_mode=ParseMode.MARKDOWN)
        
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ping command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        await update.message.reply_text("🏓 Pong! Bot is online and responsive!")
        
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command - clear conversation history"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        chat_id = update.effective_chat.id
        if chat_id in self.conversation_history:
            self.conversation_history[chat_id] = []
            await update.message.reply_text("🧹 Conversation history cleared!")
        else:
            await update.message.reply_text("No conversation history to clear.")
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        message_text = update.message.text
        chat_id = update.effective_chat.id
        username = update.effective_user.username or update.effective_user.first_name or "User"
        
        # Store message in history
        self.store_message(chat_id, username, message_text)
        
        # Get conversation context
        context_str = self.get_conversation_context(chat_id)
        
        # Check for URLs in message (only if web search is enabled)
        urls = extract_urls_from_message(message_text)
        url_contents = None
        if urls and settings_manager.is_web_search_enabled():
            url_contents = []
            for url in urls[:2]:  # Limit to 2 URLs
                url_content = await fetch_url_content(url)
                if url_content:
                    url_contents.append(url_content)
                    
        # Get LLM response
        try:
            response = await get_llm_reply(
                prompt=message_text,
                context=context_str,
                url_contents=url_contents
            )
            
            # Format response if it contains code
            if detect_code_in_message(response):
                response = format_code_blocks(response)
                
            # Store bot response in history
            self.store_message(chat_id, BOT_USERNAME.capitalize(), response)
            
            # Split long messages
            if len(response) > 4096:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            await update.message.reply_text("❌ Oops! Something went wrong. Please try again later.")
            
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
        application.add_handler(CommandHandler("setting", bot.setting_command))
        application.add_handler(CommandHandler("clock", bot.clock_command))
        application.add_handler(CommandHandler("price", bot.price_command))
        application.add_handler(CommandHandler("xmr", bot.xmr_command))
        application.add_handler(CommandHandler("stonks", bot.stonks_command))
        application.add_handler(CommandHandler("search", bot.search_command))
        application.add_handler(CommandHandler("stats", bot.stats_command))
        application.add_handler(CommandHandler("ping", bot.ping_command))
        application.add_handler(CommandHandler("reset", bot.reset_command))
        
        # Only add meme handler if enabled
        if settings_manager.is_meme_enabled():
            application.add_handler(CommandHandler("meme", bot.meme_command))
        
        # Add message handler for regular messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Add error handler
        application.add_error_handler(bot.error_handler)
        
        print("=" * 50)
        print(f"🤖 {BOT_USERNAME.capitalize()} Bot - Telegram Integration Active!")
        print("=" * 50)
        print("✅ Telegram bot starting...")
        print(f"✅ Bot Name: {BOT_USERNAME.capitalize()}")
        print("📝 Commands: /help to see all commands")
        print("💬 Chat: Just send a message to chat")
        print("⚙️ Settings: /setting to manage bot settings")
        print("🕐 World clock: /clock <city/country> for world time")
        print("💰 Price tracking: /price <crypto> [currency] or /price <from> <to>")
        print("📊 Stock market: /stonks <ticker> for stock data")
        if settings_manager.is_meme_enabled():
            print("🎨 Meme generation: /meme <topic> to create memes")
        else:
            print("🎨 Meme generation: DISABLED (use /setting meme on to enable)")
        if settings_manager.is_web_search_enabled():
            print("🔍 Web search: /search <query>")
        else:
            print("🔍 Web search: DISABLED (use /setting search on to enable)")
        print("📊 Stats: /stats for bot statistics")
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
