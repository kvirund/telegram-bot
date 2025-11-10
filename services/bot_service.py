"""Bot service for managing Telegram bot initialization and lifecycle."""

import logging
import asyncio
from typing import Optional
from telegram import Update, BotCommand
from telegram.ext import Application, MessageHandler, MessageReactionHandler, CallbackQueryHandler, filters
from config import get_config
from handlers.message_handler import handle_message, handle_message_reaction, auto_save_profiles, auto_save_context
from utils.profile_manager import profile_manager
from utils.context_extractor import message_history

logger = logging.getLogger(__name__)


class BotService:
    """Service class for managing Telegram bot operations."""

    def __init__(self):
        """Initialize the bot service."""
        self.config = get_config()
        self.app: Optional[Application] = None
        self.background_tasks: set[asyncio.Task] = set()

    async def initialize(self) -> Application:
        """Initialize the Telegram bot application.

        Returns:
            Application: The initialized Telegram application
        """
        logger.info("Initializing Telegram bot application...")

        # Create the Application with post_init callback
        async def post_init(application: Application) -> None:
            """Initialize after application starts."""
            await self._start_background_tasks()
            await self._set_bot_commands()

        self.app = Application.builder().token(self.config.telegram_token).post_init(post_init).build()

        # Register all handlers
        self._register_handlers()

        # Register error handler
        self.app.add_error_handler(self._error_handler)

        logger.info("Bot application initialized successfully")
        return self.app

    async def _start_background_tasks(self) -> None:
        """Start background tasks for auto-saving."""
        if self.config.yaml_config.user_profiling.enabled:
            logger.info("Starting auto-save profiles background task...")
            task = asyncio.create_task(auto_save_profiles())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

        # Always start context auto-save task
        logger.info("Starting auto-save context history background task...")
        task = asyncio.create_task(auto_save_context())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def _set_bot_commands(self) -> None:
        """Set bot commands for autocompletion in Telegram."""
        if not self.app:
            logger.warning("Cannot set bot commands: application not initialized")
            return

        # Import registry to get commands
        from handlers.commands import command_registry

        # Get bot commands from registry
        commands = command_registry.get_bot_commands()

        try:
            await self.app.bot.set_my_commands(commands)
            logger.info(f"Successfully set {len(commands)} bot commands for autocompletion")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")

    def _register_handlers(self) -> None:
        """Register all message and command handlers."""
        if not self.app:
            raise RuntimeError("Application not initialized")

        # Register message handler for text messages (this will handle both regular messages and commands)
        self.app.add_handler(MessageHandler(filters.TEXT, handle_message))

        # Register handler for message reactions
        self.app.add_handler(MessageReactionHandler(handle_message_reaction))

        # Register callback query handler for interactive help
        from handlers.commands.help_command import handle_help_callback
        self.app.add_handler(CallbackQueryHandler(handle_help_callback, pattern=r"^help_"))

        logger.info("Registered message, reaction, and callback query handlers")

    async def _error_handler(self, update: Update, context) -> None:
        """Handle errors that occur during update processing.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        logger.error(f"Update {update} caused error: {context.error}")

    def shutdown_sync(self) -> None:
        """Shutdown the bot gracefully (synchronous version for signal handlers)."""
        logger.info("Shutting down bot service...")

        # Save all profiles before shutdown
        logger.info("Saving all user profiles before shutdown...")
        try:
            saved_count = profile_manager.save_all_profiles()
            logger.info(f"Successfully saved {saved_count} profiles")
        except Exception as e:
            logger.error(f"Error saving profiles during shutdown: {e}")

        # Save context history before shutdown
        logger.info("Saving context history before shutdown...")
        try:
            message_history.save_all()
            logger.info("Successfully saved context history")
        except Exception as e:
            logger.error(f"Error saving context history during shutdown: {e}")

        # Cancel all background tasks synchronously
        cancelled_count = 0
        for task in self.background_tasks.copy():
            if not task.done():
                task.cancel()
                cancelled_count += 1
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} background tasks")

        # Note: We don't try to stop the application here because the event loop
        # is still running. The application will be stopped when the process exits.
        logger.info("Shutdown cleanup complete - application will stop on process exit")

    async def shutdown(self) -> None:
        """Shutdown the bot gracefully (async version)."""
        logger.info("Shutting down bot service...")

        # Save all profiles before shutdown
        logger.info("Saving all user profiles before shutdown...")
        try:
            saved_count = profile_manager.save_all_profiles()
            logger.info(f"Successfully saved {saved_count} profiles")
        except Exception as e:
            logger.error(f"Error saving profiles during shutdown: {e}")

        # Save context history before shutdown
        logger.info("Saving context history before shutdown...")
        try:
            message_history.save_all()
            logger.info("Successfully saved context history")
        except Exception as e:
            logger.error(f"Error saving context history during shutdown: {e}")

        # Cancel all background tasks
        cancelled_count = 0
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                cancelled_count += 1
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} background tasks")
        self.background_tasks.clear()

        if self.app:
            await self.app.stop()
            logger.info("Bot application stopped")

    def run(self) -> None:
        """Run the bot with polling (blocking call)."""
        logger.info("Starting bot polling...")
        logger.info("Press Ctrl+C to stop the bot")

        # Create the Application - post_init will handle async initialization
        async def post_init(application: Application) -> None:
            """Initialize after application starts."""
            await self._start_background_tasks()
            await self._set_bot_commands()

        self.app = Application.builder().token(self.config.telegram_token).post_init(post_init).build()

        # Register all handlers
        self._register_handlers()

        # Register error handler
        self.app.add_error_handler(self._error_handler)

        logger.info("Bot application initialized successfully")

        # Run polling (this is blocking and manages its own event loop)
        self.app.run_polling(
            allowed_updates=Update.ALL_TYPES, drop_pending_updates=True  # Drop pending updates on start
        )

    def start(self) -> None:
        """Start the bot (blocking call)."""
        logger.info("Starting bot service...")
        self.run()
