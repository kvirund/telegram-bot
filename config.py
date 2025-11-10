"""Configuration management for the Telegram AI Assistant."""
import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class BotSettings:
    """Bot settings."""
    telegram_token: str
    bot_username: str
    admin_user_ids: List[int] = field(default_factory=list)


@dataclass
class GroqSettings:
    """Groq provider settings."""
    api_key: str = ""
    model: str = "llama-3.2-90b-text-preview"


@dataclass
class OpenRouterSettings:
    """OpenRouter provider settings."""
    api_key: str = ""
    model: str = "openai/gpt-4o-mini"


@dataclass
class LocalSettings:
    """Local API provider settings."""
    api_key: str = "dummy"
    api_url: str = "http://localhost:11434/v1"
    model: str = "llama2-uncensored"


@dataclass
class AISettings:
    """AI provider configuration."""
    provider: str = "local"
    context_messages_count: int = 10
    max_retries: int = 3
    groq: GroqSettings = field(default_factory=GroqSettings)
    openrouter: OpenRouterSettings = field(default_factory=OpenRouterSettings)
    local: LocalSettings = field(default_factory=LocalSettings)


@dataclass
class AutonomousCommentingConfig:
    """Autonomous commenting configuration."""
    enabled: bool = True
    min_messages_between_comments: int = 8
    max_messages_between_comments: int = 20
    comment_probability: float = 0.3
    min_time_between_comments_seconds: int = 120
    use_intelligent_decision: bool = True
    use_ai_decision: bool = True
    prefer_replies: bool = True
    standalone_probability: float = 0.3
    roasting_enabled: bool = True
    roasting_aggression: float = 0.7
    target_weaknesses_probability: float = 0.6
    avoid_sensitive_topics: bool = False
    learn_from_reactions: bool = True


@dataclass
class UserProfilingConfig:
    """User profiling configuration."""
    enabled: bool = True
    profile_directory: str = "profiles"
    max_profile_size_kb: int = 100
    enrichment_interval_messages: int = 10
    track_topics: bool = True
    track_speaking_style: bool = True
    track_interests: bool = True
    track_relationships: bool = True
    track_humor_type: bool = True
    track_weaknesses: bool = True
    track_mistakes: bool = True
    track_embarrassments: bool = True
    track_contradictions: bool = True
    auto_save_interval_seconds: int = 300
    cross_chat_profiling: bool = True


@dataclass
class ConversationMonitoringConfig:
    """Conversation monitoring configuration."""
    context_window_size: int = 15
    language_detection: bool = True
    uncensored_mode: bool = True


@dataclass
class ReactionSystemConfig:
    """Reaction system configuration."""
    enabled: bool = True
    track_reactions: bool = True
    add_own_reactions: bool = True
    reaction_probability: float = 0.15
    min_time_between_reactions_seconds: int = 60
    reaction_types: List[str] = field(default_factory=lambda: ["👍", "😂", "🔥", "😱", "🤔", "👀", "💯", "🎯"])


@dataclass
class SystemPromptsConfig:
    """System prompts configuration."""
    joke_generation: str = "You are a witty AI assistant that can generate jokes and humorous content."
    conversation: str = "You are a helpful, witty AI assistant."
    autonomous_comment: str = "You are an observational bot."
    ai_decision: str = "You are a conversation analyst. Respond with YES or NO."
    mention_response: str = "You are a straightforward, sarcastic bot. Respond directly to mentions."


@dataclass
class YamlConfig:
    """YAML configuration wrapper."""
    bot: BotSettings = field(default_factory=lambda: BotSettings(telegram_token="", bot_username=""))
    ai: AISettings = field(default_factory=AISettings)
    autonomous_commenting: AutonomousCommentingConfig = field(default_factory=AutonomousCommentingConfig)
    user_profiling: UserProfilingConfig = field(default_factory=UserProfilingConfig)
    conversation_monitoring: ConversationMonitoringConfig = field(default_factory=ConversationMonitoringConfig)
    reaction_system: ReactionSystemConfig = field(default_factory=ReactionSystemConfig)
    system_prompts: SystemPromptsConfig = field(default_factory=SystemPromptsConfig)
    excluded_chats: List[int] = field(default_factory=list)


