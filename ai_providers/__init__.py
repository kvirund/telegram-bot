"""AI provider factory module."""
import logging
from .base import AIProvider
from .groq_provider import GroqProvider
from .openrouter_provider import OpenRouterProvider


logger = logging.getLogger(__name__)


def create_provider(provider_type: str, api_key: str, model: str) -> AIProvider:
    """Factory function to create AI provider instances.
    
    Args:
        provider_type: Type of provider ("groq" or "openrouter")
        api_key: API key for the provider
        model: Model name to use
        
    Returns:
        AIProvider: Instantiated provider
        
    Raises:
        ValueError: If provider_type is not supported
    """
    provider_type = provider_type.lower()
    
    if provider_type == "groq":
        logger.info("Creating Groq provider")
        return GroqProvider(api_key=api_key, model=model)
    elif provider_type == "openrouter":
        logger.info("Creating OpenRouter provider")
        return OpenRouterProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}. Must be 'groq' or 'openrouter'")


__all__ = ["AIProvider", "GroqProvider", "OpenRouterProvider", "create_provider"]
