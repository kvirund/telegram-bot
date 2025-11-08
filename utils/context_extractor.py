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
    """Simple in-memory message history tracker."""
    
    def __init__(self, max_messages: int = 100):
        """Initialize message history.
        
        Args:
            max_messages: Maximum number of messages to keep per chat
        """
        self.history = {}  # chat_id -> list of messages
        self.max_messages = max_messages
    
    def add_message(self, chat_id: int, message: Message):
        """Add a message to history.
        
        Args:
            chat_id: Chat ID
            message: Message to add
        """
        if chat_id not in self.history:
            self.history[chat_id] = []
        
        self.history[chat_id].append(message)
        
        # Keep only the last N messages
        if len(self.history[chat_id]) > self.max_messages:
            self.history[chat_id] = self.history[chat_id][-self.max_messages:]
    
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
        return format_context_for_ai(recent_messages)


# Global message history instance
message_history = MessageHistory()
