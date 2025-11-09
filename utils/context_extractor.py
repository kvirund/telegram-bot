"""Context extraction utility for fetching conversation history."""
import logging
from typing import List
from telegram import Bot, Message


logger = logging.getLogger(__name__)


async def extract_context(chat_id: int, message_id: int, count: int, bot: Bot) -> str:
    """Extract context from previous messages in the chat.
    
    Args:
        chat_id: The chat ID to fetch messages from
        message_id: The current message ID to use as reference
        count: Number of previous messages to fetch
        bot: The bot instance
        
    Returns:
        str: Formatted context string
    """
    try:
        messages = []
        current_id = message_id - 1  # Start from the message before the current one
        
        # Fetch previous messages
        for _ in range(count):
            if current_id <= 0:
                break
            
            try:
                msg = await bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=chat_id,
                    message_id=current_id
                )
                # Delete the forwarded message immediately
                await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                
                # Fetch the actual message
                # Note: This is a workaround since Telegram doesn't have a direct getMessage API
                # We'll use a different approach - store messages as we see them
                current_id -= 1
            except Exception as e:
                logger.debug(f"Could not fetch message {current_id}: {e}")
                current_id -= 1
                continue
        
        if not messages:
            logger.info("No previous messages found for context")
            return ""
        
        # Format context
        context = format_context_for_ai(messages)
        logger.info(f"Extracted context from {len(messages)} messages")
        return context
        
    except Exception as e:
        logger.error(f"Failed to extract context: {e}")
        return ""


def format_context_for_ai(messages: List[Message]) -> str:
    """Format messages into a readable context string for AI.
    
    Args:
        messages: List of Telegram messages
        
    Returns:
        str: Formatted context string
    """
    if not messages:
        return ""
    
    context_lines = []
    for msg in reversed(messages):  # Reverse to show oldest first
        text = sanitize_message(msg)
        if text:
            user_name = msg.from_user.first_name if msg.from_user else "Unknown"
            context_lines.append(f"{user_name}: {text}")
    
    return "\n".join(context_lines)


def sanitize_message(message: Message) -> str:
    """Remove sensitive data and extract text from a message.
    
    Args:
        message: Telegram message
        
    Returns:
        str: Sanitized message text
    """
    if not message:
        return ""
    
    # Extract text from message
    text = message.text or message.caption or ""
    
    # Remove bot commands for cleaner context
    if text.startswith('/'):
        return ""
    
    # Truncate very long messages
    max_length = 200
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()


