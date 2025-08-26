"""Configuration settings for Nifty bot"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_USERNAME = os.getenv("BOT_USERNAME", "nifty").lower()

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

# LLM Provider Selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()  # 'openrouter' or 'ollama'

# OpenRouter config - no defaults for API keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")

# Ollama config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "5m")  # How long to keep model loaded in memory
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "1000"))  # Max tokens to generate
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.8"))  # Temperature for generation
OLLAMA_TOP_K = int(os.getenv("OLLAMA_TOP_K", "40"))  # Top-k sampling
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))  # Top-p (nucleus) sampling
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))  # Penalize repetition

# Jina.ai config - no defaults for API keys
JINA_API_KEY = os.getenv("JINA_API_KEY")

# Bot filter - prevent triggering other bots
FILTERED_WORDS = os.getenv("FILTERED_WORDS", "").split(",") if os.getenv("FILTERED_WORDS") else []

# Known bots to ignore
KNOWN_BOTS = os.getenv("KNOWN_BOTS", "").split(",") if os.getenv("KNOWN_BOTS") else []

# Request queue settings
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "5"))

# Timeout settings
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))
URL_FETCH_TIMEOUT = int(os.getenv("URL_FETCH_TIMEOUT", "20"))
PRICE_FETCH_TIMEOUT = int(os.getenv("PRICE_FETCH_TIMEOUT", "10"))

# Context settings
MAX_ROOM_HISTORY = int(os.getenv("MAX_ROOM_HISTORY", "100"))
MAX_CONTEXT_LOOKBACK = int(os.getenv("MAX_CONTEXT_LOOKBACK", "30"))
MAX_IMPORTANT_MESSAGES = int(os.getenv("MAX_IMPORTANT_MESSAGES", "20"))

# Retry settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BASE_RETRY_DELAY = int(os.getenv("BASE_RETRY_DELAY", "1"))

# Price tracking settings
PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "300"))  # 5 minutes cache for price data
ENABLE_PRICE_TRACKING = os.getenv("ENABLE_PRICE_TRACKING", "true").lower() == "true"
