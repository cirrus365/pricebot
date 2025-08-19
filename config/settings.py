"""Configuration settings for Nifty bot"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Integration toggles
INTEGRATIONS = {
    'matrix': os.getenv("ENABLE_MATRIX", "true").lower() == "true",
    'discord': os.getenv("ENABLE_DISCORD", "false").lower() == "true"
}

# Matrix credentials
HOMESERVER = os.getenv("MATRIX_HOMESERVER", "https://converser.eu")
USERNAME = os.getenv("MATRIX_USERNAME", "@nifty:converser.eu")
PASSWORD = os.getenv("MATRIX_PASSWORD")

# Discord credentials
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_COMMAND_PREFIX = os.getenv("DISCORD_COMMAND_PREFIX", "!")
DISCORD_ALLOWED_GUILDS = os.getenv("DISCORD_ALLOWED_GUILDS", "").split(",") if os.getenv("DISCORD_ALLOWED_GUILDS") else []

# OpenRouter config
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")

# Jina.ai config
JINA_API_KEY = os.getenv("JINA_API_KEY")

# Bot filter - prevent triggering other bots
FILTERED_WORDS = os.getenv("FILTERED_WORDS", "kyoko").split(",")  # Comma-separated list

# Known bots to ignore
KNOWN_BOTS = os.getenv("KNOWN_BOTS", "@kyoko:xmr.mx").split(",")  # Comma-separated list

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
