"""Base classes for command system."""
import logging
from abc import ABC, abstractmethod
from typing import Callable, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class Command(ABC):
    """Base class for all bot commands.

    Each command should inherit from this class and implement the required methods.
    Commands are automatically registered when instantiated.
    """

    def __init__(self, name: str, description: str, admin_only: bool = False):
        """Initialize a command.

        Args:
            name: Command name without the leading slash (e.g., 'help', 'joke')
            description: Short description for help and bot menu
            admin_only: Whether this command requires admin privileges
        """
        self.name = name
        self.description = description
        self.admin_only = admin_only
        self.command_name = f"/{name}"

        # Register this command
        from .registry import command_registry
        command_registry.register_command(self)

    @abstractmethod
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Execute the command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        pass

    def can_execute(self, user_id: int, config: Any) -> bool:
        """Check if user can execute this command.

        Args:
            user_id: User ID attempting to execute command
            config: Bot configuration object

        Returns:
            bool: True if user can execute command
        """
        if not self.admin_only:
            return True

        # Check if user is admin
        return user_id in getattr(config, 'admin_user_ids', [])

    def get_help_text(self, language: str = 'en') -> str:
        """Get help text for this command.

        Args:
            language: Language code ('en' or 'ru')

        Returns:
            str: Help text for this command
        """
        return f"{self.command_name} - {self.description}"


class FunctionCommand(Command):
    """Command that wraps an existing function handler.

    This allows gradual migration of existing function-based commands
    to the new class-based system.
    """

    def __init__(self, name: str, description: str, handler: Callable, admin_only: bool = False):
        """Initialize a function-based command.

        Args:
            name: Command name without leading slash
            description: Command description
            handler: Async function that handles the command
            admin_only: Whether command requires admin privileges
        """
        self.handler = handler
        super().__init__(name, description, admin_only)

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Execute the command by calling the handler function."""
        await self.handler(update, context)
