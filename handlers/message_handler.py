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
from .commands.joke_command import handle_joke_command, send_joke_response  # noqa: F401
from .commands.ask_command import handle_ask_command  # noqa: F401
from .commands.help_command import handle_help_command  # noqa: F401
from .commands.context_command import handle_context_command  # noqa: F401
from .commands.reload_command import handle_reload_command  # noqa: F401
from .commands.comment_command import handle_comment_command  # noqa: F401
from .commands.profile_command import handle_profile_command  # noqa: F401
from .commands.chats_command import handle_chats_command  # noqa: F401
from .commands.setprompt_command import handle_setprompt_command  # noqa: F401
from .commands.saveprofiles_command import handle_saveprofiles_command  # noqa: F401

# Import other handlers
from .conversation_handler import handle_private_conversation
from .mention_handler import handle_mention, is_bot_mentioned
from .autonomous_handler import check_and_make_autonomous_comment, check_and_add_reaction


async def handle_message_reaction(update, context):
    """Handle message reaction updates.

    This function is called when users add/remove reactions to messages.
    Tracks user reaction patterns for profile analysis.
    """
    if not update.message_reaction:
        return

    reaction_update = update.message_reaction
    chat_id = reaction_update.chat.id

    # Check if reaction tracking is enabled
    if not config.yaml_config.reaction_system.track_reactions:
        logger.debug(f"Reaction tracking disabled, ignoring reaction in chat {chat_id}")
        return

    try:
        # Get the user who reacted
        if not reaction_update.user:
            logger.debug("Reaction update without user, ignoring")
            return

        user_id = reaction_update.user.id
        bot_user_id = context.bot.id

        # Don't track bot's own reactions
        if user_id == bot_user_id:
            logger.debug(f"Ignoring bot's own reaction in chat {chat_id}")
            return

        # Process new reactions (reactions that were added)
        if reaction_update.new_reaction:
            for reaction in reaction_update.new_reaction:
                if hasattr(reaction, "emoji") and reaction.emoji:
                    emoji = reaction.emoji

                    # Try to get the target message text for content analysis
                    target_message_text = ""
                    try:
                        # Get the message that was reacted to
                        target_message = await context.bot.get_chat_message(
                            chat_id=chat_id, message_id=reaction_update.message_id
                        )
                        if target_message and target_message.text:
                            target_message_text = target_message.text
                    except Exception as e:
                        logger.debug(f"Could not retrieve target message text: {e}")

                    # Track the reaction in this specific chat
                    profile_manager.track_reaction_in_chat(
                        chat_id=chat_id, user_id=user_id, emoji=emoji, target_message_text=target_message_text
                    )

                    logger.debug(f"Tracked reaction {emoji} from user {user_id} in chat {chat_id}")

        # Note: We don't currently track reaction removals, but this could be added later
        # if reaction_update.old_reaction:
        #     # Handle reaction removals if needed

    except Exception as e:
        logger.error(f"Error processing message reaction: {e}", exc_info=True)


logger = logging.getLogger(__name__)


# Initialize AI provider and autonomous systems
config = get_config()
reaction_manager = get_reaction_manager(config)
ai_provider = create_provider(
    provider_type=config.ai_provider, api_key=config.api_key, model=config.model_name, base_url=config.base_url
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
    if config.yaml_config.user_profiling.enabled and message.from_user and message.from_user.id != bot_user_id:
        try:
            user_id = message.from_user.id
            username = message.from_user.username or message.from_user.first_name

            # Update basic profile info
            profile_manager.update_profile_from_message(message)
            logger.info(
                f"[PROFILE] Updated for user {user_id} (@{username}) - "
                f"Message #{profile_manager.profiles[user_id].message_count}"
            )

            # Check if AI enrichment should be triggered
            current_profile = profile_manager.profiles.get(user_id)
            if current_profile:
                enrichment_interval = config.yaml_config.user_profiling.enrichment_interval_messages
                if current_profile.message_count % enrichment_interval == 0:
                    logger.info(
                        f"[AI-ENRICH] Triggered for user {user_id} (@{username}) after "
                        f"{current_profile.message_count} messages"
                    )

                    # Get recent messages FROM THIS USER ONLY for profile analysis
                    user_messages = message_history.get_user_messages(
                        chat_id=chat_id,
                        user_id=user_id,
                        count=min(30, config.yaml_config.conversation_monitoring.context_window_size),
                    )

                    if user_messages:
                        # Run AI enrichment asynchronously
                        try:
                            await profile_manager.enrich_profile_with_ai(
                                user_id=user_id, recent_messages=user_messages, ai_analyzer=ai_provider
                            )
                            logger.info(f"[AI-ENRICH] Completed successfully for user {user_id}")
                        except Exception as e:
                            logger.error(f"[AI-ENRICH] Failed for user {user_id}: {e}")
                    else:
                        logger.warning(f"[AI-ENRICH] No messages available for user {user_id} in this chat")
                else:
                    messages_until_enrichment = enrichment_interval - (
                        current_profile.message_count % enrichment_interval
                    )
                    logger.debug(
                        f"[PROFILE] Update recorded for user {user_id}. "
                        f"AI enrichment in {messages_until_enrichment} messages"
                    )

                # Save profile after update
                profile_manager.save_profile(user_id)
        except Exception as e:
            logger.error(f"[PROFILE] Error updating profile: {e}")

    # Store message in history for context extraction (both private and group chats)
    message_history.add_message(chat_id, message)

    # Track message for autonomous commenting (only in group chats)
    if not is_private and message.from_user and message.from_user.id != bot_user_id:
        autonomous_commenter.add_message(chat_id, message)

    # Route to appropriate command handler using registry
    if message.text.startswith("/"):
        # Extract command name (remove leading slash and handle @username suffix)
        command_text = message.text.strip()
        if " " in command_text:
            command_part = command_text.split()[0][1:]  # Remove '/' and get first word
        else:
            command_part = command_text[1:]  # Remove leading '/'

        # Handle commands with @username suffix (e.g., /help@BotName)
        if "@" in command_part:
            command_name = command_part.split("@")[0]
        else:
            command_name = command_part

        # Import registry and find command
        from .commands import command_registry

        command = command_registry.get_command(command_name)

        if command:
            # Check if user can execute this command
            user_id = message.from_user.id if message.from_user else 0
            if command.can_execute(user_id, config):
                await command.execute(update, context)
                return
            else:
                await message.reply_text(
                    "❌ You don't have permission to use this command.", reply_to_message_id=message.message_id
                )
                return
        else:
            # Unknown command
            await message.reply_text(
                f"❌ Unknown command: /{command_name}\n\nUse /help to see available commands.",
                reply_to_message_id=message.message_id,
            )
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
    if not is_private and config.yaml_config.autonomous_commenting.enabled and not message.text.startswith("/"):
        await check_and_make_autonomous_comment(update, context)

    # Check for autonomous reaction opportunity (group chats only)
    if (
        not is_private
        and message.from_user
        and message.from_user.id != bot_user_id
        and not message.text.startswith("/")
    ):
        await check_and_add_reaction(update, context)
