# Profile Regeneration Tool

## Overview

The profile regeneration tool allows you to re-enrich all user profiles using the current AI enrichment prompt. This is useful when:
- You've updated the AI enrichment prompt in `utils/profile_manager.py`
- You want to regenerate profiles with improved AI analysis
- Profiles were created with an old version of the enrichment prompt

## Usage

### Command Line

Run the regeneration script from the command line:

```bash
cd telegram-joke-bot
python bot.py --regenerate-profiles
```

### What It Does

1. **Loads Configuration**: Reads your `config.yaml` and AI provider settings
2. **Initializes AI Provider**: Sets up the AI model (Groq, OpenRouter, or Local)
3. **Reads Context History**: Loads chat history for all chats from `context_history/`
4. **Collects User Messages**: Gathers up to 100 recent messages per user
5. **Filters Users**: Only processes users with 5+ messages
6. **AI Enrichment**: Re-analyzes each user's messages with AI
7. **Saves Profiles**: Writes updated profiles to `profiles/users/`

### Output Example

```
============================================================
PROFILE REGENERATION STARTING
============================================================
Configuration loaded: groq / llama-3.2-90b-text-preview
AI provider initialized
Found 3 chats in history
Found 15 users to process
Processing user 509897407 (John) - 45 messages
✓ User 509897407 enriched successfully
Processing user 157117521 (Jane) - 32 messages
✓ User 157117521 enriched successfully
...
============================================================
PROFILE REGENERATION COMPLETE
Processed: 12
Skipped (<5 messages): 3
Failed: 0
Total: 15
============================================================
```

## Requirements

- Bot must be stopped (profiles are loaded/saved)
- Context history files must exist (`context_history/chat_*.json`)
- AI provider must be configured and accessible
- Minimum 5 messages per user required for processing

## Notes

- Processing time depends on number of users and AI provider speed
- Failed enrichments are logged but don't stop the process
- Profiles are saved immediately after each successful enrichment
- The bot does NOT need to be running - this is a standalone utility

## Troubleshooting

### No users found
- Check that `context_history/` directory contains chat JSON files
- Verify that chat files have user messages (not just bot messages)

### AI enrichment fails
- Check AI provider API key in `config.yaml`
- Verify AI provider service is accessible
- Check logs for specific error messages

### Profile not updated
- Ensure user has 5+ messages
- Check that profile directory is writable
- Verify AI enrichment completed successfully (check logs)
