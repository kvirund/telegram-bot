"""Ask command handler for free-form AI requests."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from ai_providers import create_provider
from .base import Command


logger = logging.getLogger(__name__)


class AskCommand(Command):
    """Ask command for free-form AI requests.

    Usage formats:
    - /ask <user_message> - sends user message only
    - /ask system:<system_message> user:<user_message> - sends both system and user messages
    """

    def __init__(self):
        super().__init__(name="ask", description="Free-form AI request", admin_only=False)

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ask command for free-form requests.

        Usage formats:
        - /ask <user_message> - sends user message only
        - /ask system:<system_message> user:<user_message> - sends both system and user messages

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

        logger.info(f"User {user_id} (@{username}) requested /ask command in chat {chat_id}")

        try:
            # Get AI provider
            config = get_config()
            ai_provider = create_provider(
                provider_type=config.ai_provider,
                api_key=config.api_key,
                model=config.model_name,
                base_url=config.base_url,
            )

            # Parse command
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)

            if len(parts) < 2:
                await message.reply_text(
                    "Использование:\n"
                    "/ask <ваш запрос> - простой запрос\n"
                    "/ask system:<системное сообщение> user:<запрос пользователя> - с системным промптом",
                    reply_to_message_id=message.message_id,
                )
                return

            request_text = parts[1].strip()
            system_message = None
            user_message = None

            # Check if using system/user format
            if "system:" in request_text and "user:" in request_text:
                # Extract system and user messages
                system_start = request_text.find("system:") + 7
                user_start = request_text.find("user:")

                if system_start < user_start:
                    system_message = request_text[system_start:user_start].strip()
                    user_message = request_text[user_start + 5 :].strip()
                else:
                    await message.reply_text(
                        "Неверный формат. Используйте: /ask system:<текст> user:<текст>",
                        reply_to_message_id=message.message_id,
                    )
                    return
            else:
                # Simple user message only
                user_message = request_text

            if not user_message:
                await message.reply_text(
                    "Запрос пользователя не может быть пустым", reply_to_message_id=message.message_id
                )
                return

            logger.info(f"Processing free request in chat {chat_id}")

            # Make the request
            response = await ai_provider.free_request(user_message=user_message, system_message=system_message)

            # Send response
            await message.reply_text(response, reply_to_message_id=message.message_id)
            logger.info(f"Successfully sent response to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error handling /ask command: {e}")
            await message.reply_text(
                "Извините, произошла ошибка при обработке запроса. Попробуйте позже.",
                reply_to_message_id=message.message_id,
            )


# Create and register the command instance
ask_command = AskCommand()


# Legacy function for backward compatibility during transition
async def handle_ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await ask_command.execute(update, context)
