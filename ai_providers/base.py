"""Abstract base class for AI providers."""
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract base class for AI joke generation providers."""
    
    @abstractmethod
    async def generate_joke(self, context: str = None, is_contextual: bool = False) -> str:
        """Generate a Russian joke.
        
        Args:
            context: Optional context for the joke (conversation history or user-provided context)
            is_contextual: Whether this is a contextual joke based on conversation
            
        Returns:
            str: Generated Russian joke
            
        Raises:
            Exception: If joke generation fails
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider.
        
        Returns:
            str: Provider name (e.g., "Groq", "OpenRouter")
        """
        pass
