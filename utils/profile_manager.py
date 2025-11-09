"""User profile management for tracking user behavior and weaknesses."""
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from telegram import Message


logger = logging.getLogger(__name__)


@dataclass
class SpeakingStyle:
    """User's speaking style characteristics."""
    tone: str = "neutral"  # casual, formal, sarcastic, etc.
    vocabulary_level: str = "medium"  # basic, medium, technical, advanced
    emoji_usage: str = "moderate"  # rare, moderate, frequent
    message_length: str = "medium"  # short, medium, long
    typo_frequency: str = "low"  # low, medium, high


@dataclass
class UserWeaknesses:
    """User's weaknesses categorized by type."""
    technical: List[str] = field(default_factory=list)
    personal: List[str] = field(default_factory=list)
    social: List[str] = field(default_factory=list)


@dataclass
class UserPatterns:
    """User's behavioral patterns."""
    common_mistakes: List[str] = field(default_factory=list)
    repeated_behaviors: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)


@dataclass
class RoastHistory:
    """Track roasting effectiveness."""
    successful_roasts: int = 0
    topics_hit: List[str] = field(default_factory=list)
    reactions: str = "unknown"  # laughs, defends, ignores, etc.
    last_roasted: Optional[str] = None


@dataclass
class UserProfile:
    """Complete user profile with all tracked information."""
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    first_seen: str = ""
    last_seen: str = ""
    message_count: int = 0
    chats: List[int] = field(default_factory=list)
    
    # Tracked attributes
    topics: Dict[str, int] = field(default_factory=dict)  # topic: count
    speaking_style: SpeakingStyle = field(default_factory=SpeakingStyle)
    interests: List[str] = field(default_factory=list)
    humor_type: str = "unknown"
    
    # Weakness tracking
    weaknesses: UserWeaknesses = field(default_factory=UserWeaknesses)
    embarrassing_moments: List[str] = field(default_factory=list)
    complaint_topics: List[str] = field(default_factory=list)
    patterns: UserPatterns = field(default_factory=UserPatterns)
    
    # Social tracking
    relationships: Dict[int, str] = field(default_factory=dict)  # user_id: relationship_type
    language_preference: str = "en"
    
    # Roasting effectiveness
    roast_history: RoastHistory = field(default_factory=RoastHistory)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create profile from dictionary."""
        # Convert nested dataclasses
        if 'speaking_style' in data and isinstance(data['speaking_style'], dict):
            data['speaking_style'] = SpeakingStyle(**data['speaking_style'])
        if 'weaknesses' in data and isinstance(data['weaknesses'], dict):
            data['weaknesses'] = UserWeaknesses(**data['weaknesses'])
        if 'patterns' in data and isinstance(data['patterns'], dict):
            data['patterns'] = UserPatterns(**data['patterns'])
        if 'roast_history' in data and isinstance(data['roast_history'], dict):
            data['roast_history'] = RoastHistory(**data['roast_history'])
        
        return cls(**data)


class ProfileManager:
    """Manages user profiles with persistence to disk."""
    
    def __init__(self, profile_directory: str = "profiles"):
        """Initialize profile manager.
        
        Args:
            profile_directory: Directory to store profile files
        """
        self.profile_directory = profile_directory
        self.profiles: Dict[int, UserProfile] = {}  # user_id -> profile
        self.chat_metadata: Dict[int, Dict[str, Any]] = {}  # chat_id -> metadata
        
        # Create directory structure
        self.users_dir = os.path.join(profile_directory, "users")
        self.chats_dir = os.path.join(profile_directory, "chats")
        os.makedirs(self.users_dir, exist_ok=True)
        os.makedirs(self.chats_dir, exist_ok=True)
        
        logger.info(f"ProfileManager initialized with directory: {profile_directory}")
    
    def _get_user_profile_path(self, user_id: int) -> str:
        """Get file path for user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            str: Path to profile file
        """
        return os.path.join(self.users_dir, f"user_{user_id}.json")
    
    def _get_chat_metadata_path(self, chat_id: int) -> str:
        """Get file path for chat metadata.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            str: Path to chat metadata file
        """
        return os.path.join(self.chats_dir, f"chat_{chat_id}.json")
    
    def load_profile(self, user_id: int) -> UserProfile:
        """Load user profile from disk or create new one.
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfile: Loaded or new profile
        """
        # Check in-memory cache first
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        # Try to load from disk
        profile_path = self._get_user_profile_path(user_id)
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile = UserProfile.from_dict(data)
                    self.profiles[user_id] = profile
                    logger.info(f"Loaded profile for user {user_id}")
                    return profile
            except Exception as e:
                logger.error(f"Error loading profile for user {user_id}: {e}")
        
        # Create new profile
        profile = UserProfile(
            user_id=user_id,
            first_seen=datetime.utcnow().isoformat()
        )
        self.profiles[user_id] = profile
        logger.info(f"Created new profile for user {user_id}")
        return profile
    
    def save_profile(self, user_id: int) -> bool:
        """Save user profile to disk.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful
        """
        if user_id not in self.profiles:
            logger.warning(f"No profile to save for user {user_id}")
            return False
        
        try:
            profile = self.profiles[user_id]
            profile_path = self._get_user_profile_path(user_id)
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved profile for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving profile for user {user_id}: {e}")
            return False
    
    def update_profile_from_message(self, message: Message) -> None:
        """Update user profile based on message content.
        
        This is a lightweight update that extracts basic info.
        AI-based deep analysis happens separately.
        
        Args:
            message: Telegram message
        """
        if not message.from_user:
            return
        
        user = message.from_user
        user_id = user.id
        
        # Load or create profile
        profile = self.load_profile(user_id)
        
        # Update basic info
        profile.username = user.username or ""
        profile.first_name = user.first_name or ""
        profile.last_name = user.last_name or ""
        profile.last_seen = datetime.utcnow().isoformat()
        profile.message_count += 1
        
        # Track chat participation
        chat_id = message.chat_id
        if chat_id not in profile.chats:
            profile.chats.append(chat_id)
        
        # Detect language (simple heuristic)
        if message.text:
            # Cyrillic characters indicate Russian
            if any('\u0400' <= char <= '\u04FF' for char in message.text):
                profile.language_preference = "ru"
            elif profile.language_preference == "":
                profile.language_preference = "en"
    
    async def enrich_profile_with_ai(
        self,
        user_id: int,
        recent_messages: str,
        ai_analyzer
    ) -> None:
        """Use AI to extract deeper insights from messages.
        
        Args:
            user_id: User ID
            recent_messages: Recent message history for context
            ai_analyzer: AI provider for analysis
        """
        profile = self.load_profile(user_id)
        
        try:
            # Build analysis prompt
            analysis_prompt = f"""Проанализируй следующие сообщения пользователя и извлеки информацию о его личности.

