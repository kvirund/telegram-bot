"""Abstract base class for AI providers."""
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """Abstract base class for AI joke generation providers."""

    @abstractmethod
    async def generate_joke(
        self, context: str = None, is_contextual: bool = False
    ) -> str:
        """Generate a Russian joke.

        Args:
            context: Optional context for the joke (conversation history
                or user-provided context)
            is_contextual: Whether this is a contextual joke based on
                conversation

        Returns:
            str: Generated Russian joke

        Raises:
            Exception: If joke generation fails
        """
        pass

    @abstractmethod
    async def free_request(
        self, user_message: str, system_message: Optional[str] = None
    ) -> str:
        """Make a free-form request to the AI model.

        Args:
            user_message: The user's message/prompt
            system_message: Optional system message to set context/behavior

        Returns:
            str: AI model's response

        Raises:
            Exception: If request fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider.

        Returns:
            str: Provider name (e.g., "Groq", "OpenRouter")
        """
        pass

    @abstractmethod
    async def generate_autonomous_comment(
        self, prompt: str, language: str = "en"
    ) -> str:
        """Generate an autonomous comment for the chat.

        Args:
            prompt: The prompt containing conversation context and
                instructions
            language: Preferred language for the response

        Returns:
            str: AI model's response (should be JSON formatted)

        Raises:
            Exception: If generation fails
        """
        pass
