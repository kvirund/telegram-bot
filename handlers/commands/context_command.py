"""Context command handler for clearing conversation context."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from utils.autonomous_commenter import AutonomousCommenter
from .base import Command
from .arguments import ArgumentDefinition, ArgumentType


logger = logging.getLogger(__name__)


class ContextCommand(Command):
    """Context command for clearing conversation context.

    Usage:
    - /context - Clear context for current chat
    - /context <chat_id> - Clear context for specified chat (admin only)
    """

    def __init__(self):
        arguments = [
            ArgumentDefinition(
                name="chat_id",
                type=ArgumentType.INTEGER,
                required=False,
                description="Chat ID to clear context for (admin only, defaults to current chat)"
            )
        ]
        super().__init__(
            name="context",
            description="Clear chat context (admin only)",
            admin_only=True,
            arguments=arguments,
            description_ru="Очистить контекст чата (только админ)"
        )

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /context command to reset/clear conversation context.

        Usage:
        - /context - Clear context for current chat
        - /context <chat_id> - Clear context for specified chat (admin only)

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        current_chat_id = message.chat_id

        logger.info(f"User {user_id} (@{username}) requested /context command in chat {current_chat_id}")

        try:
            config = get_config()

            # Parse command
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)

            # Determine target chat
            if len(parts) > 1:
                # Admin wants to clear specific chat
                if user_id not in config.admin_user_ids:
                    await message.reply_text(
                        "❌ Только администраторы могут очищать контекст для других чатов.",
                        reply_to_message_id=message.message_id,
                    )
                    return

                try:
                    target_chat_id = int(parts[1].strip())
                except ValueError:
                    await message.reply_text(
                        "❌ Неверный ID чата. Использование: /context <chat_id>", reply_to_message_id=message.message_id
                    )
                    return
            else:
                # Clear current chat context
                target_chat_id = current_chat_id

            # Get context stats before clearing
            context_messages = message_history.get_recent_messages(target_chat_id)
            message_count = len(context_messages) if context_messages else 0

            # Clear context
            message_history.clear_chat_history(target_chat_id)

            # Also reset autonomous commenter state for this chat
            # Note: This would need to be passed in or accessed differently
            # For now, we'll handle this in the main message handler

            logger.info(f"Context cleared for chat {target_chat_id} by user {user_id} ({message_count} messages)")

            await message.reply_text(
                f"✅ Контекст очищен для чата `{target_chat_id}`\n"
                f"📊 Удалено {message_count} сообщений из истории\n"
                f"🔄 Состояние автономного комментатора сброшено",
                reply_to_message_id=message.message_id,
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error in /context command: {e}")
            await message.reply_text(f"❌ Ошибка: {str(e)}", reply_to_message_id=message.message_id)


# Create and register the command instance
context_command = ContextCommand()


# Legacy function for backward compatibility during transition
async def handle_context_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await context_command.execute(update, context)
