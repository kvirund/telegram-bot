"""Reaction management system for tracking and adding reactions."""
import logging
import random
import time
from typing import Optional
from telegram import Update


logger = logging.getLogger(__name__)


class ReactionManager:
    """Manages bot reactions to messages."""
    
    def __init__(self, config):
        """Initialize reaction manager.
        
        Args:
            config: Bot configuration
        """
        self.config = config
        self.last_reaction_time = {}  # chat_id -> timestamp
    
    def should_react(self, chat_id: int) -> bool:
        """Determine if bot should react to a message.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            bool: True if should react
        """
        if not self.config.yaml_config.reaction_system.enabled:
            logger.debug(f"Reaction system disabled, not reacting in chat {chat_id}")
            return False
        
        if not self.config.yaml_config.reaction_system.add_own_reactions:
            logger.debug(f"Bot reactions disabled, not reacting in chat {chat_id}")
            return False
        
        # Check time since last reaction
        last_time = self.last_reaction_time.get(chat_id, 0)
        time_since = time.time() - last_time
        min_time = self.config.yaml_config.reaction_system.min_time_between_reactions_seconds
        
        if time_since < min_time:
            logger.debug(f"Too soon to react in chat {chat_id} (last: {time_since:.1f}s ago, min: {min_time}s)")
            return False
        
        # Probability check
        should = random.random() < self.config.yaml_config.reaction_system.reaction_probability
        if not should:
            logger.debug(f"Probability check failed for reaction in chat {chat_id}")
        return should
    
    def mark_reacted(self, chat_id: int):
        """Mark that bot reacted in this chat.
        
        Args:
            chat_id: Chat ID
        """
        self.last_reaction_time[chat_id] = time.time()
    
    def choose_reaction(self, message_text: str) -> str:
        """Choose appropriate reaction based on message content.
        
        Args:
            message_text: Message text to react to
            
        Returns:
            str: Emoji reaction
        """
        text_lower = message_text.lower()
        reaction = None
        reason = "random"
        
        # Simple heuristic-based selection
        if any(word in text_lower for word in ['lol', 'haha', 'lmao', 'funny', 'joke', '😂', '🤣']):
            reaction = "😂"
            reason = "humor detected"
        elif any(word in text_lower for word in ['wtf', 'wow', 'omg', '!', 'shocking']):
            reaction = "😱"
            reason = "surprise detected"
        elif any(word in text_lower for word in ['good', 'great', 'awesome', 'perfect', 'nice', '👍']):
            reaction = "👍"
            reason = "positive sentiment"
        elif any(word in text_lower for word in ['fire', 'amazing', 'incredible', '🔥']):
            reaction = "🔥"
            reason = "enthusiasm detected"
        elif any(word in text_lower for word in ['hmm', 'think', '?', 'question']):
            reaction = "🤔"
            reason = "question/thinking"
        elif any(word in text_lower for word in ['watch', 'see', 'look', '👀']):
            reaction = "👀"
            reason = "attention keyword"
        elif any(word in text_lower for word in ['100', 'exactly', 'agree', 'true']):
            reaction = "💯"
            reason = "agreement"
        elif any(word in text_lower for word in ['right', 'correct', 'spot on', 'exactly']):
            reaction = "🎯"
            reason = "accuracy"
        else:
            # Random selection from available types
            reaction = random.choice(self.config.yaml_config.reaction_system.reaction_types)
            reason = "random choice"
        
        logger.info(f"Selected reaction {reaction} ({reason}) for message: {message_text[:50]}...")
        return reaction


# Global instance
reaction_manager: Optional[ReactionManager] = None


def get_reaction_manager(config):
    """Get or create reaction manager instance.
    
    Args:
        config: Bot configuration
        
    Returns:
        ReactionManager: Reaction manager instance
    """
    global reaction_manager
    if reaction_manager is None:
        reaction_manager = ReactionManager(config)
    return reaction_manager
