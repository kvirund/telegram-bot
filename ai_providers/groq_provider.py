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
    
    def get_provider_name(self) -> str:
        """Get the provider name.
        
        Returns:
            str: Provider name
        """
        return "Groq"
