## Installation

### 1. Clone the repository

```bash
git clone https://github.com/cirrus365/pricebot.git
cd pricebot
```

### 2. Install dependencies

```bash
# Install required Python packages
pip install -r requirements.txt

# Or if using a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Copy the example environment file and edit it with your API keys and settings:

```bash
cp .env.example .env
# Edit .env with your Matrix/Discord tokens and other settings
```

### 4. Setting up as a systemd service

Create a systemd service file to run the bot automatically:

```bash
sudo nano /etc/systemd/system/pricebot.service
```

Add the following content, replacing the paths and username with your actual values:

```ini
[Unit]
Description=Price Tracker Bot
After=multi-user.target
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your_username
Group=your_username
WorkingDirectory=/path/to/pricebot
ExecStart=/path/to/python3 /path/to/pricebot/bot.py
# For virtual environment, use:
# ExecStart=/path/to/pricebot/venv/bin/python /path/to/pricebot/bot.py
Restart=on-failure
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5. Enable and start the service

Enable and start the systemd service:

```bash
# Copy the service file and reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start pricebot.service

# Check service status
sudo systemctl status pricebot.service

# Enable auto-start on boot
sudo systemctl enable pricebot.service
```

### 6. Managing the service

```bash
# Stop the service
sudo systemctl stop pricebot.service

# Restart the service
sudo systemctl restart pricebot.service

# View logs
sudo journalctl -u pricebot.service -f
```

## Requirements

- Python 3.8+
- Matrix SDK (for Matrix functionality)
- Discord.py (for Discord functionality)
- Required API keys for cryptocurrency/stock data sources

## Configuration

The bot requires configuration through a `.env` file. See `.env.example` for the required format and settings.
