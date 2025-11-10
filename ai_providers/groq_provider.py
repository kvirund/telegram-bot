"""Groq AI provider implementation."""
import logging
from typing import List, Dict
from groq import Groq
from .base import AIProvider


logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq AI provider for joke generation."""

    def __init__(self, api_key: str, model: str = "llama-3.2-90b-text-preview"):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
        self.client = Groq(api_key=api_key)
        logger.info(f"Initialized Groq provider with model: {model}")

    def _build_prompt(self, context: str = None, is_contextual: bool = False) -> List[Dict[str, str]]:
        """Build the prompt messages for the API.

        Args:
            context: Optional context for the joke
            is_contextual: Whether this is a contextual joke

        Returns:
            List of message dictionaries
        """
        system_message = {
            "role": "system",
            "content": "Ты профессиональный комик, который рассказывает смешные анекдоты на русском языке. "
                      "Твои анекдоты должны быть остроумными, уместными и веселыми. "
                      "Отвечай ТОЛЬКО анекдотом, без дополнительных комментариев или объяснений."
        }

        if is_contextual and context:
            user_message = {
                "role": "user",
                "content": f"Расскажи смешной анекдот на русском языке, связанный с этим контекстом:\n\n{context}\n\n"
                          f"Анекдот должен быть уместным и относиться к теме разговора."
            }
        elif context:
            # User provided explicit context in /joke command
            user_message = {
                "role": "user",
                "content": f"Расскажи смешной анекдот на русском языке на тему: {context}"
            }
        else:
            user_message = {
                "role": "user",
                "content": "Расскажи смешной анекдот на русском языке."
            }

        return [system_message, user_message]

    async def generate_joke(self, context: str = None, is_contextual: bool = False) -> str:
        """Generate a Russian joke using Groq.

        Args:
            context: Optional context for the joke
            is_contextual: Whether this is a contextual joke

        Returns:
            str: Generated Russian joke

        Raises:
            Exception: If joke generation fails
        """
        try:
            messages = self._build_prompt(context, is_contextual)

            logger.info(f"Generating joke with Groq (contextual={is_contextual})")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9,  # Higher temperature for more creative jokes
                max_tokens=500,
                top_p=1.0
            )

            joke = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated joke ({len(joke)} chars)")

            return joke

        except Exception as e:
            logger.error(f"Failed to generate joke with Groq: {e}")
            raise Exception(f"Groq API error: {str(e)}")

    async def free_request(self, user_message: str, system_message: str = None) -> str:
        """Make a free-form request to the AI model.

        Args:
            user_message: The user's message/prompt
            system_message: Optional system message to set context/behavior

        Returns:
            str: AI model's response

        Raises:
            Exception: If request fails
        """
        try:
            messages = []

            if system_message:
                messages.append({
                    "role": "system",
                    "content": system_message
                })

            messages.append({
                "role": "user",
                "content": user_message
            })

            logger.info(f"Making free request to Groq")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                top_p=1.0
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Successfully received response ({len(result)} chars)")

            return result

        except Exception as e:
            logger.error(f"Failed to make free request with Groq: {e}")
            raise Exception(f"Groq API error: {str(e)}")

    async def generate_autonomous_comment(self, prompt: str, language: str = "en") -> str:
        """Generate an autonomous comment for the chat.

        Args:
            prompt: The prompt containing conversation context and instructions
            language: Preferred language for the response

        Returns:
            str: AI model's response (should be JSON formatted)

        Raises:
            Exception: If generation fails
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that responds in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            logger.info(f"Generating autonomous comment with Groq")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=1000,
                top_p=1.0
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated autonomous comment ({len(result)} chars)")

            return result

        except Exception as e:
            logger.error(f"Failed to generate autonomous comment with Groq: {e}")
            raise Exception(f"Groq API error: {str(e)}")

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            str: Provider name
        """
        return "Groq"
