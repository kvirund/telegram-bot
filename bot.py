"""Main Telegram bot application."""
import sys
import signal
import logging
import asyncio
import argparse
from telegram import Update
from telegram.ext import Application, MessageHandler, MessageReactionHandler, filters
from config import get_config
from handlers.message_handler import handle_message, handle_message_reaction, auto_save_profiles, auto_save_context
from utils.profile_manager import profile_manager
from utils.context_extractor import message_history
from ai_providers import create_provider


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


async def regenerate_all_profiles():
    """Regenerate all user profiles from context history.
    
    This standalone function can be called from command line to regenerate
    all profiles using the new AI enrichment prompt.
    """
    logger.info("=" * 60)
    logger.info("PROFILE REGENERATION STARTING")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = get_config()
        logger.info(f"Configuration loaded: {config.ai_provider} / {config.model_name}")
        
        # Create AI provider
        ai_provider = create_provider(
            provider_type=config.ai_provider,
            api_key=config.api_key,
            model=config.model_name,
            base_url=config.base_url
        )
        logger.info("AI provider initialized")
        
        # Get all chats from message history
        all_chats = message_history.get_all_chat_ids()
        logger.info(f"Found {len(all_chats)} chats in history")
        
        # Collect user messages from all chats
        user_data = {}  # user_id -> messages list
        user_info = {}  # user_id -> user info dict

        for chat_id in all_chats:
            messages = message_history.get_recent_messages(chat_id)
            if not messages:
                continue

            # Limit to most recent 100 messages
            messages = messages[-100:]

            for msg_data in messages:
                msg_user_id = msg_data.get('user_id', 0)
                text = msg_data.get('text', '')

                if msg_user_id == 0 or not text or text.startswith('/'):
                    continue

                # Store user info from the first message we see for each user
                if msg_user_id not in user_info:
                    user_info[msg_user_id] = {
                        'username': msg_data.get('username', ''),
                        'first_name': msg_data.get('first_name', ''),
                        'last_name': msg_data.get('last_name', '')
                    }

                if msg_user_id not in user_data:
                    user_data[msg_user_id] = []
                user_data[msg_user_id].append(text)
        
        if not user_data:
            logger.warning("No user messages found in context history")
            return
        
        logger.info(f"Found {len(user_data)} users to process")
        
        # Process each user
        processed = 0
        skipped = 0
        failed = 0
        
        for user_id, messages in user_data.items():
            if len(messages) < 5:
                logger.info(f"Skipping user {user_id} (only {len(messages)} messages)")
                skipped += 1
                continue

            profile = profile_manager.load_profile(user_id)

            # Update profile with user info from context history
            if user_id in user_info:
                info = user_info[user_id]
                profile.username = info['username'] or profile.username
                profile.first_name = info['first_name'] or profile.first_name
                profile.last_name = info['last_name'] or profile.last_name

            messages_text = "\n".join(messages[:30])

            # Sanitize name for logging to avoid Unicode encoding issues
            safe_name = (profile.first_name or 'Unknown').encode('ascii', 'ignore').decode('ascii') or 'Unknown'
            logger.info(f"Processing user {user_id} ({safe_name}) - {len(messages)} messages")
            
            try:
                await profile_manager.enrich_profile_with_ai(
                    user_id=user_id,
                    recent_messages=messages_text,
                    ai_analyzer=ai_provider
                )
                profile_manager.save_profile(user_id)
                processed += 1
                logger.info(f"[OK] User {user_id} enriched successfully")

            except Exception as e:
                logger.error(f"[FAIL] Failed to regenerate profile for user {user_id}: {e}")
                failed += 1
        
        logger.info("=" * 60)
        logger.info("PROFILE REGENERATION COMPLETE")
        logger.info(f"Processed: {processed}")
        logger.info(f"Skipped (<5 messages): {skipped}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Total: {len(user_data)}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during profile regeneration: {e}", exc_info=True)
        raise


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
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Telegram Joke Bot')
    parser.add_argument(
        '--regenerate-profiles',
        action='store_true',
        help='Regenerate all user profiles from context history using AI enrichment'
    )
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # If regenerate profiles flag is set, run that instead of the bot
    if args.regenerate_profiles:
        logger.info("REGENERATE PROFILES MODE")
        asyncio.run(regenerate_all_profiles())
        return
    
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
