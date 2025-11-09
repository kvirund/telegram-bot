"""Message handlers for the Telegram bot."""
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from ai_providers import create_provider
from utils.context_extractor import message_history
from utils.profile_manager import profile_manager
from utils.autonomous_commenter import AutonomousCommenter
from utils.reaction_manager import get_reaction_manager

# Import command handlers
from .commands.joke_command import handle_joke_command, send_joke_response
from .commands.ask_command import handle_ask_command
from .commands.help_command import handle_help_command
from .commands.context_command import handle_context_command
from .commands.reload_command import handle_reload_command
from .commands.comment_command import handle_comment_command
from .commands.profile_command import handle_profile_command
from .commands.chats_command import handle_chats_command
from .commands.setprompt_command import handle_setprompt_command
from .commands.saveprofiles_command import handle_saveprofiles_command

# Import other handlers
from .conversation_handler import handle_private_conversation
from .mention_handler import handle_mention, is_bot_mentioned
from .autonomous_handler import check_and_make_autonomous_comment, check_and_add_reaction


async def handle_message_reaction(update, context):
    """Handle message reaction updates.

    This function is called when users add/remove reactions to messages.
    Currently, we don't do anything special with reactions, but this
    could be extended to track user reaction patterns.
    """
    # For now, just log the reaction event
    if update.message_reaction:
        logger.debug(f"Message reaction update: {update.message_reaction}")
    # Could be extended to track user reaction patterns in the future


logger = logging.getLogger(__name__)


# Initialize AI provider and autonomous systems
config = get_config()
reaction_manager = get_reaction_manager(config)
ai_provider = create_provider(
    provider_type=config.ai_provider,
    api_key=config.api_key,
    model=config.model_name,
    base_url=config.base_url
)

# Initialize autonomous commenter
autonomous_commenter = AutonomousCommenter(config, profile_manager)

# Auto-save profiles periodically
async def auto_save_profiles():
    """Background task to periodically save profiles."""
    while True:
        try:
            interval = config.yaml_config.user_profiling.auto_save_interval_seconds
            await asyncio.sleep(interval)
            if config.yaml_config.user_profiling.enabled:
                profile_manager.save_all_profiles()
                logger.info("Auto-saved all profiles")
        except Exception as e:
            logger.error(f"Error in auto-save profiles: {e}")


# Auto-save context history periodically
async def auto_save_context():
    """Background task to periodically save context history."""
    while True:
        try:
            # Save every 5 minutes (300 seconds)
            await asyncio.sleep(300)
            message_history.save_all()
            message_history.cleanup_expired()
            logger.info("Auto-saved context history and cleaned up expired messages")
        except Exception as e:
            logger.error(f"Error in auto-save context: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main message handler that processes all incoming messages.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    if not update.message or not update.message.text:
        return

    message = update.message
    chat_id = message.chat_id
    is_private = message.chat.type == "private"
    bot_user_id = context.bot.id

    # Update user profile (if profiling enabled and not bot's own message)
    if (config.yaml_config.user_profiling.enabled and
        message.from_user and
        message.from_user.id != bot_user_id):
        try:
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name

            # Update basic profile info
            profile_manager.update_profile_from_message(message)
            logger.info(f"[PROFILE] Updated for user {user_id} (@{username}) - Message #{profile_manager.profiles[user_id].message_count}")

            # Check if AI enrichment should be triggered
            current_profile = profile_manager.profiles.get(user_id)
            if current_profile:
                enrichment_interval = config.yaml_config.user_profiling.enrichment_interval_messages
                if current_profile.message_count % enrichment_interval == 0:
                    logger.info(f"[AI-ENRICH] Triggered for user {user_id} (@{username}) after {current_profile.message_count} messages")

                    # Get recent messages FROM THIS USER ONLY for profile analysis
                    user_messages = message_history.get_user_messages(
                        chat_id=chat_id,
                        user_id=user_id,
                        count=min(30, config.yaml_config.conversation_monitoring.context_window_size)
                    )

                    if user_messages:
                        # Run AI enrichment asynchronously
                        try:
                            await profile_manager.enrich_profile_with_ai(
                                user_id=user_id,
                                recent_messages=user_messages,
                                ai_analyzer=ai_provider
                            )
                            logger.info(f"[AI-ENRICH] Completed successfully for user {user_id}")
                        except Exception as e:
                            logger.error(f"[AI-ENRICH] Failed for user {user_id}: {e}")
                    else:
                        logger.warning(f"[AI-ENRICH] No messages available for user {user_id} in this chat")
                else:
                    messages_until_enrichment = enrichment_interval - (current_profile.message_count % enrichment_interval)
                    logger.debug(f"[PROFILE] Update recorded for user {user_id}. AI enrichment in {messages_until_enrichment} messages")

                # Save profile after update
                profile_manager.save_profile(user_id)
        except Exception as e:
            logger.error(f"[PROFILE] Error updating profile: {e}")

    # Store message in history for context extraction (both private and group chats)
    message_history.add_message(chat_id, message)

    # Track message for autonomous commenting (only in group chats)
    if not is_private and message.from_user and message.from_user.id != bot_user_id:
        autonomous_commenter.add_message(chat_id, message)

    # Route to appropriate command handler
    if message.text.startswith('/joke'):
        await handle_joke_command(update, context, is_private)
        return

    elif message.text.startswith('/ask'):
        await handle_ask_command(update, context)
        return

    elif message.text.startswith('/help'):
        await handle_help_command(update, context)
        return

    elif message.text.startswith('/context'):
        await handle_context_command(update, context)
        return

    # Admin-only commands
    elif message.text.startswith('/reload'):
        await handle_reload_command(update, context)
        return

    elif message.text.startswith('/comment'):
        await handle_comment_command(update, context)
        return

    elif message.text.startswith('/profile'):
        await handle_profile_command(update, context)
        return

    elif message.text.startswith('/chats'):
        await handle_chats_command(update, context)
        return

    elif message.text.startswith('/setprompt'):
        await handle_setprompt_command(update, context)
        return

    elif message.text.startswith('/saveprofiles'):
        await handle_saveprofiles_command(update, context)
        return

    # In private chats, respond conversationally to all messages
    if is_private:
        await handle_private_conversation(update, context)
        return

    # In group chats, check if bot is mentioned
    if is_bot_mentioned(message, config.bot_username):
        await handle_mention(update, context)
        return

    # Check for autonomous commenting opportunity (not in response to commands/mentions)
    if (not is_private and
        config.yaml_config.autonomous_commenting.enabled and
        not message.text.startswith('/')):
        await check_and_make_autonomous_comment(update, context)

    # Check for autonomous reaction opportunity (group chats only)
    if (not is_private and
        message.from_user and
        message.from_user.id != bot_user_id and
        not message.text.startswith('/')):
        await check_and_add_reaction(update, context)
