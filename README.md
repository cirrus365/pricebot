# Nifty - Matrix Chatbot with Internet Search

A feature-rich Matrix chatbot powered by DeepSeek AI with internet search capabilities for augmented responses. Nifty can fetch real-time information from the web, analyze URLs, and provide context-aware responses in Matrix chat rooms.

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
- **👥 Multi-Room Support** - Works across multiple Matrix rooms simultaneously
- **🎯 Smart Topic Detection** - Tracks conversation topics and user expertise
- **💱 Fiat Exchange Rates** - Real-time currency conversion between major fiat currencies
- **₿ Cryptocurrency Prices** - Live crypto-to-fiat price tracking with 24h change percentages

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
- Matrix account
- OpenRouter API key (for DeepSeek AI)
- Jina.ai API key (for web search)

## Installation

Install the required Python dependencies:

```bash
pip install asyncio aiohttp matrix-nio
```

## Configuration

Edit the following variables in the script:

- `HOMESERVER` - Your Matrix homeserver URL (e.g., `"https://matrix.org"`)
- `USERNAME` - Your bot's Matrix username (e.g., `"@botname:matrix.org"`)
- `PASSWORD` - Your bot's password
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `JINA_API_KEY` - Your Jina.ai API key for web search
- `ENABLE_PRICE_TRACKING` - Toggle price tracking feature (default: `True`)
- `PRICE_CACHE_TTL` - Cache duration for price data in seconds (default: `300`)

## Running the Bot

### From Terminal

```bash
python nifty_bot.py
```

### Using systemd Service

Create a systemd service file to run the chatbot as a system service:

```bash
sudo nano /etc/systemd/system/nifty-bot.service
```

Add the following content:

```ini
[Unit]
Description=Nifty Matrix Chatbot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/bot/directory
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/bot/directory/nifty_bot.py
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

### Triggering the Bot

- **Direct mention**: Include "nifty" anywhere in your message
- **Reply**: Reply to any of Nifty's messages
- **Commands**:
  - `nifty !reset` - Clear conversation context
  - `nifty summary` - Get a comprehensive chat analysis
  - `nifty [your question]` - Ask anything!
  - `nifty btc price` - Get Bitcoin price
  - `nifty convert 100 usd to eur` - Currency conversion

### Features in Action

- **Web Search**: Ask about current events, news, or real-time information
- **URL Analysis**: Share URLs and Nifty will read and analyze the content
- **Code Help**: Get programming assistance with syntax-highlighted code
- **Chat Summary**: Request summaries of recent conversations
- **Price Tracking**: Get real-time crypto prices and fiat exchange rates

## Dependencies

- `asyncio` - Asynchronous programming support
- `aiohttp` - Async HTTP client/server
- `matrix-nio` - Matrix client library ([matrix-nio.readthedocs.io](https://matrix-nio.readthedocs.io/))
- `datetime` - Date and time handling
- `json` - JSON data handling
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
- For E2EE support, additional setup with matrix-nio encryption dependencies is required
- Doesn't log personal data beyond conversation context
- Open-source and self-hostable
- Respects user privacy preferences
- Price data is cached locally to minimize API calls

**Note**: This bot currently does not support end-to-end encrypted rooms out of the box. To enable E2EE support, you would need to install additional dependencies and configure the [matrix-nio](https://github.com/matrix-nio/matrix-nio) E2EE plugin.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open-source. Please check the repository for license details.
