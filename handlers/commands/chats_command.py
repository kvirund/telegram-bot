"""Handle /chats command to list all chats where the bot is present."""

import logging
import html
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from .base import Command

logger = logging.getLogger(__name__)


class ChatsCommand(Command):
    """Chats command for listing all active chats.

    Only administrators can use this command.
    """

    def __init__(self):
        super().__init__(name="chats", description="List all active chats (admin only)", admin_only=True)

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /chats command to list all chats where the bot is present.

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

        logger.info(f"User {user_id} (@{username}) requested /chats command")

        # Check admin privilege
        if user_id not in config.admin_user_ids:
            await message.reply_text(
                "❌ Only administrators can view chat list.", reply_to_message_id=message.message_id
            )
            return

        try:
            # Get all chats from context history
            all_chats = message_history.get_all_chat_ids()

            if not all_chats:
                await message.reply_text(
                    "📭 No active chats found.\n\nThe bot hasn't received messages in any chats yet.",
                    reply_to_message_id=message.message_id,
                )
                return

            # Build response using HTML instead of Markdown for better compatibility
            response = f"💬 <b>Active Chats</b> ({len(all_chats)})\n\n"

            # Try to get chat information for each chat
            for chat_id in sorted(all_chats):
                try:
                    # Get chat info
                    chat = await context.bot.get_chat(chat_id)
                    chat_type = chat.type

                    # Format chat name (escape HTML special chars)
                    if chat_type == "private":
                        chat_name = f"{chat.first_name or 'Private'}"
                        if chat.username:
                            chat_name += f" (@{chat.username})"
                        chat_icon = "👤"
                    elif chat_type in ["group", "supergroup"]:
                        chat_name = chat.title or "Group"
                        chat_icon = "👥"
                    elif chat_type == "channel":
                        chat_name = chat.title or "Channel"
                        chat_icon = "📢"
                    else:
                        chat_name = "Unknown"
                        chat_icon = "❓"

                    # Escape HTML special characters in chat name
                    chat_name = html.escape(chat_name)

                    # Get message count
                    recent_messages = message_history.get_recent_messages(chat_id)
                    msg_count = len(recent_messages) if recent_messages else 0

                    response += f"{chat_icon} <b>{chat_name}</b>\n"
                    response += f"   • ID: <code>{chat_id}</code>\n"
                    response += f"   • Type: {chat_type}\n"
                    response += f"   • Messages: {msg_count}\n\n"

                except Exception as e:
                    # Chat might be inaccessible or bot was removed
                    logger.warning(f"Could not get info for chat {chat_id}: {e}")
                    response += f"❓ <b>Unknown Chat</b>\n"
                    response += f"   • ID: <code>{chat_id}</code>\n"
                    response += f"   • Status: Inaccessible\n\n"

            # Send response (might be long, so check length)
            if len(response) > 4000:
                # Split into multiple messages
                parts = []
                current = ""
                for line in response.split("\n\n"):
                    if len(current) + len(line) + 2 > 4000:
                        parts.append(current)
                        current = line + "\n\n"
                    else:
                        current += line + "\n\n"
                if current:
                    parts.append(current)

                for i, part in enumerate(parts):
                    if i == 0:
                        await message.reply_text(part, reply_to_message_id=message.message_id, parse_mode="HTML")
                    else:
                        await message.reply_text(part, parse_mode="HTML")
            else:
                await message.reply_text(response, reply_to_message_id=message.message_id, parse_mode="HTML")

            logger.info(f"Chat list displayed for admin {user_id} ({len(all_chats)} chats)")

        except Exception as e:
            logger.error(f"Error in /chats command: {e}")
            await message.reply_text(f"❌ Error: {str(e)}", reply_to_message_id=message.message_id)


# Create and register the command instance
chats_command = ChatsCommand()


# Legacy function for backward compatibility during transition
async def handle_chats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await chats_command.execute(update, context)
