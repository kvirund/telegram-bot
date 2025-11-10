"""Handle /setprompt command to modify system prompts."""

import logging
import yaml
import os
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config, reload_config
from .base import Command

logger = logging.getLogger(__name__)


class SetPromptCommand(Command):
    """SetPrompt command for modifying system prompts.

    Usage:
    - /setprompt - Show current prompts and available prompt types
    - /setprompt <type> <new_prompt> - Update a specific prompt

    Available types: joke_generation, conversation, autonomous_comment, ai_decision, mention_response

    Only administrators can use this command.
    """

    def __init__(self):
        super().__init__(name="setprompt", description="Modify system prompts (admin only)", admin_only=True)

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /setprompt command to modify system prompts.

        Usage:
        - /setprompt - Show current prompts and available prompt types
        - /setprompt <type> <new_prompt> - Update a specific prompt

        Available types: joke_generation, conversation, autonomous_comment, ai_decision, mention_response

        Only administrators can use this command.

        Args:
            update: Telegram update object
            context: Telegram context object
        """
        config = get_config()

        if not update.message or not update.message.from_user:
            return

        message = update.message
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"

        logger.info(f"User {user_id} (@{username}) requested /setprompt command")

        # Check if command is sent in private chat only
        if message.chat.type != "private":
            logger.warning(f"/setprompt command attempted in group chat {message.chat_id} by user {user_id}")
            await message.reply_text(
                "[X] This command can only be used in private chat with the bot.",
                reply_to_message_id=message.message_id,
            )
            return

        # Check admin privilege
        if user_id not in config.admin_user_ids:
            logger.warning(f"Unauthorized /setprompt attempt by user {user_id}")
            await message.reply_text(
                "[X] Only administrators can modify system prompts.", reply_to_message_id=message.message_id
            )
            return

        try:
            # Parse command
            command_text = message.text.strip()
            parts = command_text.split(maxsplit=2)

            if len(parts) < 2:
                # Show current prompts
                current_prompts = config.yaml_config.system_prompts
                response = "[i] Current System Prompts:\n\n"
                response += f"1. joke_generation:\n{current_prompts.joke_generation[:100]}...\n\n"
                response += f"2. conversation:\n{current_prompts.conversation[:100]}...\n\n"
                response += f"3. autonomous_comment:\n{current_prompts.autonomous_comment[:100]}...\n\n"
                response += f"4. ai_decision:\n{current_prompts.ai_decision[:100]}...\n\n"
                response += f"5. mention_response:\n{current_prompts.mention_response[:100]}...\n\n"
                response += "Usage: /setprompt <type> <new_prompt>\n"
                response += "Example: /setprompt joke_generation Your new prompt here"

                await message.reply_text(response, reply_to_message_id=message.message_id)
                return

            if len(parts) < 3:
                await message.reply_text(
                    "[X] Missing prompt text.\n" "Usage: /setprompt <type> <new_prompt>",
                    reply_to_message_id=message.message_id,
                )
                return

            prompt_type = parts[1].lower()
            new_prompt = parts[2]

            # Validate prompt type
            valid_types = ["joke_generation", "conversation", "autonomous_comment", "ai_decision", "mention_response"]
            if prompt_type not in valid_types:
                await message.reply_text(
                    f"[X] Invalid prompt type: {prompt_type}\n" f"Valid types: {', '.join(valid_types)}",
                    reply_to_message_id=message.message_id,
                )
                return

            # Update prompt in config.yaml
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")

            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            if "system_prompts" not in yaml_data:
                yaml_data["system_prompts"] = {}

            yaml_data["system_prompts"][prompt_type] = new_prompt

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)

            # Reload config
            config = reload_config()

            logger.info(f"Prompt '{prompt_type}' updated by admin {user_id}")

            await message.reply_text(
                f"[OK] Prompt '{prompt_type}' updated successfully!\n\n"
                f"New prompt (first 200 chars):\n{new_prompt[:200]}{'...' if len(new_prompt) > 200 else ''}",
                reply_to_message_id=message.message_id,
            )

        except Exception as e:
            logger.error(f"Error in /setprompt command: {e}")
            await message.reply_text(f"[X] Error: {str(e)}", reply_to_message_id=message.message_id)


# Create and register the command instance
setprompt_command = SetPromptCommand()


# Legacy function for backward compatibility during transition
async def handle_setprompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await setprompt_command.execute(update, context)
