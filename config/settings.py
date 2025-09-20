"""Configuration settings for Chatbot"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_USERNAME = os.getenv("BOT_USERNAME", "chatbot").lower()

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

# Matrix E2EE Settings
ENABLE_MATRIX_E2EE = os.getenv("ENABLE_MATRIX_E2EE", "true").lower() == "true"
MATRIX_STORE_PATH = os.getenv("MATRIX_STORE_PATH", "./matrix_store")

# Matrix Auto-Invite Settings
ENABLE_AUTO_INVITE = os.getenv("ENABLE_AUTO_INVITE", "true").lower() == "true"
ALLOWED_INVITE_USERS = os.getenv("ALLOWED_INVITE_USERS", "").split(",") if os.getenv("ALLOWED_INVITE_USERS") else []

# Matrix Performance Settings
MATRIX_SYNC_TIMEOUT = int(os.getenv("MATRIX_SYNC_TIMEOUT", "10000"))  # 10 seconds default
MATRIX_REQUEST_TIMEOUT = int(os.getenv("MATRIX_REQUEST_TIMEOUT", "20"))  # 20 seconds default
MATRIX_KEEPALIVE_INTERVAL = int(os.getenv("MATRIX_KEEPALIVE_INTERVAL", "60"))  # 60 seconds default
MATRIX_FULL_SYNC_INTERVAL = int(os.getenv("MATRIX_FULL_SYNC_INTERVAL", "1800"))  # 30 minutes default

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
OPENROUTER_FALLBACK_MODEL = os.getenv("OPENROUTER_FALLBACK_MODEL", "")  # Optional fallback model

# Ollama config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "5m")  # How long to keep model loaded in memory
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "500"))  # Reduced from 1000 for faster responses
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.8"))  # Temperature for generation
OLLAMA_TOP_K = int(os.getenv("OLLAMA_TOP_K", "40"))  # Top-k sampling
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))  # Top-p (nucleus) sampling
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))  # Penalize repetition
OLLAMA_WARM_INTERVAL = int(os.getenv("OLLAMA_WARM_INTERVAL", "300"))  # 5 minutes between warm-ups

# Jina.ai config - no defaults for API keys
JINA_API_KEY = os.getenv("JINA_API_KEY")

# Imgflip config for meme generation - no defaults for credentials
IMGFLIP_USERNAME = os.getenv("IMGFLIP_USERNAME")
IMGFLIP_PASSWORD = os.getenv("IMGFLIP_PASSWORD")
ENABLE_MEME_GENERATION = os.getenv("ENABLE_MEME_GENERATION", "true").lower() == "true"

# Bot filter - prevent triggering other bots
FILTERED_WORDS = os.getenv("FILTERED_WORDS", "").split(",") if os.getenv("FILTERED_WORDS") else []

# Known bots to ignore
KNOWN_BOTS = os.getenv("KNOWN_BOTS", "").split(",") if os.getenv("KNOWN_BOTS") else []

# Request queue settings
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "5"))

# Timeout settings
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "20"))  # Reduced from 30
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "10"))  # Reduced from 15
URL_FETCH_TIMEOUT = int(os.getenv("URL_FETCH_TIMEOUT", "10"))  # Reduced from 20
PRICE_FETCH_TIMEOUT = int(os.getenv("PRICE_FETCH_TIMEOUT", "5"))  # Reduced from 10

# Context settings - SIMPLIFIED
MAX_ROOM_HISTORY = int(os.getenv("MAX_ROOM_HISTORY", "20"))  # Reduced from 100
MAX_CONTEXT_LOOKBACK = int(os.getenv("MAX_CONTEXT_LOOKBACK", "5"))  # Reduced from 30
MAX_IMPORTANT_MESSAGES = int(os.getenv("MAX_IMPORTANT_MESSAGES", "3"))  # Reduced from 20
ENABLE_CONTEXT_ANALYSIS = os.getenv("ENABLE_CONTEXT_ANALYSIS", "false").lower() == "true"  # Disabled by default

# Detailed context feature toggles
ENABLE_TOPIC_TRACKING = os.getenv("ENABLE_TOPIC_TRACKING", "false").lower() == "true"
ENABLE_USER_INTERESTS = os.getenv("ENABLE_USER_INTERESTS", "false").lower() == "true"
ENABLE_IMPORTANCE_DETECTION = os.getenv("ENABLE_IMPORTANCE_DETECTION", "false").lower() == "true"
ENABLE_CONVERSATION_FLOW = os.getenv("ENABLE_CONVERSATION_FLOW", "false").lower() == "true"

# Context inclusion settings
INCLUDE_CONTEXT_IN_PROMPT = os.getenv("INCLUDE_CONTEXT_IN_PROMPT", "true").lower() == "true"
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "500"))

# Context cleanup settings
CONTEXT_CLEANUP_INTERVAL = int(os.getenv("CONTEXT_CLEANUP_INTERVAL", "3600"))  # 1 hour
CONTEXT_CLEANUP_AGE = int(os.getenv("CONTEXT_CLEANUP_AGE", "86400"))  # 24 hours

# Retry settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))  # Reduced from 3
BASE_RETRY_DELAY = int(os.getenv("BASE_RETRY_DELAY", "1"))

# Price tracking settings
PRICE_CACHE_TTL = int(os.getenv("PRICE_CACHE_TTL", "300"))  # 5 minutes cache for price data
ENABLE_PRICE_TRACKING = os.getenv("ENABLE_PRICE_TRACKING", "true").lower() == "true"

# Stock market settings
ENABLE_STOCK_MARKET = os.getenv("ENABLE_STOCK_MARKET", "true").lower() == "true"

# Web search settings
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"  # Disabled by default for speed
