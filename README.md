# Nifty - Multi-Platform AI Chatbot with Internet Search

A feature-rich, multi-platform chatbot powered by DeepSeek AI with internet search capabilities for augmented responses. Nifty works across Matrix, Discord, and Telegram platforms, providing intelligent conversations, real-time web search, and cryptocurrency price tracking.

## 🚀 Supported Platforms

- **Matrix** - Full-featured support for Matrix chat rooms
- **Discord** - Bot and slash command support for Discord servers
- **Telegram** - Bot support for Telegram chats and groups

## Features

- **🤖 AI-Powered Conversations** - Uses DeepSeek AI for intelligent, context-aware responses
- **🔍 Internet Search Integration** - Automatically searches the web for current information using Jina.ai
- **🔗 URL Content Analysis** - Reads and analyzes content from shared URLs
- **💬 Context-Aware Responses** - Tracks conversation history and adapts responses accordingly
- **📊 Chat Analytics** - Provides comprehensive chat summaries and activity analysis
- **💻 Code Formatting** - Proper syntax highlighting for multiple programming languages
- **😎 Emoji Reactions** - Automatically reacts to messages with appropriate emojis
- **🧹 Context Management** - Reset conversation context with simple commands
- **🔒 Privacy-Focused** - Designed with privacy and open-source values in mind
- **👥 Multi-Room Support** - Works across multiple rooms/channels/groups simultaneously
- **🎯 Smart Topic Detection** - Tracks conversation topics and user expertise
- **💱 Fiat Exchange Rates** - Real-time currency conversion between major fiat currencies
- **₿ Cryptocurrency Prices** - Live crypto-to-fiat price tracking with 24h change percentages

## Platform-Specific Features

### Matrix
- Full conversation context tracking
- Emoji reactions to messages
- Room-based conversation history
- Automatic URL content fetching
- Comprehensive chat summaries

### Discord
- Slash commands support
- Guild whitelist for security
- Built-in help command system
- Mention-based interactions
- Per-channel conversation tracking
- Commands: `/help`, `/price`, `/xmr`, `/stats`, `/ping`

### Telegram
- Command-based interactions
- User and group authorization
- Inline keyboard support (planned)
- Commands: `/start`, `/help`, `/price`, `/xmr`, `/search`, `/stats`, `/ping`, `/reset`

## Price Tracking Features

### Cryptocurrency Prices
Get real-time cryptocurrency prices and market data:
- **Supported cryptos**: BTC, ETH, XMR, SOL, ADA, DOT, MATIC, LINK, UNI, AAVE, and more
- **Price info includes**: Current price, 24h change percentage, formatted in requested currency
- **Example queries**:
  - "What's the price of Bitcoin?"
  - "BTC price in EUR"
  - "How much is Monero worth?"
  - "ETH to GBP"

### Fiat Currency Exchange
Convert between major world currencies:
- **Supported currencies**: USD, EUR, GBP, JPY, AUD, CAD, CHF, CNY, and more
- **Real-time exchange rates** with 5-minute caching for performance
- **Example queries**:
  - "Convert 100 USD to EUR"
  - "What's the exchange rate for GBP to JPY?"
  - "How much is 50 euros in dollars?"

### Smart Price Detection
Nifty automatically detects price-related queries and provides:
- Formatted prices with appropriate currency symbols
- Percentage changes with color indicators (🟢 for gains, 🔴 for losses)
- Cached responses for frequently requested pairs (5-minute TTL)

## Requirements

- Python 3.8 or higher
- API Keys:
  - OpenRouter API key (for DeepSeek AI)
  - Jina.ai API key (for web search)
- Platform-specific requirements:
  - **Matrix**: Matrix account
  - **Discord**: Discord bot token and application
  - **Telegram**: Telegram bot token from BotFather

## Installation

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

Or manually install core dependencies:

```bash
pip install asyncio aiohttp matrix-nio discord.py python-telegram-bot python-dotenv
```

## Configuration

Create a `.env` file based on `.env.example` with the following variables:

### Core Settings
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `JINA_API_KEY` - Your Jina.ai API key for web search
- `ENABLE_PRICE_TRACKING` - Toggle price tracking feature (default: `true`)
- `PRICE_CACHE_TTL` - Cache duration for price data in seconds (default: `300`)

### Platform Toggles
- `ENABLE_MATRIX` - Enable Matrix integration (default: `true`)
- `ENABLE_DISCORD` - Enable Discord integration (default: `false`)
- `ENABLE_TELEGRAM` - Enable Telegram integration (default: `false`)

### Matrix Configuration
- `MATRIX_HOMESERVER` - Your Matrix homeserver URL (e.g., `"https://matrix.org"`)
- `MATRIX_USERNAME` - Your bot's Matrix username (e.g., `"@botname:matrix.org"`)
- `MATRIX_PASSWORD` - Your bot's password

### Discord Configuration
- `DISCORD_TOKEN` - Your Discord bot token
- `DISCORD_COMMAND_PREFIX` - Command prefix for Discord (default: `!`)
- `DISCORD_ALLOWED_GUILDS` - Comma-separated list of allowed guild IDs (optional)

