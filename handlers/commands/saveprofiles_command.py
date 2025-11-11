"""Handle /saveprofiles command to force save all profiles to disk."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.profile_manager import profile_manager
from .base import Command

logger = logging.getLogger(__name__)


class SaveProfilesCommand(Command):
    """SaveProfiles command for forcing profile save to disk.

    This immediately saves all in-memory profiles to disk without waiting
    for the auto-save interval. Useful for ensuring data persistence.

    Only administrators can use this command.
    """

    def __init__(self):
        super().__init__(name="saveprofiles", description="Force save all profiles (admin only)", admin_only=True, description_ru="Принудительно сохранить все профили (только админ)")

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /saveprofiles command to force save all profiles to disk.

        This immediately saves all in-memory profiles to disk without waiting
        for the auto-save interval. Useful for ensuring data persistence.

        Only administrators can use this command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        config = get_config()

        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"

        logger.info(f"User {user_id} (@{username}) requested /saveprofiles command")

        # Check if command is sent in private chat only
        if message.chat.type != "private":
            logger.warning(f"/saveprofiles command attempted in group chat {message.chat_id} by user {user_id}")
            await message.reply_text(
                "[X] Эта команда может использоваться только в приватном чате с ботом.",
                reply_to_message_id=message.message_id,
            )
            return

        # Check admin privilege
        if user_id not in config.admin_user_ids:
            logger.warning(f"Unauthorized /saveprofiles attempt by user {user_id}")
            await message.reply_text(
                "[X] Только администраторы могут принудительно сохранять профили.", reply_to_message_id=message.message_id
            )
            return

        try:
            # Get profile count before saving
            profile_count = len(profile_manager.profiles)

            if profile_count == 0:
                await message.reply_text("[!] Нет профилей в памяти для сохранения.", reply_to_message_id=message.message_id)
                return

            # Save all profiles
            profile_manager.save_all_profiles()

            logger.info(f"Forced save of {profile_count} profiles by admin {user_id}")

            # Build response with profile summary
            response = f"[OK] Успешно сохранено {profile_count} профилей на диск!\n\n"
            response += "Топ 5 самых активных пользователей:\n"

            # Sort profiles by message count
            sorted_profiles = sorted(profile_manager.profiles.items(), key=lambda x: x[1].message_count, reverse=True)[
                :5
            ]

            for user_id_prof, profile in sorted_profiles:
                response += f"- {profile.first_name} (@{profile.username}): {profile.message_count} messages\n"

            await message.reply_text(response, reply_to_message_id=message.message_id)

        except Exception as e:
            logger.error(f"Error in /saveprofiles command: {e}")
            await message.reply_text(f"[X] Ошибка сохранения профилей: {str(e)}", reply_to_message_id=message.message_id)


# Create and register the command instance
saveprofiles_command = SaveProfilesCommand()


# Legacy function for backward compatibility during transition
async def handle_saveprofiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await saveprofiles_command.execute(update, context)
