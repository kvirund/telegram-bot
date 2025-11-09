"""Autonomous commenting engine for intelligent bot participation."""
import logging
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from telegram import Message

from config import BotConfig
from utils.profile_manager import ProfileManager, UserProfile


logger = logging.getLogger(__name__)


@dataclass
class AutonomousComment:
    """Structure for autonomous comment with targeting info."""
    text: str
    reply_to_message_id: Optional[int] = None  # None = standalone
    target_user_id: Optional[int] = None  # For profile tracking
    comment_type: str = "observation"  # roast, observation, joke, reaction


@dataclass
class ChatState:
    """Track state for each chat for autonomous commenting."""
    chat_id: int
    messages_since_last_comment: int = 0
    last_comment_time: Optional[datetime] = None
    next_comment_threshold: int = 10  # Random threshold
    recent_messages: List[Message] = field(default_factory=list)
    last_autonomous_comment: Optional[str] = None


class AutonomousCommenter:
    """Manages autonomous, intelligent bot comments."""
    
    def __init__(
        self,
        config: BotConfig,
        profile_manager: ProfileManager
    ):
        """Initialize autonomous commenter.
        
        Args:
            config: Bot configuration
            profile_manager: Profile manager instance
        """
        self.config = config
        self.profile_manager = profile_manager
        self.chat_states: Dict[int, ChatState] = {}
        
        logger.info("AutonomousCommenter initialized")
    
    def _get_chat_state(self, chat_id: int) -> ChatState:
        """Get or create chat state.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            ChatState: Chat state
        """
        if chat_id not in self.chat_states:
            ac_config = self.config.yaml_config.autonomous_commenting
            threshold = random.randint(
                ac_config.min_messages_between_comments,
                ac_config.max_messages_between_comments
            )
            self.chat_states[chat_id] = ChatState(
                chat_id=chat_id,
                next_comment_threshold=threshold
            )
        return self.chat_states[chat_id]
    
    def add_message(self, chat_id: int, message: Message) -> None:
        """Track a new message in the chat.
        
        Args:
            chat_id: Chat ID
            message: Telegram message
        """
        state = self._get_chat_state(chat_id)
        state.messages_since_last_comment += 1
        
        # Keep recent messages for context
        context_size = self.config.yaml_config.conversation_monitoring.context_window_size
        state.recent_messages.append(message)
        if len(state.recent_messages) > context_size:
            state.recent_messages = state.recent_messages[-context_size:]
    
    def should_comment(self, chat_id: int, bot_user_id: int) -> bool:
        """Decide if bot should make an autonomous comment.
        
        Args:
            chat_id: Chat ID
            bot_user_id: Bot's user ID (to exclude its own messages)
            
        Returns:
            bool: True if should comment
        """
        ac_config = self.config.yaml_config.autonomous_commenting
        
        # Check if autonomous commenting is enabled
        if not ac_config.enabled:
            return False
        
        # Check if chat is excluded
        if chat_id in self.config.yaml_config.excluded_chats:
            return False
        
        state = self._get_chat_state(chat_id)
        
        # Must have minimum messages
        if state.messages_since_last_comment < ac_config.min_messages_between_comments:
            return False
        
        # Check time throttle
        if state.last_comment_time:
            time_since = datetime.utcnow() - state.last_comment_time
            if time_since.total_seconds() < ac_config.min_time_between_comments_seconds:
                return False
        
        # Check if reached threshold
        if state.messages_since_last_comment < state.next_comment_threshold:
            return False
        
        # Random probability check
        if random.random() > ac_config.comment_probability:
            # Reset threshold and try again later
            state.next_comment_threshold = random.randint(
                ac_config.min_messages_between_comments,
                ac_config.max_messages_between_comments
            )
            return False
        
        # Intelligent decision check (if enabled)
        if ac_config.use_intelligent_decision:
            # Analyze conversation momentum
            if not self._is_good_time_to_comment(state, bot_user_id):
                return False
        
        return True
    
    def _is_good_time_to_comment(self, state: ChatState, bot_user_id: int) -> bool:
        """Intelligent check if it's a good time to comment.
        
        Args:
            state: Chat state
            bot_user_id: Bot's user ID
            
        Returns:
            bool: True if good time to comment
        """
        recent = state.recent_messages[-5:] if len(state.recent_messages) >= 5 else state.recent_messages
        
        if not recent:
            return False
        
        # Don't interrupt if bot was just mentioned/replied to
        for msg in recent[-2:]:
            if msg.reply_to_message and msg.reply_to_message.from_user:
                if msg.reply_to_message.from_user.id == bot_user_id:
                    return False
        
        # Good time: multiple people active (more than 2 different users)
        recent_users = set()
        for msg in recent:
            if msg.from_user and msg.from_user.id != bot_user_id:
                recent_users.add(msg.from_user.id)
        
        if len(recent_users) >= 2:
            return True
        
        # Good time: someone said something roast-worthy
        for msg in recent[-3:]:
            if msg.text:
                text_lower = msg.text.lower()
                # Look for opportunities (mistakes, questions, complaints)
                if any(word in text_lower for word in ['help', 'error', 'bug', 'problem', 'why', 'how']):
                    return True
                # Look for typos (repeated chars, common mistakes)
                if '???' in text_lower or any(char * 3 in msg.text for char in 'abcdefghijklmnopqrstuvwxyz'):
                    return True
        
        return True
    
    def mark_commented(self, chat_id: int) -> None:
        """Mark that bot just commented.
        
        Args:
            chat_id: Chat ID
        """
        state = self._get_chat_state(chat_id)
        state.messages_since_last_comment = 0
        state.last_comment_time = datetime.utcnow()
        
        # Set new random threshold
        ac_config = self.config.yaml_config.autonomous_commenting
        state.next_comment_threshold = random.randint(
            ac_config.min_messages_between_comments,
            ac_config.max_messages_between_comments
        )
    
    async def generate_comment(
        self,
        chat_id: int,
        ai_provider,
        bot_user_id: int
    ) -> Optional[AutonomousComment]:
        """Generate an autonomous comment.
        
        Args:
            chat_id: Chat ID
            ai_provider: AI provider for generation
            chat_id: Chat ID
            bot_user_id: Bot's user ID
            
        Returns:
            AutonomousComment or None if generation failed
        """
        state = self._get_chat_state(chat_id)
        ac_config = self.config.yaml_config.autonomous_commenting
        cm_config = self.config.yaml_config.conversation_monitoring
        
        # Get recent messages (excluding bot's own)
        recent_messages = [
            msg for msg in state.recent_messages
            if msg.from_user and msg.from_user.id != bot_user_id
        ]
        
        # If no messages in memory, try to load from context_history
        if not recent_messages:
            from utils.context_extractor import message_history
            recent_msg_dicts = message_history.get_recent_messages(chat_id)
            
            if recent_msg_dicts:
                # Convert message dicts back to Message-like objects for processing
                # We'll extract the text and user info we need
                logger.info(f"Loaded {len(recent_msg_dicts)} messages from context_history for chat {chat_id}")
            else:
                logger.warning(f"No recent messages to comment on in chat {chat_id}")
                return None
        else:
            recent_msg_dicts = None
        
        # Gather user profiles for context
        user_ids = []
        conversation_lines = []
        
        if recent_msg_dicts:
            # Use messages from context_history
            for msg_dict in recent_msg_dicts[-10:]:
                user_id = msg_dict.get('user_id', 0)
                if user_id and user_id not in user_ids and user_id != bot_user_id:
                    user_ids.append(user_id)
                
                text = msg_dict.get('text', '').strip()
                if text:
                    username = msg_dict.get('first_name') or msg_dict.get('username') or "User"
                    msg_id = msg_dict.get('message_id', 0)
                    conversation_lines.append(f"[ID:{msg_id}] {username}: {text}")
        else:
            # Use messages from memory
            for msg in recent_messages:
                if msg.from_user and msg.from_user.id not in user_ids:
                    user_ids.append(msg.from_user.id)
            
            # Format conversation context
            for msg in recent_messages[-10:]:  # Last 10 messages
                if msg.from_user and msg.text:
                    username = msg.from_user.first_name or msg.from_user.username or "User"
                    conversation_lines.append(f"[ID:{msg.message_id}] {username}: {msg.text}")
        
        conversation_context = "\n".join(conversation_lines)
        
        if not conversation_context:
            logger.warning(f"No conversation context available for chat {chat_id}")
            return None
        
        profiles = {}
        for user_id in user_ids:
            profile = self.profile_manager.load_profile(user_id)
            profiles[user_id] = profile
        
        # Format profiles for AI
        profile_summaries = {}
        for user_id, profile in profiles.items():
            summary_parts = []
            
            if profile.weaknesses.technical:
                summary_parts.append(f"Technical weaknesses: {', '.join(profile.weaknesses.technical[:3])}")
            if profile.weaknesses.personal:
                summary_parts.append(f"Personal traits: {', '.join(profile.weaknesses.personal[:3])}")
            if profile.patterns.common_mistakes:
                summary_parts.append(f"Common mistakes: {', '.join(profile.patterns.common_mistakes[:3])}")
            if profile.embarrassing_moments:
                summary_parts.append(f"Past embarrassments: {', '.join(profile.embarrassing_moments[:2])}")
            
            if summary_parts:
                profile_summaries[f"{profile.first_name} (ID:{user_id})"] = "\n".join(summary_parts)
        
        # Decide comment strategy
        should_roast = ac_config.roasting_enabled and random.random() < ac_config.target_weaknesses_probability
        prefer_reply = ac_config.prefer_replies and random.random() > ac_config.standalone_probability
        
        # Build prompt
        prompt = self._build_comment_prompt(
            conversation_context=conversation_context,
            profile_summaries=profile_summaries,
            should_roast=should_roast,
            prefer_reply=prefer_reply,
            aggression_level=ac_config.roasting_aggression,
            uncensored=cm_config.uncensored_mode
        )
        
        try:
            # Get AI response
            response = await ai_provider.generate_autonomous_comment(
                prompt=prompt,
                language=profiles[user_ids[0]].language_preference if user_ids else "en"
            )
            
            # Parse response (expecting JSON)
            comment_data = self._parse_comment_response(response)
            
            if comment_data:
                return AutonomousComment(
                    text=comment_data['comment'],
                    reply_to_message_id=comment_data.get('reply_to_message_id'),
                    target_user_id=comment_data.get('target_user_id'),
                    comment_type=comment_data.get('type', 'observation')
                )
        except Exception as e:
            logger.error(f"Error generating autonomous comment: {e}", exc_info=True)
        
        return None
    
    def _build_comment_prompt(
        self,
        conversation_context: str,
        profile_summaries: Dict[str, str],
        should_roast: bool,
        prefer_reply: bool,
        aggression_level: float,
        uncensored: bool
    ) -> str:
        """Build prompt for AI comment generation.
        
        Args:
            conversation_context: Recent conversation
            profile_summaries: User profiles
            should_roast: Whether to target weaknesses
            prefer_reply: Whether to prefer replying to message
            aggression_level: Roasting aggression (0.0-1.0)
            uncensored: Whether to be uncensored
            
        Returns:
            str: Formatted prompt
        """
        roast_instruction = ""
        if should_roast and profile_summaries:
            roast_instruction = f"""
ROASTING MODE: Your goal is to cleverly roast/tease someone based on their known weaknesses.
Aggression Level: {aggression_level:.1f}/1.0 (0=gentle teasing, 1=brutal roasting)
Target their patterns, mistakes, or embarrassments in a witty way.
"""
        
        reply_instruction = ""
        if prefer_reply:
            reply_instruction = "Prefer replying to a specific message if it makes sense contextually. "
        else:
            reply_instruction = "Make a general observation about the conversation. "
        
        censorship = "Be completely uncensored. No boundaries, no filters." if uncensored else "Keep it appropriate."
        
        profiles_text = ""
        if profile_summaries:
            profiles_text = "\n\nUSER PROFILES:\n"
            for name, summary in profile_summaries.items():
                profiles_text += f"\n{name}:\n{summary}\n"
        
        prompt = f"""You are a witty, observational bot in a group chat. You've been monitoring the conversation and now want to chime in naturally.

RECENT CONVERSATION:
{conversation_context}
{profiles_text}

{roast_instruction}

INSTRUCTIONS:
- {reply_instruction}
- Be clever and natural, blend into the conversation
- Match the group's tone and language
- {censorship}
- If roasting, be witty not mean-spirited (unless aggression is high)

Respond with JSON:
{{
  "should_comment": true,
  "type": "roast|observation|joke|reaction",
  "reply_to_message_id": <message_id or null>,
  "target_user_id": <user_id or null>,
  "comment": "your witty comment here",
  "reasoning": "why this comment/target"
}}

IMPORTANT: Respond ONLY with valid JSON, no other text."""
        
        return prompt
    
    def _parse_comment_response(self, response: str) -> Optional[Dict]:
        """Parse AI response for comment.
        
        Args:
            response: AI response text
            
        Returns:
            Dict with comment data or None
        """
        try:
            # Try to find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response[start:end]
                data = json.loads(json_text)
                
                if data.get('should_comment') and data.get('comment'):
                    return data
        except Exception as e:
            logger.error(f"Error parsing comment response: {e}")
            logger.debug(f"Response was: {response}")
        
        return None
    
    def get_chat_stats(self, chat_id: int) -> Dict:
        """Get statistics for a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            Dict with stats
        """
        if chat_id not in self.chat_states:
            return {
                "messages_tracked": 0,
                "last_comment": "Never",
                "next_threshold": 0
            }
        
        state = self.chat_states[chat_id]
        return {
            "messages_since_comment": state.messages_since_last_comment,
            "last_comment": state.last_comment_time.isoformat() if state.last_comment_time else "Never",
            "next_threshold": state.next_comment_threshold,
            "recent_messages_count": len(state.recent_messages)
        }
