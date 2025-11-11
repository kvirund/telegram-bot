"""Command registry for managing all bot commands."""

import logging
from typing import Dict, List, Optional
from telegram import BotCommand

from .base import Command

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Central registry for all bot commands.

    Manages command registration, lookup, and provides methods for
    generating Telegram bot commands and help text.
    """

    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, Command] = {}
        logger.info("Command registry initialized")

    def register_command(self, command: Command) -> None:
        """Register a command in the registry.

        Args:
            command: Command instance to register
        """
        if command.name in self._commands:
            logger.warning(f"Command '{command.name}' is being overwritten")
        else:
            logger.info(f"Registered command: {command.name}")

        self._commands[command.name] = command

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name.

        Args:
            name: Command name without leading slash

        Returns:
            Command instance or None if not found
        """
        return self._commands.get(name)

    def get_all_commands(self) -> List[Command]:
        """Get all registered commands.

        Returns:
            List of all command instances
        """
        return list(self._commands.values())

    def get_user_commands(self, user_id: int, config) -> List[Command]:
        """Get commands available to a specific user.

        Args:
            user_id: User ID to check permissions for
            config: Bot configuration object

        Returns:
            List of commands the user can execute
        """
        return [cmd for cmd in self._commands.values() if cmd.can_execute(user_id, config)]

    def get_admin_commands(self) -> List[Command]:
        """Get all admin-only commands.

        Returns:
            List of admin-only command instances
        """
        return [cmd for cmd in self._commands.values() if cmd.admin_only]

    def get_public_commands(self) -> List[Command]:
        """Get all public (non-admin) commands.

        Returns:
            List of public command instances
        """
        return [cmd for cmd in self._commands.values() if not cmd.admin_only]

    def get_bot_commands(self, language: str = "en") -> List[BotCommand]:
        """Get Telegram BotCommand objects for all commands.

        Args:
            language: Language for command descriptions ('en' or 'ru')

        Returns:
            List of BotCommand objects for Telegram API
        """
        return [BotCommand(cmd.name, cmd.get_description(language)) for cmd in self._commands.values()]

    def get_command_names(self) -> List[str]:
        """Get list of all command names with leading slashes.

        Returns:
            List of command names like ['/help', '/joke', ...]
        """
        return [f"/{name}" for name in self._commands.keys()]

    def generate_help_text(self, user_id: int, config, language: str = "en") -> str:
        """Generate help text based on available commands.

        Args:
            user_id: User ID to check command permissions
            config: Bot configuration object
            language: Language for help text ('en' or 'ru')

        Returns:
            Formatted help text
        """
        available_commands = self.get_user_commands(user_id, config)

        if language == "ru":
            return self._generate_russian_help(available_commands, user_id, config)
        else:
            return self._generate_english_help(available_commands, user_id, config)

    def _generate_english_help(self, commands: List[Command], user_id: int, config) -> str:
        """Generate English help text."""
        public_commands = [cmd for cmd in commands if not cmd.admin_only]
        admin_commands = [cmd for cmd in commands if cmd.admin_only]

        help_text = "🤖 <b>Telegram Joke Bot Help</b>\n\n"
        help_text += f"🆔 <b>Your ID:</b> <code>{user_id}</code>\n\n"

        # Public commands
        if public_commands:
            help_text += "📋 <b>Available Commands:</b>\n"
            for cmd in sorted(public_commands, key=lambda x: x.name):
                help_text += f"• {cmd.get_help_text('en')}\n"
            help_text += "\n"

        # Admin commands
        if admin_commands:
            help_text += "🔐 <b>Admin Commands:</b>\n"
            for cmd in sorted(admin_commands, key=lambda x: x.name):
                help_text += f"• {cmd.get_help_text('en')}\n"
            help_text += "\n"

        help_text += "ℹ️ <b>Features:</b>\n"
        help_text += "• Context-aware responses\n"
        help_text += "• AI-powered autonomous comments\n"
        help_text += "• Multi-language support\n"

        return help_text

    def _generate_russian_help(self, commands: List[Command], user_id: int, config) -> str:
        """Generate Russian help text."""
        public_commands = [cmd for cmd in commands if not cmd.admin_only]
        admin_commands = [cmd for cmd in commands if cmd.admin_only]

        help_text = "🤖 <b>Помощь по Telegram Joke Bot</b>\n\n"
        help_text += f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n\n"

        # Public commands
        if public_commands:
            help_text += "📋 <b>Доступные команды:</b>\n"
            for cmd in sorted(public_commands, key=lambda x: x.name):
                help_text += f"• {cmd.get_help_text('ru')}\n"
            help_text += "\n"

        # Admin commands
        if admin_commands:
            help_text += "🔐 <b>Команды администратора:</b>\n"
            for cmd in sorted(admin_commands, key=lambda x: x.name):
                help_text += f"• {cmd.get_help_text('ru')}\n"
            help_text += "\n"

        help_text += "ℹ️ <b>Возможности:</b>\n"
        help_text += "• Контекстные ответы\n"
        help_text += "• Автономные комментарии с ИИ\n"
        help_text += "• Поддержка нескольких языков\n"

        return help_text


# Global command registry instance
command_registry = CommandRegistry()
