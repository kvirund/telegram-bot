"""Help command handler for the Telegram bot."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.profile_manager import profile_manager
from .base import Command
from .registry import command_registry


logger = logging.getLogger(__name__)


class HelpCommand(Command):
    """Help command that shows available commands based on user privilege level.

    Supports language detection and manual language selection:
    - /help - Auto-detect language from user profile
    - /help ru - Force Russian
    - /help en - Force English
    """

    def __init__(self):
        super().__init__(name="help", description="Show help message with available commands", admin_only=False)

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - show available commands based on user privilege level.

        Supports language detection and manual language selection:
        - /help - Auto-detect language from user profile
        - /help ru - Force Russian
        - /help en - Force English

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name or "User"

        logger.info(f"User {user_id} ({username}) requested /help command")

        # Parse command for language parameter
        command_text = message.text.strip()
        parts = command_text.split(maxsplit=1)
        forced_language = parts[1].lower() if len(parts) > 1 else None

        # Determine language
        if forced_language in ["ru", "russian", "русский"]:
            language = "ru"
        elif forced_language in ["en", "english", "английский"]:
            language = "en"
        else:
            # Auto-detect from user profile
            user_profile = profile_manager.load_profile(user_id)
            if user_profile and user_profile.language_preference:
                language = "ru" if user_profile.language_preference == "ru" else "en"
            else:
                # Default to Russian for Russian-speaking chats
                language = "ru"

        # Get config for user permission check
        config = get_config()

        # Generate help text using the registry
        help_text = command_registry.generate_help_text(user_id, config, language)

        await message.reply_text(help_text, reply_to_message_id=message.message_id, parse_mode="HTML")
        logger.info(f"Sent {language} help to user {user_id} ({username})")


# Create and register the command instance
help_command = HelpCommand()


# Legacy function for backward compatibility during transition
async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await help_command.execute(update, context)
