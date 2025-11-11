"""Handle /comment command to force an autonomous comment."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.autonomous_commenter import AutonomousCommenter
from utils.profile_manager import profile_manager
from .base import Command

logger = logging.getLogger(__name__)


class CommentCommand(Command):
    """Comment command for forcing autonomous comments.

    This forces the bot to generate and post an autonomous comment immediately
    in a specified chat, using current context. Only authorized admin users can
    execute this command, and it must be used in private chat.

    Usage: /comment <chat_id>
    """

    def __init__(self):
        super().__init__(name="comment", description="Force comment in chat (admin only)", admin_only=True, description_ru="Принудительно прокомментировать в чате (только админ)")

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /comment command to force an autonomous comment.

        This forces the bot to generate and post an autonomous comment immediately
        in a specified chat, using current context. Only authorized admin users can
        execute this command, and it must be used in private chat.

        Usage: /comment <chat_id>

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        config = get_config()
        autonomous_commenter = AutonomousCommenter(config, profile_manager)

        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"

        logger.info(f"User {user_id} (@{username}) requested /comment command")

        # Check if command is sent in private chat only
        if message.chat.type != "private":
            logger.warning(f"/comment command attempted in group chat {message.chat_id} by user {user_id}")
            await message.reply_text(
                "❌ Эта команда может использоваться только в приватном чате с ботом.", reply_to_message_id=message.message_id
            )
            return

        # Check if user is authorized admin
        if user_id not in config.admin_user_ids:
            logger.warning(f"Unauthorized /comment attempt by user {user_id} (@{message.from_user.username})")
            await message.reply_text(
                "❌ Нет доступа. Только администраторы бота могут использовать эту команду.", reply_to_message_id=message.message_id
            )
            return

        try:
            # Parse command to get chat ID
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=1)

            if len(parts) < 2:
                await message.reply_text(
                    "Использование: /comment <chat_id>\n\n"
                    "Принудительно заставляет бота сгенерировать автономный комментарий в указанном чате.\n"
                    "Пример: /comment -1001234567890",
                    reply_to_message_id=message.message_id,
                )
                return

            try:
                target_chat_id = int(parts[1].strip())
            except ValueError:
                await message.reply_text(
                    "❌ Неверный ID чата. Пожалуйста, укажите числовой ID чата.\n" "Пример: /comment -1001234567890",
                    reply_to_message_id=message.message_id,
                )
                return

            logger.info(f"Forcing autonomous comment in chat {target_chat_id} by admin {user_id}")

            # Generate comment for target chat
            bot_user_id = context.bot.id
            comment = await autonomous_commenter.generate_comment(
                chat_id=target_chat_id, ai_provider=None, bot_user_id=bot_user_id  # Will be set by the caller
            )

            if not comment:
                await message.reply_text(
                    f"❌ Не удалось сгенерировать комментарий для чата {target_chat_id}.\n"
                    "Возможные причины:\n"
                    "- Нет истории сообщений для этого чата\n"
                    "- Чат не найден в истории\n"
                    "- Сбой генерации ИИ",
                    reply_to_message_id=message.message_id,
                )
                return

            # Send comment to target chat
            try:
                if comment.reply_to_message_id:
                    await context.bot.send_message(
                        chat_id=target_chat_id, text=comment.text, reply_to_message_id=comment.reply_to_message_id
                    )
                    await message.reply_text(
                        f"✅ Комментарий отправлен в чат {target_chat_id} в ответ на сообщение {comment.reply_to_message_id}",
                        reply_to_message_id=message.message_id,
                    )
                else:
                    await context.bot.send_message(chat_id=target_chat_id, text=comment.text)
                    await message.reply_text(
                        f"✅ Отдельный комментарий отправлен в чат {target_chat_id}", reply_to_message_id=message.message_id
                    )

                # Mark that we commented
                autonomous_commenter.mark_commented(target_chat_id)

                # Record roast if applicable
                if comment.target_user_id and comment.comment_type == "roast":
                    profile_manager.record_roast(
                        target_user_id=comment.target_user_id, roast_topic=comment.comment_type, success=True
                    )

                logger.info(f"Successfully sent forced comment to chat {target_chat_id}")

            except Exception as e:
                logger.error(f"Failed to send comment to chat {target_chat_id}: {e}")
                await message.reply_text(
                    f"❌ Не удалось отправить комментарий в чат {target_chat_id}: {str(e)}\n"
                    "Возможно, бот не имеет доступа к этому чату.",
                    reply_to_message_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error in /comment command: {e}")
            await message.reply_text(f"❌ Ошибка: {str(e)}", reply_to_message_id=message.message_id)


# Create and register the command instance
comment_command = CommentCommand()


# Legacy function for backward compatibility during transition
async def handle_comment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await comment_command.execute(update, context)