# Alternative simpler implementation that works with message history
class MessageHistory:
    """Message history tracker with disk persistence and auto-expiration."""
    
    def __init__(self, max_messages: int = 100, storage_dir: str = "context_history", 
                 expiration_hours: int = 24):
        """Initialize message history.
        
        Args:
            max_messages: Maximum number of messages to keep per chat
            storage_dir: Directory to store context history
            expiration_hours: Hours after which messages expire (default 24)
        """
        self.history = {}  # chat_id -> list of message dicts
        self.max_messages = max_messages
        self.storage_dir = storage_dir
        self.expiration_seconds = expiration_hours * 3600
        
        # Create storage directory
        import os
        os.makedirs(storage_dir, exist_ok=True)
        
        # Load existing context from disk
        self._load_context_history()
        
        logger.info(f"MessageHistory initialized with {expiration_hours}h expiration")
    
    def _load_context_history(self):
        """Load context history from disk."""
        import os
        import json
        import time
        
        current_time = time.time()
        loaded_chats = 0
        expired_messages = 0
        
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.json'):
                continue
            
            try:
                chat_id = int(filename.replace('chat_', '').replace('.json', ''))
                filepath = os.path.join(self.storage_dir, filename)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Filter out expired messages
                valid_messages = []
                for msg_data in data.get('messages', []):
                    if current_time - msg_data.get('timestamp', 0) < self.expiration_seconds:
                        valid_messages.append(msg_data)
                    else:
                        expired_messages += 1
                
                if valid_messages:
                    self.history[chat_id] = valid_messages
                    loaded_chats += 1
                else:
                    # Remove file if all messages expired
                    os.remove(filepath)
                    
            except Exception as e:
                logger.warning(f"Failed to load context history from {filename}: {e}")
        
        if loaded_chats > 0:
            logger.info(f"Loaded context history for {loaded_chats} chats (expired {expired_messages} messages)")
    
    def _save_context_history(self):
        """Save context history to disk."""
        import os
        import json
        
        saved_chats = 0
        for chat_id, messages in self.history.items():
            if not messages:
                continue
            
            try:
                filepath = os.path.join(self.storage_dir, f'chat_{chat_id}.json')
                data = {
                    'chat_id': chat_id,
                    'messages': messages
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                saved_chats += 1
            except Exception as e:
                logger.error(f"Failed to save context history for chat {chat_id}: {e}")
        
        if saved_chats > 0:
            logger.debug(f"Saved context history for {saved_chats} chats")
    
    def add_message(self, chat_id: int, message: Message):
        """Add a message to history and save to disk.
        
        Args:
            chat_id: Chat ID
            message: Message to add
        """
        import time
        
        if chat_id not in self.history:
            self.history[chat_id] = []
        
        # Convert message to dict for JSON storage
        message_data = {
            'text': message.text or '',
            'user_id': message.from_user.id if message.from_user else 0,
            'username': message.from_user.username if message.from_user else '',
            'first_name': message.from_user.first_name if message.from_user else 'Unknown',
            'timestamp': time.time(),
            'message_id': message.message_id
        }
        
        self.history[chat_id].append(message_data)
        
        # Keep only the last N messages
        if len(self.history[chat_id]) > self.max_messages:
            self.history[chat_id] = self.history[chat_id][-self.max_messages:]
        
        # Save to disk periodically (every 10 messages)
        if len(self.history[chat_id]) % 10 == 0:
            self._save_context_history()
    
    def get_context(self, chat_id: int, count: int = 10) -> str:
        """Get formatted context from recent messages.
        
        Args:
            chat_id: Chat ID
            count: Number of recent messages to include
            
        Returns:
            str: Formatted context string
        """
        if chat_id not in self.history:
            return ""
        
        recent_messages = self.history[chat_id][-count:]
        
        # Format message dicts into context string
        context_lines = []
        for msg_data in recent_messages:
            text = msg_data.get('text', '').strip()
            if text and not text.startswith('/'):
                user_name = msg_data.get('first_name', 'Unknown')
                # Truncate long messages
                if len(text) > 200:
                    text = text[:200] + "..."
                context_lines.append(f"{user_name}: {text}")
        
        return "\n".join(context_lines)
    
    def get_user_messages(self, chat_id: int, user_id: int, count: int = 20) -> str:
        """Get formatted messages from a specific user only.
        
        Args:
            chat_id: Chat ID
            user_id: User ID to filter messages for
            count: Maximum number of messages to include
            
        Returns:
            str: Formatted string of user's messages
        """
        if chat_id not in self.history:
            return ""
        
        # Filter messages for this specific user
        user_messages = [
            msg for msg in self.history[chat_id]
            if msg.get('user_id') == user_id
        ]
        
        # Get most recent messages
        recent = user_messages[-count:]
        
        # Format into context string (just the text, no username prefix since it's all one user)
        message_lines = []
        for msg_data in recent:
            text = msg_data.get('text', '').strip()
            if text and not text.startswith('/'):
                # Don't truncate - we want full context for profiling
                message_lines.append(text)
        
        return "\n".join(message_lines)
    
    def cleanup_expired(self):
        """Remove expired messages from all chats."""
        import time
        
        current_time = time.time()
        removed_count = 0
        
        for chat_id in list(self.history.keys()):
            valid_messages = [
                msg for msg in self.history[chat_id]
                if current_time - msg.get('timestamp', 0) < self.expiration_seconds
            ]
            removed_count += len(self.history[chat_id]) - len(valid_messages)
            
            if valid_messages:
                self.history[chat_id] = valid_messages
            else:
                del self.history[chat_id]
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired context messages")
            self._save_context_history()
    
    def save_all(self):
        """Save all context history to disk."""
        self._save_context_history()
    
    def get_all_chat_ids(self) -> List[int]:
        """Get list of all chat IDs with message history.
        
        Returns:
            List[int]: List of chat IDs
        """
        return list(self.history.keys())
    
    def get_recent_messages(self, chat_id: int):
        """Get recent messages for a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            List of message dicts or None
        """
        return self.history.get(chat_id)
    
    def clear_chat_history(self, chat_id: int):
        """Clear all message history for a chat.
        
        Args:
            chat_id: Chat ID to clear
        """
        import os
        
        if chat_id in self.history:
            del self.history[chat_id]
            logger.info(f"Cleared message history for chat {chat_id}")
        
        # Also remove the file
        filepath = os.path.join(self.storage_dir, f'chat_{chat_id}.json')
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Removed context file for chat {chat_id}")
            except Exception as e:
                logger.error(f"Failed to remove context file for chat {chat_id}: {e}")


# Global message history instance
message_history = MessageHistory()
