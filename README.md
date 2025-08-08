Nifty Matrix chatbot - Readme

Overview
- Nifty is a Matrix-based chatbot designed to operate within Matrix homeservers (example: matrix.org). It responds to conversations, manages context, analyzes topics, and fetches information from external sources when needed.
- A defined personality can be set using the system prompt. Adjusting the system prompt changes tone, style, and approach while keeping core capabilities intact.
- This readme describes features, usage, and how to run the software from the terminal, as well as how to set up a systemd service to run it automatically.

Key Features
- Personality defined by a system prompt: tailorable tone and behavior via a central system prompt string.
- Context-aware responses: tracks room-level context, topics, user interests, and important messages to produce informed replies.
- Message handling and interaction: detects engagement triggers, can respond to direct mentions or replies, and can react with emojis to certain prompts.
- Code formatting and content handling: formats code blocks properly for display, detects and processes code content.
- URL handling: can read and discuss content from URLs shared in conversations; supports content summarization and analysis.
- Web search integration: uses a web-search layer to fetch current information when appropriate, with smart detection about when to search.
- Technical support emphasis: capable of providing technical guidance with code examples and best practices when relevant.
- Conversation summarization: can generate comprehensive summaries of recent activity, with notes on topics, participants, and important messages.
- Localizable and extensible: designed to be extended with additional triggers, topics, or integrations as needed.

Usage and Commands
- Engage by mentioning a trigger phrase in a message (default: a specific trigger word in the configuration). You can also reply directly to a prior message to continue the conversation.
- Common commands:
  - nifty !reset — Clear the current contextual history for the active room.
  - nifty summary — Get a detailed analysis of recent activity in the room.
  - Share URLs — Any shared URL can be read and analyzed by the assistant.
- Output handling:
  - The assistant formats code blocks nicely for display.
  - When content is fetched from the web or shared URLs, the assistant provides summaries and actionable insights.

System Prompt and Personality
- The personality is defined by a system prompt embedded in the code. To modify how it behaves, edit the BOT_PERSONALITY string in the file nifty.py.
- The personality is designed to be helpful, concise, and context-aware, while keeping interactions focused on user needs and available data.
- You can customize tone, style, and preferences via the system prompt to suit a particular environment or audience.
- Important: The exact content of the system prompt is not shown here. Edit nifty.py to adjust the personality.

Getting Started (Prerequisites)
- A Python 3.x environment.
- Access to a Matrix homeserver (example: matrix.org) and a user account.
- Dependencies installed (as described in installation steps below).
- If you plan to enable web search and external content processing, you may need API keys for:
  - OpenRouter (for large language model interactions)
  - Jina (for web search and content extraction)
  - Optional: any other external services you enable via configuration

Files and Example Configuration
- The main script is named nifty.py. Save or rename the script exactly as nifty.py to follow the example.
- Example Home server and account (for illustration):
  - HOMESERVER: https://matrix.org
  - USERNAME: @nifty:matrix.org
  - PASSWORD: your-password-here
- Important: For security and best practices, avoid embedding credentials directly in the code in production. Consider loading credentials from environment variables or a secure vault, and reference them from the script.

Launching from the Terminal
- Create and activate a Python environment (optional but recommended):
  - python3 -m venv venv
  - source venv/bin/activate
- Install dependencies (adjust as needed for your environment):
  - pip install aiohttp matrix-nio
  - (If you have a requirements.txt from the project, use: pip install -r requirements.txt)
- Run the program:
  - python3 nifty.py
- While running, the assistant will log in to the specified Matrix homeserver and begin listening for conversations in joined rooms.

Running as a Systemd Service (auto-start on boot)
- Create a dedicated user (optional but recommended):
  - sudo useradd -r -m nifty
- Create a working directory for the app and place nifty.py there.
- Create a Python virtual environment (optional):
  - python3 -m venv /path/to/nifty/venv
  - /path/to/nifty/venv/bin/python -m pip install -r requirements.txt
