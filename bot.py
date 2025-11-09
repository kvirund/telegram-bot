"""Main Telegram bot application."""
import sys
import signal
import logging
import asyncio
import argparse
from config import get_config
from services.bot_service import BotService
from services.profile_regeneration_service import ProfileRegenerationService


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


# Global bot service instance for graceful shutdown
bot_service = None


def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    # Perform synchronous shutdown
    if bot_service:
        bot_service.shutdown_sync()

    logger.info("Shutdown complete")
    sys.exit(0)


async def regenerate_profiles_main():
    """Run profile regeneration as a standalone operation."""
    logger.info("REGENERATE PROFILES MODE")

    try:
        service = ProfileRegenerationService()
        result = await service.regenerate_all_profiles()

        logger.info("Profile regeneration completed:")
        logger.info(f"  Processed: {result['processed']}")
        logger.info(f"  Skipped: {result['skipped']}")
        logger.info(f"  Failed: {result['failed']}")
        logger.info(f"  Total: {result['total']}")

    except Exception as e:
        logger.error(f"Profile regeneration failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point for the bot."""
    global bot_service

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Telegram AI Assistant')
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
        asyncio.run(regenerate_profiles_main())
        return

    logger.info("Starting Telegram AI Assistant...")

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

        # Create and initialize bot service
        bot_service = BotService()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        # Run the bot (let the Application manage the event loop)
        bot_service.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