Сообщения:
{recent_messages[:1000]}

ВАЖНО: Анализируй РЕАЛЬНЫЕ сообщения выше и извлекай РЕАЛЬНУЮ информацию о пользователе.
НЕ используй примеры - анализируй то, что реально видишь в сообщениях.

Верни ТОЛЬКО валидный JSON без текста до или после:
{{
  "interests": ["список реальных интересов из сообщений, если есть"],
  "technical_weaknesses": ["реальные технические проблемы, если упоминались"],
  "personal_weaknesses": ["личные слабости, если видны"],
  "speaking_tone": "casual или formal или sarcastic (оцени по стилю)",
  "humor_type": "sarcastic или witty или silly или unknown (оцени по сообщениям)",
  "common_mistakes": ["реальные ошибки или паттерны, если заметны"],
  "embarrassing_moments": ["неловкие моменты, если были"]
}}

Если информации нет - оставь пустой массив []. НЕ придумывай данные."""

            system_prompt = "Ты эксперт-психолог по анализу текстов. Анализируй ТОЛЬКО то, что реально видишь в сообщениях. Не придумывай данные. Отвечай ТОЛЬКО валидным JSON."
            
            # Get AI analysis
            response = await ai_analyzer.free_request(
                user_message=analysis_prompt,
                system_message=system_prompt
            )
            
            # Parse JSON response
            import json
            # Clean response - remove markdown code blocks if present
            response_clean = response.strip()
            if response_clean.startswith('```'):
                response_clean = response_clean.split('```')[1]
                if response_clean.startswith('json'):
                    response_clean = response_clean[4:]
            response_clean = response_clean.strip()
            
            analysis = json.loads(response_clean)
            
            # Update profile with AI insights
            if 'interests' in analysis:
                for interest in analysis['interests']:
                    if interest and interest not in profile.interests:
                        profile.interests.append(interest)
                # Keep only last 10
                profile.interests = profile.interests[-10:]
            
            if 'technical_weaknesses' in analysis:
                for weakness in analysis['technical_weaknesses']:
                    if weakness and weakness not in profile.weaknesses.technical:
                        profile.weaknesses.technical.append(weakness)
                profile.weaknesses.technical = profile.weaknesses.technical[-5:]
            
            if 'personal_weaknesses' in analysis:
                for weakness in analysis['personal_weaknesses']:
                    if weakness and weakness not in profile.weaknesses.personal:
                        profile.weaknesses.personal.append(weakness)
                profile.weaknesses.personal = profile.weaknesses.personal[-5:]
            
            if 'speaking_tone' in analysis:
                profile.speaking_style.tone = analysis['speaking_tone']
            
            if 'humor_type' in analysis:
                profile.humor_type = analysis['humor_type']
            
            if 'common_mistakes' in analysis:
                for mistake in analysis['common_mistakes']:
                    if mistake and mistake not in profile.patterns.common_mistakes:
                        profile.patterns.common_mistakes.append(mistake)
                profile.patterns.common_mistakes = profile.patterns.common_mistakes[-5:]
            
            if 'embarrassing_moments' in analysis:
                for moment in analysis['embarrassing_moments']:
                    if moment and moment not in profile.embarrassing_moments:
                        profile.embarrassing_moments.append(moment)
                profile.embarrassing_moments = profile.embarrassing_moments[-5:]
            
            logger.info(f"AI-enriched profile for user {user_id}")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI profile analysis for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error enriching profile for user {user_id}: {e}")
    
    def get_profile_summary(self, user_id: int) -> str:
        """Get formatted summary of user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            str: Formatted profile summary
        """
        profile = self.load_profile(user_id)
        
        parts = [
            f"User: {profile.first_name} (@{profile.username})",
            f"Messages: {profile.message_count}",
            f"Language: {profile.language_preference}",
        ]
        
        if profile.interests:
            parts.append(f"Interests: {', '.join(profile.interests[:5])}")
        
        if profile.weaknesses.technical:
            parts.append(f"Technical weaknesses: {', '.join(profile.weaknesses.technical[:3])}")
        
        if profile.weaknesses.personal:
            parts.append(f"Personal weaknesses: {', '.join(profile.weaknesses.personal[:3])}")
        
        if profile.patterns.common_mistakes:
            parts.append(f"Common mistakes: {', '.join(profile.patterns.common_mistakes[:3])}")
        
        return "\n".join(parts)
    
    def get_merged_context(
        self,
        user_ids: List[int],
        chat_id: int
    ) -> Dict[int, str]:
        """Get profile summaries for multiple users.
        
        Args:
            user_ids: List of user IDs
            chat_id: Chat ID for context
            
        Returns:
            Dict mapping user_id to profile summary
        """
        context = {}
        for user_id in user_ids:
            context[user_id] = self.get_profile_summary(user_id)
        return context
    
    def record_roast(
        self,
        target_user_id: int,
        roast_topic: str,
        success: bool = True
    ) -> None:
        """Record a roast attempt for tracking effectiveness.
        
        Args:
            target_user_id: User who was roasted
            roast_topic: Topic of the roast
            success: Whether the roast was successful
        """
        profile = self.load_profile(target_user_id)
        
        if success:
            profile.roast_history.successful_roasts += 1
            if roast_topic not in profile.roast_history.topics_hit:
                profile.roast_history.topics_hit.append(roast_topic)
        
        profile.roast_history.last_roasted = datetime.utcnow().isoformat()
    
    def save_all_profiles(self) -> int:
        """Save all in-memory profiles to disk.
        
        Returns:
            int: Number of profiles saved
        """
        saved_count = 0
        for user_id in self.profiles.keys():
            if self.save_profile(user_id):
                saved_count += 1
        
        logger.info(f"Saved {saved_count} profiles to disk")
        return saved_count
    
    def get_profile_size_kb(self, user_id: int) -> float:
        """Get profile file size in KB.
        
        Args:
            user_id: User ID
            
        Returns:
            float: Size in KB
        """
        profile_path = self._get_user_profile_path(user_id)
        if os.path.exists(profile_path):
            size_bytes = os.path.getsize(profile_path)
            return size_bytes / 1024
        return 0.0


# Global profile manager instance
profile_manager = ProfileManager()