@dataclass
class BotConfig:
    """Bot configuration dataclass."""
    telegram_token: str
    bot_username: str
    ai_provider: str
    api_key: str
    model_name: str
    base_url: str = None
    context_messages_count: int = 10
    max_retries: int = 3
    admin_user_ids: List[int] = field(default_factory=list)
    yaml_config: YamlConfig = field(default_factory=YamlConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.bot_username:
            raise ValueError("BOT_USERNAME is required")
        if self.ai_provider not in ["groq", "openrouter", "local"]:
            raise ValueError("AI_PROVIDER must be 'groq', 'openrouter', or 'local'")
        if not self.api_key:
            raise ValueError(f"API key for {self.ai_provider} is required")
        if not self.model_name:
            raise ValueError("MODEL_NAME is required")
        if self.context_messages_count < 1:
            raise ValueError("CONTEXT_MESSAGES_COUNT must be at least 1")
        if self.max_retries < 1:
            raise ValueError("MAX_RETRIES must be at least 1")


# Singleton configuration instance
_config: Optional[BotConfig] = None


def load_yaml_config() -> YamlConfig:
    """Load YAML configuration from config.yaml.

    Returns:
        YamlConfig: Loaded YAML configuration with defaults
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    # Use defaults if file doesn't exist (for testing/CI)
    if not os.path.exists(config_path):
        import logging
        logging.warning(f"config.yaml not found at {config_path}, using defaults")
        return YamlConfig()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f) or {}
        
        # Parse bot section
        bot_data = yaml_data.get('bot', {})
        bot = BotSettings(
            telegram_token=bot_data.get('telegram_token', ''),
            bot_username=bot_data.get('bot_username', ''),
            admin_user_ids=bot_data.get('admin_user_ids', [])
        )
        
        # Parse AI section
        ai_data = yaml_data.get('ai', {})
        groq_data = ai_data.get('groq', {})
        openrouter_data = ai_data.get('openrouter', {})
        local_data = ai_data.get('local', {})
        
        ai = AISettings(
            provider=ai_data.get('provider', 'local'),
            context_messages_count=ai_data.get('context_messages_count', 10),
            max_retries=ai_data.get('max_retries', 3),
            groq=GroqSettings(
                api_key=groq_data.get('api_key', ''),
                model=groq_data.get('model', 'llama-3.2-90b-text-preview')
            ),
            openrouter=OpenRouterSettings(
                api_key=openrouter_data.get('api_key', ''),
                model=openrouter_data.get('model', 'openai/gpt-4o-mini')
            ),
            local=LocalSettings(
                api_key=local_data.get('api_key', 'dummy'),
                api_url=local_data.get('api_url', 'http://localhost:11434/v1'),
                model=local_data.get('model', 'llama2-uncensored')
            )
        )
        
        # Parse autonomous_commenting section
        ac_data = yaml_data.get('autonomous_commenting', {})
        autonomous_commenting = AutonomousCommentingConfig(
            enabled=ac_data.get('enabled', True),
            min_messages_between_comments=ac_data.get('min_messages_between_comments', 8),
            max_messages_between_comments=ac_data.get('max_messages_between_comments', 20),
            comment_probability=ac_data.get('comment_probability', 0.3),
            min_time_between_comments_seconds=ac_data.get('min_time_between_comments_seconds', 120),
            use_intelligent_decision=ac_data.get('use_intelligent_decision', True),
            use_ai_decision=ac_data.get('use_ai_decision', True),
            prefer_replies=ac_data.get('prefer_replies', True),
            standalone_probability=ac_data.get('standalone_probability', 0.3),
            roasting_enabled=ac_data.get('roasting_enabled', True),
            roasting_aggression=ac_data.get('roasting_aggression', 0.7),
            target_weaknesses_probability=ac_data.get('target_weaknesses_probability', 0.6),
            avoid_sensitive_topics=ac_data.get('avoid_sensitive_topics', False),
            learn_from_reactions=ac_data.get('learn_from_reactions', True)
        )
        
        # Parse user_profiling section
        up_data = yaml_data.get('user_profiling', {})
        user_profiling = UserProfilingConfig(
            enabled=up_data.get('enabled', True),
            profile_directory=up_data.get('profile_directory', 'profiles'),
            max_profile_size_kb=up_data.get('max_profile_size_kb', 100),
            enrichment_interval_messages=up_data.get('enrichment_interval_messages', 10),
            track_topics=up_data.get('track_topics', True),
            track_speaking_style=up_data.get('track_speaking_style', True),
            track_interests=up_data.get('track_interests', True),
            track_relationships=up_data.get('track_relationships', True),
            track_humor_type=up_data.get('track_humor_type', True),
            track_weaknesses=up_data.get('track_weaknesses', True),
            track_mistakes=up_data.get('track_mistakes', True),
            track_embarrassments=up_data.get('track_embarrassments', True),
            track_contradictions=up_data.get('track_contradictions', True),
            auto_save_interval_seconds=up_data.get('auto_save_interval_seconds', 300),
            cross_chat_profiling=up_data.get('cross_chat_profiling', True)
        )
        
        # Parse conversation_monitoring section
        cm_data = yaml_data.get('conversation_monitoring', {})
        conversation_monitoring = ConversationMonitoringConfig(
            context_window_size=cm_data.get('context_window_size', 15),
            language_detection=cm_data.get('language_detection', True),
            uncensored_mode=cm_data.get('uncensored_mode', True)
        )
        
        # Parse reaction_system section
        rs_data = yaml_data.get('reaction_system', {})
        reaction_system = ReactionSystemConfig(
            enabled=rs_data.get('enabled', True),
            track_reactions=rs_data.get('track_reactions', True),
            add_own_reactions=rs_data.get('add_own_reactions', True),
            reaction_probability=rs_data.get('reaction_probability', 0.15),
            min_time_between_reactions_seconds=rs_data.get('min_time_between_reactions_seconds', 60),
            reaction_types=rs_data.get('reaction_types', ["👍", "😂", "🔥", "😱", "🤔", "👀", "💯", "🎯"])
        )
        
        # Parse system_prompts section
        sp_data = yaml_data.get('system_prompts', {})
        system_prompts = SystemPromptsConfig(
            joke_generation=sp_data.get('joke_generation', "You are a witty AI assistant that can generate jokes and humorous content."),
            conversation=sp_data.get('conversation', "You are a helpful, witty AI assistant."),
            autonomous_comment=sp_data.get('autonomous_comment', "You are an observational bot."),
            ai_decision=sp_data.get('ai_decision', "You are a conversation analyst. Respond with YES or NO."),
            mention_response=sp_data.get('mention_response', "You are a straightforward, sarcastic bot. Respond directly to mentions.")
        )
        
        # Parse excluded_chats
        excluded_chats = yaml_data.get('excluded_chats', [])
        
        return YamlConfig(
            bot=bot,
            ai=ai,
            autonomous_commenting=autonomous_commenting,
            user_profiling=user_profiling,
            conversation_monitoring=conversation_monitoring,
            reaction_system=reaction_system,
            system_prompts=system_prompts,
            excluded_chats=excluded_chats
        )
    except Exception as e:
        import logging
        logging.error(f"Error loading config.yaml: {e}. Using defaults.")
        raise


def load_config() -> BotConfig:
    """Load configuration from config.yaml.
    
    Returns:
        BotConfig: Loaded and validated configuration
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Load YAML configuration
    yaml_config = load_yaml_config()
    
    # Get AI provider settings
    ai_provider = yaml_config.ai.provider.lower()
    
    if ai_provider == "groq":
        api_key = yaml_config.ai.groq.api_key
        model_name = yaml_config.ai.groq.model
        base_url = None
    elif ai_provider == "openrouter":
        api_key = yaml_config.ai.openrouter.api_key
        model_name = yaml_config.ai.openrouter.model
        base_url = None
    elif ai_provider == "local":
        api_key = yaml_config.ai.local.api_key
        model_name = yaml_config.ai.local.model
        base_url = yaml_config.ai.local.api_url
    else:
        raise ValueError(f"Unknown AI_PROVIDER: {ai_provider}")
    
    # Create and validate configuration
    config = BotConfig(
        telegram_token=yaml_config.bot.telegram_token,
        bot_username=yaml_config.bot.bot_username,
        ai_provider=ai_provider,
        api_key=api_key,
        model_name=model_name,
        base_url=base_url,
        context_messages_count=yaml_config.ai.context_messages_count,
        max_retries=yaml_config.ai.max_retries,
        admin_user_ids=yaml_config.bot.admin_user_ids,
        yaml_config=yaml_config
    )
    
    return config


def get_config() -> BotConfig:
    """Get the singleton configuration instance.
    
    Returns:
        BotConfig: The loaded configuration
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> BotConfig:
    """Reload configuration from files.
    
    This forces a reload of config.yaml.
    
    Returns:
        BotConfig: The newly loaded configuration
    """
    global _config
    _config = load_config()
    return _config
