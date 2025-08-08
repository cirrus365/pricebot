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

- `HOMESERVER` - Your Matrix homeserver URL (e.g., "https://matrix.org")
- `USERNAME` - Your bot's Matrix username (e.g., "@botname:matrix.org")
- `PASSWORD` - Your bot's password
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `JINA_API_KEY` - Your Jina.ai API key for web search

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

### Features in Action

- **Web Search**: Ask about current events, news, or real-time information
- **URL Analysis**: Share URLs and Nifty will read and analyze the content
- **Code Help**: Get programming assistance with syntax-highlighted code
- **Chat Summary**: Request summaries of recent conversations

## Dependencies

- `asyncio` - Asynchronous programming support
- `aiohttp` - Async HTTP client/server
- `matrix-nio` - Matrix client library
- `datetime` - Date and time handling
- `json` - JSON data handling
- `html` - HTML escaping utilities
- `re` - Regular expressions
- `urllib.parse` - URL parsing
- `collections` - Specialized container datatypes
- `random` - Random number generation

## API Services

- **OpenRouter**: Provides access to DeepSeek AI model for conversation
- **Jina.ai**: Powers web search and URL content extraction capabilities

## Privacy & Security

Nifty is designed with privacy in mind:
- Works in standard Matrix rooms (unencrypted)
- For E2EE support, additional setup with matrix-nio encryption dependencies is required
- Doesn't log personal data beyond conversation context
- Open-source and self-hostable
- Respects user privacy preferences

**Note**: This bot currently does not support end-to-end encrypted rooms out of the box. To enable E2EE support, you would need to install additional dependencies and configure the matrix-nio E2EE plugin.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open-source. Please check the repository for license details.
