"""AI provider factory module."""
import logging
from .base import AIProvider
from .groq_provider import GroqProvider
from .openrouter_provider import OpenRouterProvider
from .local_provider import LocalProvider


logger = logging.getLogger(__name__)


def create_provider(
    provider_type: str, api_key: str, model: str, base_url: str = None
) -> AIProvider:
    """Factory function to create AI provider instances.

    Args:
        provider_type: Type of provider ("groq", "openrouter", or "local")
        api_key: API key for the provider
        model: Model name to use
        base_url: Base URL for local API (only used for "local" provider)

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
    elif provider_type == "local":
        logger.info(f"Creating Local provider at {base_url}")
        default_url = "http://localhost:8000/v1"
        return LocalProvider(
            api_key=api_key, model=model, base_url=base_url or default_url
        )
    else:
        supported = "'groq', 'openrouter', or 'local'"
        raise ValueError(f"Unsupported provider type: {provider_type}. Must be {supported}")


__all__ = [
    "AIProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "LocalProvider",
    "create_provider",
]
