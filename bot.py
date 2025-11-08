"""Main Telegram bot application."""
import sys
import signal
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from config import get_config
from handlers.message_handler import handle_message


# Configure logging
def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


logger = logging.getLogger(__name__)


# Global application instance for graceful shutdown
app = None


def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if app:
        app.stop_running()
    sys.exit(0)


async def error_handler(update: Update, context) -> None:
    """Handle errors that occur during update processing.
    
    Args:
        update: Telegram update object
        context: Telegram context object
    """
    logger.error(f"Update {update} caused error: {context.error}")


def main():
    """Main entry point for the bot."""
    global app
    
    # Set up logging
    setup_logging()
    logger.info("Starting Telegram Joke Bot...")
    
    try:
        # Load configuration
        config = get_config()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"AI Provider: {config.ai_provider}")
        logger.info(f"Model: {config.model_name}")
        logger.info(f"Bot Username: {config.bot_username}")
        
        # Create the Application
        app = Application.builder().token(config.telegram_token).build()
        
        # Register message handler for text messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Register handler for /joke command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/joke'), handle_message))
        
        # Register error handler
        app.add_error_handler(error_handler)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        
        # Start the bot with long-polling
        logger.info("Bot started successfully. Polling for updates...")
        logger.info("Press Ctrl+C to stop the bot")
        
        # Run the bot until interrupted
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Drop pending updates on start
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
