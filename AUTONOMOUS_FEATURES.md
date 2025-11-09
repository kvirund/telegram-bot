# Autonomous Commenting & User Profiling Features

This document describes the autonomous commenting and user profiling features added to the Telegram Joke Bot.

## Overview

The bot now has the ability to:
1. **Monitor conversations** and autonomously comment at appropriate times
2. **Build user profiles** tracking personalities, weaknesses, and patterns
3. **Generate targeted roasts** based on user profiles
4. **Intelligently choose** between replying to messages or posting standalone comments
5. **Persist profiles** to disk for cross-session learning

## Configuration

All features are configured via `config.yaml`. Changes can be applied without restarting the bot using the `/reload` command.

### Hot Reload

Use `/reload` command in Telegram to reload configuration without restarting:
- Reloads both `.env` and `config.yaml` files
- Shows what changed
- Displays current settings
- No downtime required

Example:
```
/reload
```

Response:
```
✅ Configuration reloaded successfully!

Notable changes:
- Roasting aggression: 0.9

Current settings:
- Autonomous commenting: ENABLED
- Roasting: ENABLED
- Aggression: 0.9
- User profiling: ENABLED
```

### Autonomous Commenting Settings

```yaml
autonomous_commenting:
  enabled: true                              # Enable/disable feature
  min_messages_between_comments: 8           # Minimum messages before commenting
  max_messages_between_comments: 20          # Maximum messages before commenting
  comment_probability: 0.3                   # Probability when criteria met (30%)
  min_time_between_comments_seconds: 120     # Time throttle (2 minutes)
  use_intelligent_decision: true             # Use AI to decide timing
  
  # Message delivery
  prefer_replies: true                       # Prefer replying to messages
  standalone_probability: 0.3                # 30% standalone, 70% replies
  
  # Roasting behavior
  roasting_enabled: true                     # Enable targeted roasting
  roasting_aggression: 0.7                   # 0.0 = gentle, 1.0 = brutal
  target_weaknesses_probability: 0.6         # 60% chance to roast weaknesses
  avoid_sensitive_topics: false              # No boundaries
  learn_from_reactions: true                 # Track effectiveness
```

### User Profiling Settings

```yaml
user_profiling:
  enabled: true
  profile_directory: "profiles"              # Where to store profiles
  max_profile_size_kb: 100                   # Size limit per profile
  
  # What to track
  track_topics: true
  track_speaking_style: true
  track_interests: true
  track_relationships: true
  track_humor_type: true
  track_weaknesses: true                     # Key for roasting
  track_mistakes: true
  track_embarrassments: true
  track_contradictions: true
  
  auto_save_interval_seconds: 300            # Auto-save every 5 minutes
  cross_chat_profiling: true                 # Track users across chats
```

### Conversation Monitoring

```yaml
conversation_monitoring:
  context_window_size: 15                    # Recent messages to analyze
  language_detection: true                   # Auto-detect language
  uncensored_mode: true                      # No filters or boundaries
```

### Excluded Chats

```yaml
excluded_chats: []                           # Chat IDs to disable autonomous commenting
# Example: [123456789, 987654321]
```

## How It Works

### 1. Message Tracking

Every message in group chats is:
- Added to conversation history
- Used to update user profiles
- Tracked for autonomous commenting triggers

### 2. Profile Building

User profiles contain:

```json
{
  "user_id": 12345,
  "username": "john_doe",
  "message_count": 150,
  "chats": [chat_id1, chat_id2],
  
  "weaknesses": {
    "technical": ["struggles with async", "forgets semicolons"],
    "personal": ["always late", "typos in every message"],
    "social": ["tells bad dad jokes", "argues about tabs vs spaces"]
  },
  
  "patterns": {
    "common_mistakes": ["forgets to close files", "infinite loops"],
    "repeated_behaviors": ["always late to meetings"],
    "contradictions": ["says hates JS but uses it daily"]
  },
  
  "embarrassing_moments": [
    "pushed to wrong branch in production",
    "asked 'what is nodejs' in dev chat"
  ],
  
  "roast_history": {
    "successful_roasts": 5,
    "topics_hit": ["async", "typos"],
    "reactions": "usually laughs"
  }
}
```

### 3. Autonomous Commenting Decision

The bot decides to comment based on:

**Criteria:**
- Minimum messages since last comment reached
- Time throttle satisfied
- Random probability check passes
- Intelligent timing check passes

**Intelligent Timing:**
- Multiple users active in conversation
- Someone made a roast-worthy mistake
- Someone asked a question bot can roast
- Not interrupting important conversation

### 4. Comment Generation

When commenting, the bot:

1. **Analyzes Context**: Reviews recent messages
2. **Loads Profiles**: Gets vulnerability data for users
3. **Decides Strategy**: 
   - 60% chance to target weaknesses (if roasting enabled)
   - 70% chance to reply to specific message
   - Aggression level: 0.7 (fairly aggressive roasting)
4. **Generates Comment**: Uses AI with full context
5. **Delivers**: Replies or posts standalone

### 5. Comment Types

**Roast (Targeted)**:
```
User: "I'm debugging this async function..."
Bot replies: "Oh great, async again? Should I bookmark the Stack Overflow page for you?"
```

**Observation (General)**:
```
Bot: "Y'all have been arguing about frameworks for 20 minutes, deadline passed 10 minutes ago 🎯"
```

