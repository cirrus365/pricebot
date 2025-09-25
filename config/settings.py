"""Configuration settings for Price Tracker Bot"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_USERNAME = os.getenv("BOT_USERNAME", "pricebot").lower()

# Integration toggles
INTEGRATIONS = {
    'matrix': os.getenv("ENABLE_MATRIX", "true").lower() == "true",
    'discord': os.getenv("ENABLE_DISCORD", "false").lower() == "true",
    'telegram': os.getenv("ENABLE_TELEGRAM", "false").lower() == "true",
    'whatsapp': os.getenv("ENABLE_WHATSAPP", "false").lower() == "true",
    'messenger': os.getenv("ENABLE_MESSENGER", "false").lower() == "true",
    'instagram': os.getenv("ENABLE_INSTAGRAM", "false").lower() == "true"
}

# Matrix credentials - no defaults for sensitive data
HOMESERVER = os.getenv("MATRIX_HOMESERVER")
USERNAME = os.getenv("MATRIX_USERNAME")
PASSWORD = os.getenv("MATRIX_PASSWORD")

# Matrix Settings
MATRIX_STORE_PATH = os.getenv("MATRIX_STORE_PATH", "./matrix_store")
MATRIX_SYNC_TIMEOUT = int(os.getenv("MATRIX_SYNC_TIMEOUT", "10000"))  # 10 seconds default
MATRIX_REQUEST_TIMEOUT = int(os.getenv("MATRIX_REQUEST_TIMEOUT", "20"))  # 20 seconds default

# Discord credentials - no defaults for sensitive data
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_COMMAND_PREFIX = os.getenv("DISCORD_COMMAND_PREFIX", "!")
DISCORD_ALLOWED_GUILDS = os.getenv("DISCORD_ALLOWED_GUILDS", "").split(",") if os.getenv("DISCORD_ALLOWED_GUILDS") else []

# Telegram credentials - no defaults for sensitive data
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if os.getenv("TELEGRAM_ALLOWED_USERS") else []
TELEGRAM_ALLOWED_GROUPS = os.getenv("TELEGRAM_ALLOWED_GROUPS", "").split(",") if os.getenv("TELEGRAM_ALLOWED_GROUPS") else []

# Twilio credentials - no defaults for sensitive data
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_MESSENGER_PAGE_ID = os.getenv("TWILIO_MESSENGER_PAGE_ID")
TWILIO_INSTAGRAM_ACCOUNT_ID = os.getenv("TWILIO_INSTAGRAM_ACCOUNT_ID")
TWILIO_WEBHOOK_BASE_URL = os.getenv("TWILIO_WEBHOOK_BASE_URL")
TWILIO_WEBHOOK_PORT = int(os.getenv("TWILIO_WEBHOOK_PORT", "5000"))

# WhatsApp configuration
WHATSAPP_ALLOWED_NUMBERS = os.getenv("WHATSAPP_ALLOWED_NUMBERS", "").split(",") if os.getenv("WHATSAPP_ALLOWED_NUMBERS") else []

# Messenger configuration
MESSENGER_ALLOWED_USERS = os.getenv("MESSENGER_ALLOWED_USERS", "").split(",") if os.getenv("MESSENGER_ALLOWED_USERS") else []

# Instagram configuration
INSTAGRAM_ALLOWED_USERS = os.getenv("INSTAGRAM_ALLOWED_USERS", "").split(",") if os.getenv("INSTAGRAM_ALLOWED_USERS") else []

# Price tracking settings
PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "300"))  # 5 minutes cache for price data
ENABLE_PRICE_TRACKING = os.getenv("ENABLE_PRICE_TRACKING", "true").lower() == "true"

# Stock market settings
ENABLE_STOCK_MARKET = os.getenv("ENABLE_STOCK_MARKET", "true").lower() == "true"

# Timeout settings
PRICE_FETCH_TIMEOUT = int(os.getenv("PRICE_FETCH_TIMEOUT", "5"))  # 5 seconds for price fetches