### Telegram Configuration
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token from BotFather
- `TELEGRAM_ALLOWED_USERS` - Comma-separated list of allowed user IDs (optional)
- `TELEGRAM_ALLOWED_GROUPS` - Comma-separated list of allowed group IDs (optional)

### Additional Settings
- `FILTERED_WORDS` - Comma-separated list of words to filter
- `KNOWN_BOTS` - Comma-separated list of known bot usernames to ignore
- `MAX_QUEUE_SIZE` - Maximum message queue size (default: `5`)
- `LLM_TIMEOUT` - LLM response timeout in seconds (default: `30`)

## Running the Bot

### From Terminal

```bash
python nifty.py
```

The bot will automatically start the enabled integrations based on your `.env` configuration.

### Using systemd Service

Create a systemd service file to run the chatbot as a system service:

```bash
sudo nano /etc/systemd/system/nifty-bot.service
```

Add the following content:

```ini
[Unit]
Description=Nifty Multi-Platform Chatbot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/bot/directory
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/bot/directory/nifty.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nifty-bot.service
sudo systemctl start nifty-bot.service
```

Check service status:

```bash
sudo systemctl status nifty-bot.service
```

View logs:

```bash
sudo journalctl -u nifty-bot.service -f
```

## Usage

### Matrix Usage

- **Direct mention**: Include "nifty" anywhere in your message
- **Reply**: Reply to any of Nifty's messages
- **Commands**:
  - `nifty !reset` - Clear conversation context
  - `nifty summary` - Get a comprehensive chat analysis
  - `nifty [your question]` - Ask anything!
  - `nifty btc price` - Get Bitcoin price
  - `nifty convert 100 usd to eur` - Currency conversion

### Discord Usage

- **Mention the bot**: `@Nifty your question`
- **Commands** (with prefix, default `!`):
  - `!help` - Show available commands
  - `!price [crypto]` - Get cryptocurrency price
  - `!xmr` - Get Monero price
  - `!stats` - Show bot statistics
  - `!ping` - Check bot latency

### Telegram Usage

- **Direct message**: Send any message to the bot
- **Group mention**: Mention the bot or reply to its messages
- **Commands**:
  - `/start` - Start interaction with the bot
  - `/help` - Show available commands
  - `/price [crypto]` - Get cryptocurrency price
  - `/xmr` - Get Monero price
  - `/search [query]` - Search the web
  - `/stats` - Show bot statistics
  - `/ping` - Check bot responsiveness
  - `/reset` - Reset conversation context

### Features in Action

- **Web Search**: Ask about current events, news, or real-time information
- **URL Analysis**: Share URLs and Nifty will read and analyze the content
- **Code Help**: Get programming assistance with syntax-highlighted code
- **Chat Summary**: Request summaries of recent conversations
- **Price Tracking**: Get real-time crypto prices and fiat exchange rates

## Setting Up Platform Bots

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the Bot section and create a bot
4. Copy the bot token to your `.env` file
5. Under OAuth2 > URL Generator, select "bot" scope and necessary permissions
6. Use the generated URL to invite the bot to your server

### Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token to your `.env` file
4. Optional: Set bot commands with `/setcommands`
5. Optional: Set bot description with `/setdescription`

## Dependencies

Core dependencies:
- `asyncio` - Asynchronous programming support
- `aiohttp` - Async HTTP client/server
- `python-dotenv` - Environment variable management
- `datetime` - Date and time handling
- `json` - JSON data handling

Platform-specific:
- `matrix-nio>=0.24.0` - Matrix client library ([matrix-nio.readthedocs.io](https://matrix-nio.readthedocs.io/))
- `discord.py>=2.3.0` - Discord bot framework
- `python-telegram-bot>=20.0` - Telegram bot framework

Additional utilities:
- `html` - HTML escaping utilities
- `re` - Regular expressions
- `urllib.parse` - URL parsing
- `collections` - Specialized container datatypes
- `random` - Random number generation

## API Services

- **OpenRouter**: Provides access to DeepSeek AI model for conversation ([openrouter.ai](https://openrouter.ai/docs))
- **Jina.ai**: Powers web search and URL content extraction capabilities ([jina.ai](https://jina.ai/))
- **CoinGecko API**: Free cryptocurrency price data (no API key required)
- **ExchangeRate-API**: Free tier fiat currency exchange rates (no API key required)

## Privacy & Security

Nifty is designed with privacy in mind:

- Works in standard Matrix rooms (unencrypted)
- Discord: Supports guild whitelisting for controlled access
- Telegram: Supports user and group whitelisting
- For E2EE support in Matrix, additional setup with matrix-nio encryption dependencies is required
- Doesn't log personal data beyond conversation context
- Open-source and self-hostable
- Respects user privacy preferences
- Price data is cached locally to minimize API calls

**Note**: Matrix bot currently does not support end-to-end encrypted rooms out of the box. To enable E2EE support, you would need to install additional dependencies and configure the [matrix-nio](https://github.com/matrix-nio/matrix-nio) E2EE plugin.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open-source. Please check the repository for license details.
