"""
Telegram integration for Nifty Bot
"""
import logging
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, TELEGRAM_ALLOWED_GROUPS
from config.personality import BOT_PERSONALITY
from modules.llm import get_llm_reply
from modules.price_tracker import price_tracker
from modules.web_search import search_with_jina, fetch_url_content
from utils.formatting import format_code_blocks
from utils.helpers import extract_urls_from_message, detect_code_in_message

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot implementation for Nifty"""
    
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
            "👋 Hey! I'm Nifty, your feisty anime assistant!\n\n"
            "Here's what I can do:\n"
            "💬 Just chat with me normally\n"
            "💰 /price <crypto> - Get crypto prices\n"
            "🔍 /search <query> - Search the web\n"
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
            "🤖 *Nifty Bot Commands*\n\n"
            "*Chat Commands:*\n"
            "💬 Just send me a message to chat!\n"
            "/reset - Clear conversation history\n\n"
            "*Crypto Commands:*\n"
            "💰 /price <crypto> - Get cryptocurrency price\n"
            "/xmr - Quick Monero price check\n\n"
            "*Search & Info:*\n"
            "🔍 /search <query> - Search the web\n"
            "📊 /stats - Bot statistics\n"
            "🏓 /ping - Check bot latency\n\n"
            "*Other:*\n"
            "❓ /help - Show this message\n"
            "👋 /start - Welcome message"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
            return
            
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        crypto = " ".join(context.args) if context.args else "XMR"
        response = await price_tracker.get_price_response(f"price {crypto}")
        
        if response:
            message = f"💰 *{crypto.upper()} Price*\n\n{response}"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Couldn't fetch price for {crypto}")
            
    async def xmr_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /xmr command - quick Monero price check"""
        context.args = ["XMR"]
        await self.price_command(update, context)
        
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command"""
        if not self.is_authorized(update):
            await update.message.reply_text("❌ Sorry, you're not authorized to use this bot.")
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
            "📊 *Nifty Bot Statistics*\n\n"
            f"💬 Active Chats: {len(self.conversation_history)}\n"
            f"📝 Total Messages Tracked: {sum(len(h) for h in self.conversation_history.values())}\n"
            f"🧠 Max History per Chat: {self.max_history} messages\n"
            f"✅ Bot Status: Online"
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
        
        # Check for URLs in message
        urls = extract_urls_from_message(message_text)
        url_contents = None
        if urls:
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
            self.store_message(chat_id, "Nifty", response)
            
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
        application.add_handler(CommandHandler("price", bot.price_command))
        application.add_handler(CommandHandler("xmr", bot.xmr_command))
        application.add_handler(CommandHandler("search", bot.search_command))
        application.add_handler(CommandHandler("stats", bot.stats_command))
        application.add_handler(CommandHandler("ping", bot.ping_command))
        application.add_handler(CommandHandler("reset", bot.reset_command))
        
        # Add message handler for regular messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
        
        # Add error handler
        application.add_error_handler(bot.error_handler)
        
        print("=" * 50)
        print("🤖 Nifty Bot - Telegram Integration Active!")
        print("=" * 50)
        print("✅ Telegram bot starting...")
        print("📝 Commands: /help to see all commands")
        print("💬 Chat: Just send a message to chat")
        print("💰 Price tracking: /price <crypto> or /xmr")
        print("🔍 Web search: /search <query>")
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
