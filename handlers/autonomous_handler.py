"""Handle autonomous commenting and reactions."""
import logging
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ContextTypes
from config import get_config
from utils.autonomous_commenter import AutonomousCommenter
from utils.profile_manager import profile_manager
from utils.reaction_manager import get_reaction_manager
from ai_providers import create_provider

logger = logging.getLogger(__name__)


async def check_and_make_autonomous_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if bot should make an autonomous comment and generate it.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    config = get_config()
    ai_provider = create_provider(
        provider_type=config.ai_provider,
        api_key=config.api_key,
        model=config.model_name,
        base_url=config.base_url
    )
    autonomous_commenter = AutonomousCommenter(config, profile_manager)

    if not update.message:
        return

    message = update.message
    chat_id = message.chat_id
    bot_user_id = context.bot.id

    try:
        # Check if should comment
        if not autonomous_commenter.should_comment(chat_id, bot_user_id):
            return

        # Additional AI check if enabled
        if config.yaml_config.autonomous_commenting.use_ai_decision:
            if not await autonomous_commenter.should_comment_ai_check(chat_id, bot_user_id, ai_provider):
                logger.info(f"AI decided not to comment in chat {chat_id}")
                return

        logger.info(f"Autonomous comment triggered for chat {chat_id}")

        # Generate comment
        comment = await autonomous_commenter.generate_comment(
            chat_id=chat_id,
            ai_provider=ai_provider,
            bot_user_id=bot_user_id
        )

        if not comment:
            logger.warning(f"Failed to generate autonomous comment for chat {chat_id}")
            return

        # Send comment (reply or standalone)
        if comment.reply_to_message_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text=comment.text,
                reply_to_message_id=comment.reply_to_message_id
            )
            logger.info(f"Sent autonomous reply to message {comment.reply_to_message_id} in chat {chat_id}")
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=comment.text
            )
            logger.info(f"Sent autonomous standalone comment in chat {chat_id}")

        # Mark that we commented
        autonomous_commenter.mark_commented(chat_id)

        # Record roast if applicable
        if comment.target_user_id and comment.comment_type == "roast":
            profile_manager.record_roast(
                target_user_id=comment.target_user_id,
                roast_topic=comment.comment_type,
                success=True
            )

    except Exception as e:
        logger.error(f"Error in autonomous commenting: {e}", exc_info=True)


async def check_and_add_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if bot should react to a message and add reaction.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    config = get_config()
    reaction_manager = get_reaction_manager(config)

    if not update.message:
        return

    message = update.message
    chat_id = message.chat_id

    try:
        # Check if should react
        if not reaction_manager.should_react(chat_id):
            return

        logger.info(f"Autonomous reaction triggered for chat {chat_id}")

        # Choose appropriate reaction
        reaction = reaction_manager.choose_reaction(message.text)

        # Check if set_message_reaction is available (requires python-telegram-bot >= 20.0)
        if not hasattr(context.bot, 'set_message_reaction'):
            logger.warning("Reaction API not available in your python-telegram-bot version. Please upgrade to >= 20.0 for reaction support.")
            return

        # Add reaction to message using ReactionTypeEmoji
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=reaction)]
        )

        # Mark that we reacted
        reaction_manager.mark_reacted(chat_id)

        logger.info(f"Added reaction to message {message.message_id} in chat {chat_id}")

    except AttributeError as e:
        logger.error(f"Reaction API not supported: {e}. Upgrade python-telegram-bot to >= 20.0")
    except Exception as e:
        logger.error(f"Error adding reaction: {e}", exc_info=True)
