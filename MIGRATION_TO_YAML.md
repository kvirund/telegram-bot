# Migration to YAML Configuration

## What Changed

The bot has been migrated from `.env` files to a single `config.yaml` file for all configuration.

### Removed Files
- `.env` - No longer used
- `.env.example` - No longer used
- `SWITCHING_PROVIDERS.md` - Outdated
- `CHANGES_SUMMARY.md` - Temporary
- `REMOVING_MODEL_RESTRICTIONS.md` - Outdated

### Key Changes

#### Before (`.env`)
```env
TELEGRAM_BOT_TOKEN=...
BOT_USERNAME=@...
AI_PROVIDER=local
GROQ_API_KEY=...
LOCAL_API_URL=...
```

#### After (`config.yaml`)
```yaml
bot:
  telegram_token: "..."
  bot_username: "@..."
  admin_user_ids: []

ai:
  provider: "local"
  groq:
    api_key: "..."
  local:
    api_url: "..."
```

## Benefits

1. **Single Configuration File**: Everything in one place
2. **Better Organization**: Hierarchical structure
3. **Comments**: Inline documentation
4. **Type Safety**: Structured data
5. **Hot Reload**: `/reload` command works seamlessly

## Migration Steps

If you have an existing installation:

1. **Backup your `.env`** (if you have custom settings)
2. **Edit `config.yaml`** with your values:
   - Copy `telegram_token` from `.env` TELEGRAM_BOT_TOKEN
   - Copy `bot_username` from `.env` BOT_USERNAME
   - Set AI provider settings based on your `.env`
3. **Test**: Run `python bot.py`
4. **Done**: `.env` is no longer read

## Configuration Reference

See [`config.yaml`](config.yaml) for complete options with comments.

## Troubleshooting

### Bot won't start
- Check `config.yaml` syntax (YAML is sensitive to indentation)
- Ensure all required fields are filled
- Run: `python -c "from config import get_config; get_config()"`

### Need to revert?
If you need the old `.env` system:
1. Restore from git: `git checkout HEAD~1 config.py`
2. Create `.env` file with your settings
3. Restart bot

## Support

All configuration is now in `config.yaml`. No `.env` file is needed or read.
