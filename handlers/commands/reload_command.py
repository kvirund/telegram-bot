"""Handle /reload command to reload configuration."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config, reload_config
from .base import Command


logger = logging.getLogger(__name__)


class ReloadCommand(Command):
    """Reload command for reloading bot configuration.

    This reloads both .env and config.yaml files without restarting the bot.
    Only authorized admin users can execute this command.
    """

    def __init__(self):
        super().__init__(name="reload", description="Reload configuration (admin only)", admin_only=True)

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reload command to reload configuration.

        This reloads both .env and config.yaml files without restarting the bot.
        Only authorized admin users can execute this command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        global config, autonomous_commenter

        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"

        logger.info(f"User {user_id} (@{username}) requested /reload command")

        # Check if command is sent in private chat only
        if message.chat.type != "private":
            logger.warning(f"/reload command attempted in group chat {message.chat_id} by user {user_id}")
            await message.reply_text(
                "❌ This command can only be used in private chat with the bot.", reply_to_message_id=message.message_id
            )
            return

        # Check if user is authorized admin
        config = get_config()
        if user_id not in config.admin_user_ids:
            logger.warning(f"Unauthorized /reload attempt by user {user_id} (@{message.from_user.username})")
            await message.reply_text(
                "❌ Unauthorized. Only bot administrators can reload configuration.",
                reply_to_message_id=message.message_id,
            )
            return

        try:
            logger.info(f"Reloading configuration requested by authorized user {user_id}")

            # Reload configuration
            old_config = config
            config = reload_config()

            # Update autonomous commenter with new config
            from utils.autonomous_commenter import AutonomousCommenter

            autonomous_commenter = AutonomousCommenter(config, None)  # Will be updated with proper profile_manager

            # Build response message
            changes = []
            if old_config.yaml_config.autonomous_commenting.enabled != config.yaml_config.autonomous_commenting.enabled:
                status = "ENABLED" if config.yaml_config.autonomous_commenting.enabled else "DISABLED"
                changes.append(f"Autonomous commenting: {status}")

            if (
                old_config.yaml_config.autonomous_commenting.roasting_aggression
                != config.yaml_config.autonomous_commenting.roasting_aggression
            ):
                changes.append(f"Roasting aggression: {config.yaml_config.autonomous_commenting.roasting_aggression}")

            if old_config.yaml_config.user_profiling.enabled != config.yaml_config.user_profiling.enabled:
                status = "ENABLED" if config.yaml_config.user_profiling.enabled else "DISABLED"
                changes.append(f"User profiling: {status}")

            response = "✅ Configuration reloaded successfully!\n\n"
            if changes:
                response += "Notable changes:\n" + "\n".join(f"- {change}" for change in changes)
            else:
                response += "No changes detected in configuration."

            response += f"\n\nCurrent settings:\n"
            response += f"- Autonomous commenting: {'ENABLED' if config.yaml_config.autonomous_commenting.enabled else 'DISABLED'}\n"
            response += f"- Roasting: {'ENABLED' if config.yaml_config.autonomous_commenting.roasting_enabled else 'DISABLED'}\n"
            response += f"- Aggression: {config.yaml_config.autonomous_commenting.roasting_aggression}\n"
            response += f"- User profiling: {'ENABLED' if config.yaml_config.user_profiling.enabled else 'DISABLED'}"

            await message.reply_text(response, reply_to_message_id=message.message_id)

            logger.info("Configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            await message.reply_text(
                f"❌ Error reloading configuration: {str(e)}", reply_to_message_id=message.message_id
            )


# Create and register the command instance
reload_command = ReloadCommand()


# Legacy function for backward compatibility during transition
async def handle_reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reload command to reload configuration.

    This reloads both .env and config.yaml files without restarting the bot.
    Only authorized admin users can execute this command.

    Args:
        update: Telegram update object
        context: Telegram context object
    """
    global config, autonomous_commenter

    if not update.message or not update.message.from_user:
        return

    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    logger.info(f"User {user_id} (@{username}) requested /reload command")

    # Check if command is sent in private chat only
    if message.chat.type != "private":
        logger.warning(f"/reload command attempted in group chat {message.chat_id} by user {user_id}")
        await message.reply_text(
            "❌ This command can only be used in private chat with the bot.", reply_to_message_id=message.message_id
        )
        return

    # Check if user is authorized admin
    config = get_config()
    if user_id not in config.admin_user_ids:
        logger.warning(f"Unauthorized /reload attempt by user {user_id} (@{message.from_user.username})")
        await message.reply_text(
            "❌ Unauthorized. Only bot administrators can reload configuration.", reply_to_message_id=message.message_id
        )
        return

    try:
        logger.info(f"Reloading configuration requested by authorized user {user_id}")

        # Reload configuration
        old_config = config
        config = reload_config()

        # Update autonomous commenter with new config
        from utils.autonomous_commenter import AutonomousCommenter

        autonomous_commenter = AutonomousCommenter(config, None)  # Will be updated with proper profile_manager

        # Build response message
        changes = []
        if old_config.yaml_config.autonomous_commenting.enabled != config.yaml_config.autonomous_commenting.enabled:
            status = "ENABLED" if config.yaml_config.autonomous_commenting.enabled else "DISABLED"
            changes.append(f"Autonomous commenting: {status}")

        if (
            old_config.yaml_config.autonomous_commenting.roasting_aggression
            != config.yaml_config.autonomous_commenting.roasting_aggression
        ):
            changes.append(f"Roasting aggression: {config.yaml_config.autonomous_commenting.roasting_aggression}")

        if old_config.yaml_config.user_profiling.enabled != config.yaml_config.user_profiling.enabled:
            status = "ENABLED" if config.yaml_config.user_profiling.enabled else "DISABLED"
            changes.append(f"User profiling: {status}")

        response = "✅ Configuration reloaded successfully!\n\n"
        if changes:
            response += "Notable changes:\n" + "\n".join(f"- {change}" for change in changes)
        else:
            response += "No changes detected in configuration."

        response += f"\n\nCurrent settings:\n"
        response += f"- Autonomous commenting: {'ENABLED' if config.yaml_config.autonomous_commenting.enabled else 'DISABLED'}\n"
        response += (
            f"- Roasting: {'ENABLED' if config.yaml_config.autonomous_commenting.roasting_enabled else 'DISABLED'}\n"
        )
        response += f"- Aggression: {config.yaml_config.autonomous_commenting.roasting_aggression}\n"
        response += f"- User profiling: {'ENABLED' if config.yaml_config.user_profiling.enabled else 'DISABLED'}"

        await message.reply_text(response, reply_to_message_id=message.message_id)

        logger.info("Configuration reloaded successfully")

    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        await message.reply_text(f"❌ Error reloading configuration: {str(e)}", reply_to_message_id=message.message_id)
