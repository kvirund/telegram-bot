"""Main Telegram bot application."""
import sys
import signal
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, MessageReactionHandler, filters
from config import get_config
from handlers.message_handler import handle_message, handle_message_reaction, auto_save_profiles, auto_save_context
from utils.profile_manager import profile_manager
from utils.context_extractor import message_history


# Configure logging
def setup_logging():
    """Set up logging configuration."""
    import os
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
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
auto_save_task = None


def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
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
    
    # Cancel auto-save task if running
    if auto_save_task and not auto_save_task.done():
        auto_save_task.cancel()
        logger.info("Cancelled auto-save task")
    
    if app:
        app.stop_running()
    
    logger.info("Shutdown complete")
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
    global app, auto_save_task
    
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
        
        # Log autonomous commenting status
        if config.yaml_config.autonomous_commenting.enabled:
            logger.info("Autonomous commenting: ENABLED")
            logger.info(f"  - Roasting enabled: {config.yaml_config.autonomous_commenting.roasting_enabled}")
            logger.info(f"  - Aggression level: {config.yaml_config.autonomous_commenting.roasting_aggression}")
        else:
            logger.info("Autonomous commenting: DISABLED")
        
        if config.yaml_config.user_profiling.enabled:
            logger.info("User profiling: ENABLED")
            logger.info(f"  - Profile directory: {config.yaml_config.user_profiling.profile_directory}")
        else:
            logger.info("User profiling: DISABLED")
        
        # Create the Application with post_init callback
        async def post_init(application: Application) -> None:
            """Initialize after application starts."""
            global auto_save_task
            tasks = []
            
            if config.yaml_config.user_profiling.enabled:
                logger.info("Starting auto-save profiles background task...")
                tasks.append(asyncio.create_task(auto_save_profiles()))
            
            # Always start context auto-save task
            logger.info("Starting auto-save context history background task...")
            tasks.append(asyncio.create_task(auto_save_context()))
            
            if tasks:
                auto_save_task = tasks[0]  # Keep reference for shutdown
        
        app = Application.builder().token(config.telegram_token).post_init(post_init).build()
        
        # Register message handler for text messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Register handler for /joke command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/joke'), handle_message))
        
        # Register handler for /ask command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/ask'), handle_message))
        
        # Register handler for /reload command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/reload'), handle_message))
        
        # Register handler for /comment command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/comment'), handle_message))
        
        # Register handler for /help command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/help'), handle_message))
        
        # Register handler for /context command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/context'), handle_message))
        
        # Register handler for /profile command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/profile'), handle_message))
        
        # Register handler for /chats command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/chats'), handle_message))
        
        # Register handler for /setprompt command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/setprompt'), handle_message))
        
        # Register handler for /saveprofiles command
        app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'^/saveprofiles'), handle_message))
        
        # Register handler for message reactions
        app.add_handler(MessageReactionHandler(handle_message_reaction))
        
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
