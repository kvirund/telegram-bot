# Telegram Joke Bot

A production-ready Telegram bot that tells Russian jokes using AI (Groq or OpenRouter). The bot monitors channels continuously and responds to `/joke` commands and bot mentions with contextual humor.

## Features

- **Multiple Trigger Modes**:
  - `/joke` - Generates a Russian joke based on recent conversation context
  - `/joke <context>` - Generates a Russian joke based on the provided context text
  - Bot mentions - Generates contextual jokes when the bot is mentioned in conversation

- **Flexible AI Provider**:
  - Groq (free tier, fast responses with Llama models)
  - OpenRouter (flat monthly pricing with multiple model options)
  - Easy switching between providers via configuration

- **Production-Ready**:
  - Long-polling (works without white IP address)
  - Systemd service for automatic restart and management
  - Comprehensive logging
  - Error handling and recovery
  - In-memory conversation context tracking

## Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Groq API key (free at [console.groq.com](https://console.groq.com))
- OR OpenRouter API key (from [openrouter.ai](https://openrouter.ai))

## Installation

### 1. Clone or Download the Repository

```bash
# If using git
git clone <repository-url>
cd telegram-joke-bot

# Or download and extract the files
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Bot

Copy the example environment file and edit it with your credentials:

```bash
cp .env.example .env
nano .env  # Or use any text editor
```

Edit `.env` with your actual values:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHANNEL_ID=-1001234567890
BOT_USERNAME=@your_bot_username

# AI Provider Configuration
AI_PROVIDER=groq

# Groq Configuration
GROQ_API_KEY=gsk_your_actual_groq_api_key_here
GROQ_MODEL=llama-3.2-90b-text-preview

# OpenRouter Configuration (optional, for switching)
OPENROUTER_API_KEY=sk-or-your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini

# Bot Behavior
CONTEXT_MESSAGES_COUNT=10
MAX_RETRIES=3
```

### 5. Get Your Configuration Values

#### Telegram Bot Token
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Copy the bot token provided

#### Channel ID
1. Add your bot to the channel as an administrator
2. Send a message in the channel
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-1001234567890}` - this is your channel ID

#### Bot Username
The username you created for your bot (e.g., `@my_joke_bot`)

#### API Keys
- **Groq**: Sign up at [console.groq.com](https://console.groq.com) and create an API key
- **OpenRouter**: Sign up at [openrouter.ai](https://openrouter.ai) and create an API key

## Running the Bot

### Local Testing

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the bot
python bot.py
```

You should see:
```
Starting Telegram Joke Bot...
Configuration loaded successfully
AI Provider: groq
Model: llama-3.2-90b-text-preview
Bot Username: @your_bot_username
Bot started successfully. Polling for updates...
```

### Test the Bot

1. Go to your Telegram channel
2. Try these commands:
   - `/joke` - Should generate a contextual joke
   - `/joke programming` - Should generate a joke about programming
   - Mention the bot in a message - Should generate a contextual joke

## Production Deployment (Ubuntu Server)

### 1. Transfer Files to Server

```bash
# From your local machine
scp -r telegram-joke-bot user@your-server:/home/user/
```

Or clone directly on the server.

### 2. Set Up on Server

```bash
# SSH into your server
ssh user@your-server

# Navigate to the bot directory
cd /home/user/telegram-joke-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure .env file
cp .env.example .env
nano .env  # Add your credentials
```

### 3. Set Up Systemd Service

Edit the service file with your actual paths:

```bash
nano systemd/telegram-joke-bot.service
```

Update these lines:
```ini
User=YOUR_USERNAME  # Your Ubuntu username
WorkingDirectory=/home/YOUR_USERNAME/telegram-joke-bot
Environment="PATH=/home/YOUR_USERNAME/telegram-joke-bot/venv/bin"
ExecStart=/home/YOUR_USERNAME/telegram-joke-bot/venv/bin/python bot.py
```

Install the service:

```bash
# Copy service file to systemd directory
sudo cp systemd/telegram-joke-bot.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable telegram-joke-bot

# Start the service
sudo systemctl start telegram-joke-bot

# Check status
sudo systemctl status telegram-joke-bot
```

### 4. Monitor Logs

```bash
# View live logs
sudo journalctl -u telegram-joke-bot -f

# View recent logs
sudo journalctl -u telegram-joke-bot -n 100

# View logs in file
tail -f logs/bot.log
```

### 5. Manage the Service

```bash
# Stop the bot
sudo systemctl stop telegram-joke-bot

# Restart the bot
sudo systemctl restart telegram-joke-bot

# Check status
sudo systemctl status telegram-joke-bot

# Disable auto-start
sudo systemctl disable telegram-joke-bot
```

## Switching AI Providers

To switch from Groq to OpenRouter (or vice versa):

1. Edit `.env` file:
   ```bash
   nano .env
   ```

2. Change `AI_PROVIDER`:
   ```env
   AI_PROVIDER=openrouter  # or "groq"
   ```

3. Restart the bot:
   ```bash
   # If running manually
   # Press Ctrl+C and restart: python bot.py
   
   # If running as service
   sudo systemctl restart telegram-joke-bot
   ```

The bot will automatically use the new provider's API key and model settings.

## Usage Examples

### Simple Random Joke
```
User: /joke
Bot: [Tells a Russian joke based on recent conversation]
```

### Joke with Custom Context
```
User: /joke about cats and dogs
Bot: [Tells a Russian joke about cats and dogs]
```

### Contextual Joke via Mention
```
User1: Я вчера купил новый компьютер
User2: Какой?
User1: MacBook Pro
User3: @your_bot_name
Bot: [Tells a Russian joke related to the MacBook conversation]
```

## Troubleshooting

### Bot Not Responding

1. Check if bot is running:
   ```bash
   sudo systemctl status telegram-joke-bot
   ```

2. Check logs for errors:
   ```bash
   sudo journalctl -u telegram-joke-bot -n 50
   ```

3. Verify configuration:
   ```bash
   cat .env  # Check if all values are set
   ```

### API Errors

- **Groq rate limits**: Wait and retry, or switch to OpenRouter
- **Invalid API key**: Double-check your API key in `.env`
- **Network issues**: Check server internet connection

### Bot Added to Channel but Not Working

1. Ensure bot is an **administrator** in the channel
2. Verify `CHANNEL_ID` is correct (should start with `-100`)
3. Check bot username is correct (include the `@` symbol)

### "No context available" Messages

This is normal when:
- Bot just started (no message history yet)
- First message in a new conversation
- All recent messages were commands (filtered out of context)

## Project Structure

```
telegram-joke-bot/
├── ai_providers/           # AI provider implementations
│   ├── __init__.py        # Provider factory
│   ├── base.py            # Abstract base class
│   ├── groq_provider.py   # Groq implementation
│   └── openrouter_provider.py  # OpenRouter implementation
├── handlers/              # Message handlers
│   └── message_handler.py # Main handler logic
├── utils/                 # Utilities
│   └── context_extractor.py  # Context extraction
├── logs/                  # Log files
├── systemd/              # Systemd service file
├── bot.py                # Main application
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── .env                  # Configuration (create from .env.example)
├── .env.example          # Configuration template
├── .gitignore           # Git exclusions
└── README.md            # This file
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is provided as-is for educational and personal use.

## Support

For issues and questions:
1. Check the logs: `sudo journalctl -u telegram-joke-bot -n 100`
2. Verify configuration in `.env`
3. Test with Groq first (easier setup, free tier)
4. Review error messages in `logs/bot.log`