- Create a systemd service file, for example /etc/systemd/system/nifty.service:
  - (copy/paste the block below)
  ```
  [Unit]
  Description=Nifty Matrix Assistant Service
  After=network-online.target

  [Service]
  Type=simple
  User=nifty
  WorkingDirectory=/path/to/nifty
  ExecStart=/path/to/nifty/venv/bin/python /path/to/nifty/nifty.py
  Restart=on-failure
  RestartSec=5s
  Environment="HOMESERVER=https://matrix.org"
  Environment="USERNAME=@nifty:matrix.org"
  Environment="PASSWORD=your-password-here"
  Environment="OPENROUTER_API_KEY=your-openrouter-key"
  Environment="JINA_API_KEY=your-jina-key"
  Environment="LOG_LEVEL=INFO"

  [Install]
  WantedBy=multi-user.target
  ```
- Enable and start the service:
  - sudo systemctl daemon-reload
  - sudo systemctl enable nifty
  - sudo systemctl start nifty
  - sudo systemctl status nifty
- Logs can be viewed with:
  - sudo journalctl -u nifty -f

Code blocks for copy-paste
- Launching from terminal (commands)
  - Create and activate virtualenv:
  ```
  python3 -m venv venv
  source venv/bin/activate
  ```
  - Install dependencies:
  ```
  pip install aiohttp matrix-nio
  ```
  - Run the program:
  ```
  python3 nifty.py
  ```
- Systemd service file (copy-paste into /etc/systemd/system/nifty.service)
  ```
  [Unit]
  Description=Nifty Matrix Assistant Service
  After=network-online.target

  [Service]
  Type=simple
  User=nifty
  WorkingDirectory=/path/to/nifty
  ExecStart=/path/to/nifty/venv/bin/python /path/to/nifty/nifty.py
  Restart=on-failure
  RestartSec=5s
  Environment="HOMESERVER=https://matrix.org"
  Environment="USERNAME=@nifty:matrix.org"
  Environment="PASSWORD=your-password-here"
  Environment="OPENROUTER_API_KEY=your-openrouter-key"
  Environment="JINA_API_KEY=your-jina-key"
  Environment="LOG_LEVEL=INFO"

  [Install]
  WantedBy=multi-user.target
  ```
- Minimal Configuration Snippet (conceptual)
  ```
  # Minimal configuration (conceptual)
  HOMESERVER = "https://matrix.org"
  USERNAME = "@nifty:matrix.org"
  PASSWORD = "your-password-here"
  ```
Notes on Security and Best Practices
- Do not store plaintext passwords or API keys in production code. Use environment variables or a secure vault.
- When using systemd, consider running under a dedicated, minimally-permissive user account.
- Regularly rotate credentials and monitor access to the Matrix account used by the script.
- Keep dependencies up to date and test updates in a staging environment before deployment.

Customization Tips
- System Prompt: The overall tone and behavior are driven by the system prompt. Edit BOT_PERSONALITY in nifty.py to adjust personality, style, and constraints.
- Context Sensitivity: The assistant tracks topics, user interests, and important messages to tailor responses. You can adjust lookback windows and topic definitions if you want finer control.
- Web and Data Sources: OpenRouter and Jina are used for advanced capabilities like web search and content extraction. Update API keys in a secure manner and adjust usage as needed.

Example: Minimal Configuration Snippet (conceptual)
- In the actual file nifty.py, set the core fields:
  - HOMESERVER = "https://matrix.org"
  - USERNAME = "@nifty:matrix.org"
  - PASSWORD = "your-password-here"
- Then customize BOT_PERSONALITY as desired, and save.

What to Expect
- Upon startup, the system will connect to the specified Matrix homeserver, join existing rooms, and listen for messages.
- Interactions are driven by explicit triggers and replies, with automatic context management to improve relevance over time.
- Code formatting, URL reading, and knowledge retrieval from external sources are designed to augment helpful, concise responses.

Troubleshooting
- If the service fails to start, check:
  - Credentials and server URL correctness.
  - Network access to the Matrix server.
  - Availability and validity of external API keys (OpenRouter, Jina).
  - Python dependencies and compatibility with the installed Python version.
- Review log output for error messages and adjust configuration accordingly.
