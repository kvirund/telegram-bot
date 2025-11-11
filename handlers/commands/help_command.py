"""Interactive help command handler for the Telegram bot."""

import logging
from typing import List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from config import get_config
from utils.profile_manager import profile_manager
from .base import Command
from .registry import command_registry


logger = logging.getLogger(__name__)


class HelpCommand(Command):
    """Interactive help command that shows available commands with inline keyboards.

    Features:
    - Interactive command browsing with inline keyboards
    - Detailed help for individual commands
    - Command categorization (public/admin)
    - Language switching
    - Argument information display
    """

    def __init__(self):
        super().__init__(name="help", description="Show interactive help with available commands", admin_only=False, description_ru="Показать интерактивную справку с доступными командами")

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - show interactive help menu.

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
        language = self._determine_language(user_id, forced_language)

        # Show main help menu
        await self._show_main_menu(message, user_id, language)

    def _determine_language(self, user_id: int, forced_language: str = None) -> str:
        """Determine the language to use for help text."""
        if forced_language in ["ru", "russian", "русский"]:
            return "ru"
        elif forced_language in ["en", "english", "английский"]:
            return "en"
        else:
            # Auto-detect from user profile
            user_profile = profile_manager.load_profile(user_id)
            if user_profile and user_profile.language_preference:
                return "ru" if user_profile.language_preference == "ru" else "en"
            else:
                # Default to Russian for Russian-speaking chats
                return "ru"

    async def _show_main_menu(self, message, user_id: int, language: str):
        """Show the main interactive help menu."""
        config = get_config()
        available_commands = command_registry.get_user_commands(user_id, config)

        public_commands = [cmd for cmd in available_commands if not cmd.admin_only]
        admin_commands = [cmd for cmd in available_commands if cmd.admin_only]

        # Create keyboard
        keyboard = []

        if public_commands:
            keyboard.append([InlineKeyboardButton(
                self._get_text("📋 Public Commands", "📋 Публичные команды", language),
                callback_data=f"help_public_{language}"
            )])

        if admin_commands:
            keyboard.append([InlineKeyboardButton(
                self._get_text("🔐 Admin Commands", "🔐 Команды администратора", language),
                callback_data=f"help_admin_{language}"
            )])

        # Language switch buttons
        lang_buttons = []
        if language == "en":
            lang_buttons.append(InlineKeyboardButton("🇷🇺 Русский", callback_data=f"help_lang_ru_{user_id}"))
        else:
            lang_buttons.append(InlineKeyboardButton("🇺🇸 English", callback_data=f"help_lang_en_{user_id}"))

        keyboard.append(lang_buttons)

        # Main text
        if language == "ru":
            text = "🤖 <b>Справка по Telegram Joke Bot</b>\n\n"
            text += f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n\n"
            text += "Выберите категорию команд для просмотра подробной информации:"
        else:
            text = "🤖 <b>Telegram Joke Bot Help</b>\n\n"
            text += f"🆔 <b>Your ID:</b> <code>{user_id}</code>\n\n"
            text += "Choose a command category to view detailed information:"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        if not query or not query.data.startswith("help_"):
            return

        await query.answer()

        data = query.data
        user_id = query.from_user.id

        # Parse callback data - handle both old underscore format and new pipe format
        if "|" in data:
            # New format: help_cmd|command_name|language
            parts = data.split("|")
            if len(parts) < 3:
                return
            action = parts[0].split("_")[1]  # Extract action from "help_cmd"
            if action == "cmd":
                command_name = parts[1]
                language = parts[2]
                await self._show_command_detail(query, command_name, language)
            return

        # Old format (underscore-based) for backward compatibility
        parts = data.split("_")
        if len(parts) < 2:
            return

        action = parts[1]

        if action == "public":
            language = parts[2] if len(parts) > 2 else "en"
            await self._show_command_list(query, user_id, "public", language)
        elif action == "admin":
            language = parts[2] if len(parts) > 2 else "en"
            await self._show_command_list(query, user_id, "admin", language)
        elif action == "cmd":
            command_name = parts[2]
            language = parts[3] if len(parts) > 3 else "en"
            await self._show_command_detail(query, command_name, language)
        elif action == "back":
            menu_type = parts[2]
            language = parts[3] if len(parts) > 3 else "en"
            if menu_type == "main":
                await self._show_main_menu_from_callback(query, user_id, language)
            else:
                await self._show_command_list(query, user_id, menu_type, language)
        elif action == "lang":
            new_lang = parts[2]
            target_user_id = int(parts[3]) if len(parts) > 3 else user_id
            if target_user_id == user_id:  # Only allow users to change their own language
                await self._show_main_menu_from_callback(query, user_id, new_lang)

    async def _show_command_list(self, query, user_id: int, category: str, language: str):
        """Show list of commands in a category."""
        config = get_config()
        available_commands = command_registry.get_user_commands(user_id, config)

        if category == "public":
            commands = [cmd for cmd in available_commands if not cmd.admin_only]
            title = self._get_text("📋 Public Commands", "📋 Публичные команды", language)
        else:
            commands = [cmd for cmd in available_commands if cmd.admin_only]
            title = self._get_text("🔐 Admin Commands", "🔐 Команды администратора", language)

        # Create keyboard with command buttons
        keyboard = []
        for cmd in sorted(commands, key=lambda x: x.name):
            # Button text should be plain text (no HTML parsing)
            # Use a separator that's not in command names (pipe |) to avoid conflicts with underscores
            keyboard.append([InlineKeyboardButton(
                f"{cmd.command_name} - {cmd.description}",
                callback_data=f"help_cmd|{cmd.name}|{language}"
            )])

        # Back button
        keyboard.append([InlineKeyboardButton(
            self._get_text("⬅️ Back", "⬅️ Назад", language),
            callback_data=f"help_back_main_{language}"
        )])

        text = f"<b>{title}</b>\n\n"
        text += self._get_text(
            "Click on a command to see detailed help:",
            "Нажмите на команду для подробной справки:",
            language
        )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

    async def _show_command_detail(self, query, command_name: str, language: str):
        """Show detailed help for a specific command."""
        command = command_registry.get_command(command_name)
        if not command:
            await query.edit_message_text("Command not found.", parse_mode="HTML")
            return

        # Get detailed help text
        help_text = command.get_help_text(language)

        # Create keyboard with back button
        keyboard = [[InlineKeyboardButton(
            self._get_text("⬅️ Back to list", "⬅️ К списку", language),
            callback_data=f"help_back_{'admin' if command.admin_only else 'public'}_{language}"
        )]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Format the help text nicely
        formatted_text = f"<b>Command Details</b>\n\n{help_text}"

        await query.edit_message_text(formatted_text, reply_markup=reply_markup, parse_mode="HTML")

    async def _show_main_menu_from_callback(self, query, user_id: int, language: str):
        """Show main menu from callback query."""
        config = get_config()
        available_commands = command_registry.get_user_commands(user_id, config)

        public_commands = [cmd for cmd in available_commands if not cmd.admin_only]
        admin_commands = [cmd for cmd in available_commands if cmd.admin_only]

        # Create keyboard
        keyboard = []

        if public_commands:
            keyboard.append([InlineKeyboardButton(
                self._get_text("📋 Public Commands", "📋 Публичные команды", language),
                callback_data=f"help_public_{language}"
            )])

        if admin_commands:
            keyboard.append([InlineKeyboardButton(
                self._get_text("🔐 Admin Commands", "🔐 Команды администратора", language),
                callback_data=f"help_admin_{language}"
            )])

        # Language switch buttons
        lang_buttons = []
        if language == "en":
            lang_buttons.append(InlineKeyboardButton("🇷🇺 Русский", callback_data=f"help_lang_ru_{user_id}"))
        else:
            lang_buttons.append(InlineKeyboardButton("🇺🇸 English", callback_data=f"help_lang_en_{user_id}"))

        keyboard.append(lang_buttons)

        # Main text
        if language == "ru":
            text = "🤖 <b>Справка по Telegram Joke Bot</b>\n\n"
            text += f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n\n"
            text += "Выберите категорию команд для просмотра подробной информации:"
        else:
            text = "🤖 <b>Telegram Joke Bot Help</b>\n\n"
            text += f"🆔 <b>Your ID:</b> <code>{user_id}</code>\n\n"
            text += "Choose a command category to view detailed information:"

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")

    def _get_text(self, en_text: str, ru_text: str, language: str) -> str:
        """Get text in the appropriate language."""
        return ru_text if language == "ru" else en_text


# Create and register the command instance
help_command = HelpCommand()


# Callback query handler for interactive help
async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for the help command."""
    await help_command.handle_callback(update, context)


# Legacy function for backward compatibility during transition
async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await help_command.execute(update, context)
