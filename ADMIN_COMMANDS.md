# Administrative Commands Guide

This document describes the administrative commands added to the Telegram Joke Bot.

## Command Overview

### For All Users

#### `/help`
Shows available commands based on the user's privilege level.

**Features:**
- Displays user's access level (User or Administrator)
- Shows user's Telegram ID
- Lists only commands available to that user
- Provides usage examples for admin commands (if admin)

**Usage:**
```
/help
```

**Output includes:**
- User's access level and ID
- Basic commands (jokes, conversation)
- Admin commands (if applicable)
- Bot features summary

---

### For Administrators Only

#### `/context` - Clear Conversation Context
Clears conversation history for a chat, resetting the bot's memory.

**Usage:**
```
/context                 # Clear current chat context
/context <chat_id>       # Clear specific chat context (admin only)
```

**Examples:**
```
/context                 # In group chat, clears that group's context
/context -1001234567890  # Admin clears specific chat's context
```

**What it clears:**
- Message history for context extraction
- Autonomous commenter state
- Conversation memory

**Response shows:**
- Number of messages removed
- Confirmation of state reset

---

#### `/chats` - List Active Chats
Lists all chats where the bot is present with message history.

**Usage:**
```
/chats
```

**Information Shown:**
- Chat name and type (private, group, supergroup, channel)
- Chat ID (useful for /comment and /context commands)
- Number of messages in history
- Accessibility status

**Examples:**
```
/chats  # Shows all active chats
```

**Output includes:**
- Chat count
- Icons for different chat types (👤 private, 👥 group, 📢 channel)
- Chat IDs for use with other admin commands
- Message counts per chat

---

#### `/profile` - View User Profile
Displays detailed profile information for any user tracked by the bot.

**Usage:**
```
/profile @username       # Search by username
/profile 123456789       # Search by user ID
/profile John           # Search by first name
```

**Profile Information Shown:**
- **Basic Info:**
  - User ID
  - Name and username
  - Language preference
  - Message count

- **Behavior Patterns:**
  - Interests
  - Technical weaknesses
  - Personal weaknesses
  - Common mistakes

- **Roasting Data:**
  - Number of successful roasts
  - Last roast date
  - Embarrassing moments tracked

**Search Methods:**
1. Direct ID lookup (fastest)
2. Username search (with or without @)
3. First name search (case-insensitive)

**Examples:**
```
/profile @john_doe       # By username
/profile 509897407       # By ID
/profile John            # By first name
```

---

#### `/groupmood` - Show Group Sentiment (Public)
Displays current group sentiment analysis for the current chat.

**Usage:** (Public command)
```
/groupmood
```

**Information Shown:**
- Overall mood (positive/neutral/negative)
- Sentiment distribution percentages
- Number of active users
- Recent reaction count

**Examples:**
```
/groupmood  # Shows current group mood
```

---

#### `/groupmood-rebuild` - Rebuild Group Mood Data
Rebuilds group mood analysis data using different data sources. Admin only.

**Usage:**
```
/groupmood-rebuild <channel>|all [context|N|full]
```

**Parameters:**
- `<channel>|all`: Channel ID (e.g., -123456789) or 'all' for all channels
- `[context|N|full]`: Data source (optional, default: context)
  - `context`: Use current stored context messages
  - `N`: Use last N messages from Telegram API
  - `full`: Use full chat history from Telegram API

**Examples:**
```
/groupmood-rebuild -123456789        # Rebuild specific channel using context
/groupmood-rebuild all full          # Rebuild all channels using full history
/groupmood-rebuild -123456789 N      # Rebuild channel using last N messages
```

**Features:**
- Batch processing for performance
- Progress updates for large operations
- Uses batching when processing multiple channels

---

#### `/profiles-rebuild` - Rebuild User Profiles
Rebuilds AI user profiles using different data sources. Admin only.

**Usage:**
```
/profiles-rebuild <user>|all [context|N|full] [<channel>]
```

**Parameters:**
- `<user>|all`: User ID (e.g., 123456789) or 'all' for all existing profiles
- `[context|N|full]`: Data source (optional, default: context)
  - `context`: Use current stored context messages
  - `N`: Use last N messages from Telegram API
  - `full`: Use full chat history from Telegram API
- `[<channel>]`: Optional channel ID to limit data source

**Examples:**
```
/profiles-rebuild 123456789              # Rebuild specific user using context
/profiles-rebuild all full               # Rebuild all profiles using full history
/profiles-rebuild all N -123456789       # Rebuild all profiles using last N messages from specific channel
/profiles-rebuild 123456789 context      # Rebuild user using context messages
```

