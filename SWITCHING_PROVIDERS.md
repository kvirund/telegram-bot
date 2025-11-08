# Switching Between AI Providers

Your telegram bot now supports three AI providers that you can easily switch between by changing a single environment variable.

## Available Providers

1. **Groq** - Fast cloud API with Llama models
2. **OpenRouter** - Access to multiple models through one API
3. **Local** - Your self-hosted vLLM server (Qwen2.5-14B-Instruct-AWQ)

## How to Switch Providers

### Method 1: Edit .env File

1. Edit your `.env` file:
```bash
nano ~/repos/telegram-bot/.env
```

2. Change the `AI_PROVIDER` variable:
```bash
# For Groq (default)
AI_PROVIDER=groq

# For OpenRouter
AI_PROVIDER=openrouter

# For Local API
AI_PROVIDER=local
```

3. Save and restart the bot:
```bash
sudo systemctl restart telegram-joke-bot
```

### Method 2: Environment Variable Override

Stop the bot and run with different provider:
```bash
cd ~/repos/telegram-bot
AI_PROVIDER=local python3 bot.py
```

## Configuration for Each Provider

### Groq Configuration
```bash
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.2-90b-text-preview
```

### OpenRouter Configuration
```bash
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-your_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

### Local API Configuration
```bash
AI_PROVIDER=local
LOCAL_API_KEY=dummy
LOCAL_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
LOCAL_API_URL=http://localhost:8000/v1
```

## Testing Different Providers

1. **Test with Groq** (fast, cloud-based):
```bash
echo "AI_PROVIDER=groq" > ~/repos/telegram-bot/.env.test
sudo systemctl restart telegram-joke-bot
```

2. **Test with Local** (private, self-hosted):
```bash
echo "AI_PROVIDER=local" > ~/repos/telegram-bot/.env.test
sudo systemctl restart telegram-joke-bot
```

3. Send `/joke` command in Telegram to test

## Advantages of Each Provider

### Groq
✅ Very fast responses (< 1 second)
✅ No local infrastructure needed
✅ Reliable uptime
❌ Requires internet
❌ Costs money (API fees)
❌ Data sent to third party

### OpenRouter
✅ Access to many models
✅ Pay-per-use pricing
✅ No infrastructure
❌ Requires internet
❌ Costs money
❌ Data sent to third party

### Local
✅ Complete privacy (data stays local)
✅ No API fees
✅ Works offline (no internet needed)
✅ Full control
❌ Slower responses (3-5 seconds)
❌ Requires GPU server running
❌ Model quality depends on local hardware

## Troubleshooting

### Local Provider Not Working

1. Check if API server is running:
```bash
curl http://localhost:8000/v1/models
```

2. Check API server logs:
```bash
tail -f ~/repos/local-ai-api-server/logs/server.log
```

3. Restart API server:
```bash
cd ~/repos/local-ai-api-server
./scripts/start-server.sh
```

### Bot Not Responding After Switch

1. Check bot logs:
```bash
sudo journalctl -u telegram-joke-bot -f
```

2. Verify .env configuration:
```bash
cat ~/repos/telegram-bot/.env
```

3. Restart bot:
```bash
sudo systemctl restart telegram-joke-bot
```

## Recommended Setup

For best experience, use:
- **Local provider** when server is available (privacy + no costs)
- **Groq provider** as fallback when traveling or for fastest response
- Keep both configured in .env for easy switching