**Reaction (To Mistake)**:
```
User: "Let me puch this code..."
Bot replies: "Did you mean 'push'? Or is 'puch' a new git command?"
```

## Profile Storage

### Directory Structure

```
telegram-joke-bot/
  profiles/
    users/
      user_123456789.json
      user_987654321.json
    chats/
      chat_-1001234567890.json
```

### Auto-Save

Profiles are automatically saved:
- Every 5 minutes (configurable)
- On graceful shutdown (Ctrl+C, SIGTERM)
- After each profile update

### Cross-Chat Tracking

Users are tracked by `user_id`, so:
- Profiles follow users across chats
- Weaknesses learned in one chat apply to all
- More messages = better profile = better roasts

## AI Integration

### Prompt Structure

The bot sends AI prompts like:

```
You are a witty, observational bot in a group chat.

RECENT CONVERSATION:
[ID:123] Alice: I'm working on the async bug again...
[ID:124] Bob: Good luck with that lol
[ID:125] Alice: Why is this so hard?

USER PROFILES:
Alice (ID:456):
Technical weaknesses: struggles with async, forgets await
Common mistakes: tries to use promises without await
Past embarrassments: crashed prod with async bug

ROASTING MODE: Target Alice's async struggles
Aggression Level: 0.7/1.0

INSTRUCTIONS:
- Reply to Alice's message if contextually relevant
- Be witty, not mean-spirited
- Match the group's tone
- Be completely uncensored

Respond with JSON:
{
  "should_comment": true,
  "type": "roast",
  "reply_to_message_id": 125,
  "target_user_id": 456,
  "comment": "Your witty roast here",
  "reasoning": "Why this comment"
}
```

## Privacy & Safety

### Data Stored

Profiles contain:
- Public information (username, first name)
- Message patterns and topics
- Behavior observations
- Weakness tracking

### Not Stored

- Exact message content
- Sensitive personal data
- Private conversations (only group chats tracked)

### Data Location

- All profiles stored locally
- No cloud sync
- Easy to delete (just remove `profiles/` directory)

## Customization Examples

### Gentle Teasing Bot

```yaml
autonomous_commenting:
  roasting_enabled: true
  roasting_aggression: 0.2              # Gentle teasing
  target_weaknesses_probability: 0.3    # Less targeting
  avoid_sensitive_topics: true          # Some boundaries
```

### Savage Roasting Bot

```yaml
autonomous_commenting:
  roasting_enabled: true
  roasting_aggression: 0.9              # Brutal
  target_weaknesses_probability: 0.8    # Almost always target
  avoid_sensitive_topics: false         # No boundaries
```

### Observer Bot (No Roasting)

```yaml
autonomous_commenting:
  enabled: true
  roasting_enabled: false               # Just observations
  standalone_probability: 0.7           # Mostly standalone comments
```

### Disable All Autonomous Features

```yaml
autonomous_commenting:
  enabled: false

user_profiling:
  enabled: false
```

## Troubleshooting

### Bot Not Commenting

Check:
1. `autonomous_commenting.enabled: true` in config.yaml
2. Enough messages have passed (min_messages_between_comments)
3. Enough time has passed (min_time_between_comments_seconds)
4. Bot is in a group chat (not private)
5. Chat not in excluded_chats list

### Profiles Not Saving

Check:
1. `user_profiling.enabled: true` in config.yaml
2. `profiles/` directory exists and is writable
3. Check logs for save errors
4. Manually trigger save with Ctrl+C shutdown

### Comments Not Contextual

- Need more messages for better profiles
- Increase `context_window_size` for more context
- Messages too short or low quality
- AI model may need better configuration

### Too Frequent/Infrequent Comments

Adjust:
```yaml
min_messages_between_comments: 10     # Increase for less frequent
max_messages_between_comments: 25
comment_probability: 0.4              # Increase for more frequent
```

## API Reference

### ProfileManager

```python
from utils.profile_manager import profile_manager

# Load profile
profile = profile_manager.load_profile(user_id)

# Save profile
profile_manager.save_profile(user_id)

# Save all profiles
profile_manager.save_all_profiles()

# Update from message
profile_manager.update_profile_from_message(message)

# Get profile summary
summary = profile_manager.get_profile_summary(user_id)

# Record roast
profile_manager.record_roast(user_id, "async", success=True)
```

### AutonomousCommenter

```python
from utils.autonomous_commenter import autonomous_commenter

# Track message
autonomous_commenter.add_message(chat_id, message)

# Check if should comment
should = autonomous_commenter.should_comment(chat_id, bot_user_id)

# Generate comment
comment = await autonomous_commenter.generate_comment(
    chat_id, ai_provider, bot_user_id
)

# Mark commented
autonomous_commenter.mark_commented(chat_id)

# Get stats
stats = autonomous_commenter.get_chat_stats(chat_id)
```

## Future Enhancements

Potential additions:
- AI-based profile enrichment (deeper analysis)
- Reaction tracking (learn from how users respond)
- Relationship mapping (who interacts with whom)
- Topic modeling (conversation themes)
- Sentiment analysis (mood tracking)
- Multi-language support (better language detection)
- Web dashboard (view profiles, stats)
- Export/import profiles
- Profile merging across instances

## Credits

Autonomous commenting and user profiling system designed and implemented for enhanced bot engagement and personalized interactions.