**Features:**
- Batch processing for performance
- Progress updates for large operations
- AI-powered profile enrichment
- Channel filtering support

**Notes:**
- 'all' rebuilds only users who already have profiles
- Uses AI to extract interests, weaknesses, and behavior patterns

---

## Access Control

### User Level
- `/joke` - Generate jokes
- `/joke <topic>` - Generate topic-specific jokes
- `/ask <question>` - Free-form AI requests
- `/help` - View this help (shows user-level commands only)
- `/context` - Clear current chat context (group chats only)

### Administrator Level
All user commands plus:
- `/reload` - Hot-reload configuration (private chat only)
- `/comment <chat_id>` - Force autonomous comment
- `/context <chat_id>` - Clear any chat's context
- `/profile <user>` - View user profiles
- `/groupmood-rebuild <channel>|all [context|N|full]` - Rebuild group mood data
- `/profiles-rebuild <user>|all [context|N|full] [<channel>]` - Rebuild user profiles

### Setting Administrators

Edit `config.yaml`:
```yaml
bot:
  admin_user_ids: [123456789, 987654321]  # Add admin user IDs
```

Then reload with `/reload` or restart the bot.

---

## Command Restrictions

### Private Chat Only
- `/reload` - Configuration changes should be deliberate
- All admin commands should be sent to bot privately

### Admin Verification
The bot verifies admin status for:
- `/reload`
- `/comment`
- `/context` (with chat_id parameter)
- `/profile`

Non-admins receive:
```
❌ Unauthorized. Only bot administrators can use this command.
```

---

## Use Cases

### Clear Context After Long Discussion
```
/context
```
Useful when topic changes or conversation gets too long.

### Check User's Weaknesses Before Roasting
```
/profile @username
```
View what the bot knows about a user for better roasting.

### Force Comment in Quiet Chat
```
/comment -1001234567890
```
Make bot comment when it hasn't spoken in a while.

### View Your Own Profile
```
/profile 123456789  # Your user ID
```
See what the bot has learned about you.

---

## Privacy Considerations

### Profile Data
- Stored locally in `profiles/users/`
- Only accessible by administrators
- Can be deleted manually from filesystem
- Auto-saved periodically

### Context Data
- Stored locally in `context_history/`
- Can be cleared with `/context`
- Auto-expires based on configuration
- Not shared between chats

---

## Troubleshooting

### "No profile found"
- User may not have interacted with bot yet
- Try different search method (ID, username, name)
- Check spelling

### "Only administrators can..."
- Your user ID is not in `admin_user_ids`
- Edit `config.yaml` and add your ID
- Use `/help` to see your current ID
- Reload with `/reload`

### Context not clearing
- Ensure you have permission
- Check chat ID is correct
- Try without chat_id parameter in current chat

---

## Security Best Practices

1. **Limit Admin Access**
   - Only add trusted user IDs
   - Don't share admin credentials

2. **Use Private Chat**
   - Execute admin commands in private chat
   - Don't expose user IDs in groups

3. **Regular Monitoring**
   - Check logs for unauthorized attempts
   - Review profile data periodically

4. **Backup Profiles**
   - Keep backups of `profiles/` directory
   - Useful for recovering deleted data

---

## Command Reference Quick List

### User Commands
```
 /help                    - Show available commands
 /joke                    - Generate contextual joke
 /joke <topic>           - Generate joke about topic
 /ask <question>         - Ask AI question
 /context                 - Clear current chat context
 /groupmood               - Show current group sentiment
```

### Admin Commands (Private Chat)
```
 /reload                  - Reload bot configuration
 /comment <chat_id>       - Force bot comment
 /context <chat_id>       - Clear specific chat context
 /profile <identifier>    - View user profile
 /groupmood-rebuild <channel>|all [source]  - Rebuild group mood data
 /profiles-rebuild <user>|all [source] [channel]  - Rebuild user profiles
```

### Getting Your User ID
Use `/help` command to see your user ID displayed at the top.

---

## Developer Notes

### Adding New Admin Commands
1. Add handler in `handlers/message_handler.py`
2. Register in `bot.py`
3. Update this documentation
4. Test with admin and non-admin accounts

### Command Pattern
All admin commands should:
- Check admin privileges
- Log attempts (authorized and unauthorized)
- Provide clear error messages
- Use private chat when sensitive

---

## See Also
- [README.md](README.md) - General bot documentation
- [AUTONOMOUS_FEATURES.md](AUTONOMOUS_FEATURES.md) - Autonomous features guide
- [config.yaml](config.yaml) - Configuration file
