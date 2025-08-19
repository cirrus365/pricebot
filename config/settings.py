"""Configuration settings for Nifty bot"""

# Matrix credentials
HOMESERVER = "https://converser.eu"
USERNAME = "@nifty:converser.eu"
PASSWORD = "kSsGP06f#Lr4xswD^aLttq0$An2pb3MDxU944urb6BMsjgXRl6z#UNI!33VZES#6niZbn1GNW8NBVBlT0Q&A@AVBrFzKa9dZd9KhyGGFrfLeUer@mdE4dtIyTDevQ3nx"

# OpenRouter config
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Jina.ai config
JINA_API_KEY = "jina_0cad2a2d42bb49d48c37eac962701bbcEZU5hmwFVrVYofGRF0fY86lzu3Lo"

# Bot filter - prevent triggering other bots
FILTERED_WORDS = ['kyoko']  # Only filter exact bot trigger word

# Known bots to ignore
KNOWN_BOTS = ['@kyoko:xmr.mx']

# Request queue settings
MAX_QUEUE_SIZE = 5

# Timeout settings
LLM_TIMEOUT = 30
SEARCH_TIMEOUT = 15
URL_FETCH_TIMEOUT = 20
PRICE_FETCH_TIMEOUT = 10

# Context settings
MAX_ROOM_HISTORY = 100
MAX_CONTEXT_LOOKBACK = 30
MAX_IMPORTANT_MESSAGES = 20

# Retry settings
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1

# Price tracking settings
PRICE_CACHE_TTL = 300  # 5 minutes cache for price data
ENABLE_PRICE_TRACKING = True  # Toggle price tracking feature
