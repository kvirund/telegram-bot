"""Configuration management for the Telegram Joke Bot."""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class BotConfig:
    """Bot configuration dataclass."""
    telegram_token: str
    channel_id: str
    bot_username: str
    ai_provider: str
    api_key: str
    model_name: str
    context_messages_count: int = 10
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.channel_id:
            raise ValueError("CHANNEL_ID is required")
        if not self.bot_username:
            raise ValueError("BOT_USERNAME is required")
        if self.ai_provider not in ["groq", "openrouter"]:
            raise ValueError("AI_PROVIDER must be 'groq' or 'openrouter'")
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


def load_config() -> BotConfig:
    """Load configuration from environment variables.
    
    Returns:
        BotConfig: Loaded and validated configuration
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Determine AI provider
    ai_provider = os.getenv("AI_PROVIDER", "groq").lower()
    
    # Get appropriate API key and model based on provider
    if ai_provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        model_name = os.getenv("GROQ_MODEL", "llama-3.2-90b-text-preview")
    elif ai_provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    else:
        raise ValueError(f"Unknown AI_PROVIDER: {ai_provider}")
    
    # Create and validate configuration
    config = BotConfig(
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        channel_id=os.getenv("CHANNEL_ID", ""),
        bot_username=os.getenv("BOT_USERNAME", ""),
        ai_provider=ai_provider,
        api_key=api_key,
        model_name=model_name,
        context_messages_count=int(os.getenv("CONTEXT_MESSAGES_COUNT", "10")),
        max_retries=int(os.getenv("MAX_RETRIES", "3"))
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
