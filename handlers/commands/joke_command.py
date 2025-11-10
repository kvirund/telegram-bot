"""Joke command handler for the Telegram bot."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from ai_providers import create_provider
from utils.context_extractor import message_history
from .base import Command


logger = logging.getLogger(__name__)


class JokeCommand(Command):
    """Joke command that generates jokes from context or about topics.

    The command can be used in two ways:
    - /joke - generates a random Russian joke (in groups: using context, in private: random)
    - /joke <context> - generates a Russian joke based on the provided context
    """

    def __init__(self):
        super().__init__(
            name="joke",
            description="Generate joke from context or about a topic",
            admin_only=False
        )

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /joke command.

        The command can be used in two ways:
        - /joke - generates a random Russian joke (in groups: using context, in private: random)
        - /joke <context> - generates a Russian joke based on the provided context

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        if not update.message:
            return

        message = update.message
        chat_id = message.chat_id
        user_id = message.from_user.id if message.from_user else 0
        username = message.from_user.username if message.from_user else "Unknown"
        is_private = message.chat.type == "private"

        logger.info(f"User {user_id} (@{username}) requested /joke command in chat {chat_id}")

        try:
            # Get AI provider
            config = get_config()
            ai_provider = create_provider(
                provider_type=config.ai_provider,
                api_key=config.api_key,
                model=config.model_name,
                base_url=config.base_url
            )

            # Parse command and extract context if provided
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)

            if len(parts) > 1:
                # User provided explicit context: /joke <context>
                user_context = parts[1].strip()
                logger.info(f"Generating joke with user-provided context in chat {chat_id}")
                joke = await ai_provider.generate_joke(context=user_context, is_contextual=False)
            elif not is_private:
                # In groups, use conversation history
                logger.info(f"Generating joke with conversation context in chat {chat_id}")
                conversation_context = message_history.get_context(
                    chat_id=chat_id,
                    count=config.context_messages_count
                )

                if conversation_context:
                    joke = await ai_provider.generate_joke(context=conversation_context, is_contextual=True)
                else:
                    # No context available, generate random joke
                    logger.info(f"No context available, generating random joke in chat {chat_id}")
                    joke = await ai_provider.generate_joke(context=None, is_contextual=False)
            else:
                # In private chats without context, generate random joke
                logger.info(f"Generating random joke in private chat {chat_id}")
                joke = await ai_provider.generate_joke(context=None, is_contextual=False)

            # Send the joke
            await send_joke_response(message, joke)

        except Exception as e:
            logger.error(f"Error handling /joke command: {e}")
            await message.reply_text(
                "Извините, произошла ошибка при генерации анекдота. Попробуйте позже.",
                reply_to_message_id=message.message_id
            )


async def send_joke_response(message, joke: str) -> None:
    """Send a joke as a reply to the message.

    Args:
        message: Telegram message to reply to
        joke: The joke text to send
    """
    try:
        await message.reply_text(
            joke,
            reply_to_message_id=message.message_id
        )
        logger.info(f"Successfully sent joke to chat {message.chat_id}")
    except Exception as e:
        logger.error(f"Failed to send joke: {e}")
        raise


# Create and register the command instance
joke_command = JokeCommand()


# Legacy functions for backward compatibility during transition
async def handle_joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE, is_private: bool = False) -> None:
    """Legacy function for backward compatibility."""
    await joke_command.execute(update, context)
