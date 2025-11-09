# Telegram AI Assistant

A production-ready Telegram bot with AI-powered features including contextual conversations, autonomous commenting with roasting, user profiling, and intelligent reactions.

## Features

### Core Features
- **Contextual Jokes**: Generates Russian jokes based on conversation context
- **Multiple Trigger Modes**: `/joke` command, bot mentions, custom context
- **Autonomous Commenting**: Bot intelligently participates in conversations with roasting capabilities
- **User Profiling**: Tracks user patterns, weaknesses, and conversation style
- **Smart Reactions**: Automatically adds contextual emoji reactions to messages
- **Private Conversations**: Context-aware chat with language detection

### AI Provider Support
- **Groq** (free tier, fast Llama models)
- **OpenRouter** (multiple model options)
- **Local AI** (vLLM, Ollama, or custom endpoints)

### Production Features
- Long-polling (no white IP required)
- Systemd service support
- Comprehensive logging
- Hot-reload configuration
- Automatic profile/context saving

## Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- AI Provider API key (Groq, OpenRouter, or local server)

## Quick Start

### 1. Install

```bash
# Clone repository
git clone <repository-url>
cd telegram-joke-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

Edit `config.yaml` with your settings:

```yaml
# Bot Settings
bot:
  telegram_token: "YOUR_BOT_TOKEN"
  bot_username: "@YourBotUsername"
  admin_user_ids: []  # Add admin IDs for /reload and /comment

# AI Provider Configuration
ai:
  provider: "local"  # Options: groq, openrouter, local
  context_messages_count: 10
  max_retries: 3
  
  # Groq settings
  groq:
    api_key: "gsk_your_groq_api_key"
    model: "llama-3.2-90b-text-preview"
  
  # OpenRouter settings
  openrouter:
    api_key: "sk-or-your_key"
    model: "openai/gpt-4o-mini"
  
  # Local API settings (vLLM, Ollama, etc.)
  local:
    api_key: "dummy"
    api_url: "http://localhost:11434/v1"
    model: "llama2-uncensored"
```

### 3. Run

```bash
python bot.py
```

## Configuration Guide

All configuration is in `config.yaml`. See [`config.yaml`](config.yaml) for complete options.

### Key Sections

#### Bot Settings
```yaml
bot:
  telegram_token: "..."  # From @BotFather
  bot_username: "@..."   # Your bot's username
  admin_user_ids: [123456789]  # Admin users for /reload, /comment
```

#### AI Provider
```yaml
ai:
  provider: "local"  # Switch between groq/openrouter/local
  context_messages_count: 10
  max_retries: 3
```

#### Autonomous Commenting
```yaml
autonomous_commenting:
  enabled: true
  roasting_enabled: true
  roasting_aggression: 0.7  # 0.0 = gentle, 1.0 = brutal
  target_weaknesses_probability: 0.6
```

#### User Profiling
```yaml
user_profiling:
  enabled: true
  track_weaknesses: true
  track_mistakes: true
  track_embarrassments: true
```

#### Reactions
```yaml
reaction_system:
  enabled: true
  reaction_probability: 0.15
  # 34 different reactions available
```

For complete configuration options, see [AUTONOMOUS_FEATURES.md](AUTONOMOUS_FEATURES.md).

## Commands

### User Commands
- `/joke` - Generate contextual joke
- `/joke <topic>` - Generate joke about topic
- `/ask <question>` - Free-form AI request
- Mention bot - Generate contextual response

### Admin Commands (Private Chat Only)
- `/reload` - Hot-reload configuration
- `/comment <chat_id>` - Force autonomous comment

## Switching AI Providers

Simply change the `provider` in `config.yaml`:

```yaml
ai:
  provider: "groq"  # Change to: groq, openrouter, or local
```

Then reload:
- If running: Press Ctrl+C and restart
- If using systemd: `sudo systemctl restart telegram-joke-bot`
- If bot supports it: `/reload` command (admin only)

## Production Deployment

### Systemd Service

1. Edit service file with your paths:
```bash
nano systemd/telegram-joke-bot.service
```

2. Install and start:
```bash
sudo cp systemd/telegram-joke-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-joke-bot
sudo systemctl start telegram-joke-bot
```

3. Monitor:
```bash
sudo journalctl -u telegram-joke-bot -f
```

## Testing

The project includes comprehensive unit tests with 81%+ code coverage.

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage report
python -m pytest --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_config.py -v
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── unit/                 # Unit tests
│   ├── test_ai_providers.py    # AI provider tests (19 tests)
│   ├── test_config.py          # Configuration tests (12 tests)
│   ├── test_profile_manager.py # Profile management tests (17 tests)
│   └── test_services.py        # Service class tests (8 tests)
└── integration/          # Integration tests (future)
```

### Test Coverage

- **AI Providers**: 68% (factory functions, all provider classes)
- **Profile Management**: 88% (user profiles, AI enrichment, reactions)
- **Configuration**: 88% (loading, validation, YAML parsing)
- **Services**: ~70% (BotService, ProfileRegenerationService)
- **Overall**: **81%** ✅

## Project Structure

```
telegram-joke-bot/
├── ai_providers/          # AI provider implementations
├── handlers/             # Message handlers
├── services/             # Business logic services
├── utils/                # Utilities (profiling, commenting, reactions)
├── tests/                # Comprehensive test suite
├── logs/                 # Log files
├── profiles/             # User profiles (auto-created)
├── context_history/      # Conversation context (auto-created)
├── systemd/              # Systemd service
├── bot.py                # Main application
├── config.py             # Configuration loader
├── config.yaml           # MAIN CONFIGURATION FILE
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## Features Documentation

- [AUTONOMOUS_FEATURES.md](AUTONOMOUS_FEATURES.md) - Complete guide to autonomous features
- [config.yaml](config.yaml) - Full configuration with comments

## Troubleshooting

### Bot Not Responding
```bash
# Check status
sudo systemctl status telegram-joke-bot

# View logs
sudo journalctl -u telegram-joke-bot -n 50
tail -f logs/bot.log
```

### Configuration Issues
```bash
# Test configuration loading
python -c "from config import get_config; print('OK')"
```

### API Errors
- Check API keys in `config.yaml`
- Verify API endpoint is accessible
- Check rate limits for your provider

## Advanced Features

### User Profiling
The bot builds profiles of users including:
- Conversation patterns
- Technical/personal weaknesses
- Common mistakes
- Embarrassing moments
- Contradictions

Profiles are stored in `profiles/` and used for targeted roasting.

### Autonomous Commenting
The bot monitors conversations and:
- Comments intelligently based on context
- Targets user weaknesses for roasting
- Adapts aggression level (configurable)
- Learns from reactions

### Smart Reactions
- 34 different emoji reactions
- Context-aware selection
- Probability-based triggering
- Rate limiting per chat

## Contributing

Contributions welcome! Please:
1. Test changes locally
2. Update documentation
3. Follow existing code style

## License

This project is provided as-is for educational and personal use.

## Support

For issues:
1. Check logs: `tail -f logs/bot.log`
2. Verify `config.yaml` settings
3. Test with simple provider (Groq) first
4. Review [AUTONOMOUS_FEATURES.md](AUTONOMOUS_FEATURES.md)
