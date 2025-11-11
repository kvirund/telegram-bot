"""Users command handler - Admin command to list all known users."""

import logging
from typing import Dict, List, Set, Tuple
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.context_extractor import message_history
from utils.profile_manager import profile_manager
from .base import Command

logger = logging.getLogger(__name__)
config = get_config()


class UsersCommand(Command):
    """Users command for listing all users known to the bot.

    Admin-only command that discovers and lists all users from:
    - Message history (context_history JSON files)
    - User profiles (profiles/users directory)
    """

    def __init__(self):
        super().__init__(
            name="users",
            description="List all users known to the bot (admin only)",
            admin_only=True,
            description_ru="Показать всех известных боту пользователей (только админ)"
        )

    def _get_raw_help_text(self, language: str = "en") -> str:
        """Get raw help text for the users command."""
        return f"{self.command_name} - {self.description}\n\nLists all users discovered from message history and profile files."

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /users command."""
        if not update.message:
            return

        message = update.message
        user_id = message.from_user.id if message.from_user else 0

        # Admin check (additional safety check)
        if user_id not in config.admin_user_ids:
            await message.reply_text("❌ Только администраторы могут просматривать список пользователей.")
            return

        try:
            await message.reply_text("🔍 Поиск пользователей в истории сообщений и профилях...")

            # Discover users from different sources
            history_users = self._discover_users_from_history()
            profile_users = self._discover_users_from_profiles()

            # Combine and deduplicate users
            all_users = self._merge_user_data(history_users, profile_users)

            # Format and send response
            response = self._format_user_list(all_users)

            # Split long messages if needed (Telegram has 4096 char limit)
            if len(response) > 4000:
                # Split into chunks
                chunks = self._split_message(response, 3500)
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await message.reply_text(f"👥 Известные боту пользователи:\n\n{chunk}")
                    else:
                        await message.reply_text(chunk)
            else:
                await message.reply_text(f"👥 Известные боту пользователи:\n\n{response}")

            logger.info(f"Listed {len(all_users)} users for admin {user_id}")

        except Exception as e:
            logger.error(f"Error in users command: {e}")
            await message.reply_text("❌ Ошибка при получении списка пользователей.")

    def _discover_users_from_history(self) -> Dict[int, Dict]:
        """Discover users from message history.

        Returns:
            Dict mapping user_id to user info dict with keys: id, username, first_name, last_name, source
        """
        users = {}

        try:
            # Get all chat IDs from message history
            chat_ids = message_history.get_all_chat_ids()
            logger.info(f"Scanning {len(chat_ids)} chats for users")

            for chat_id in chat_ids:
                try:
                    # Get recent messages from this chat (limit to avoid excessive processing)
                    messages = message_history.get_recent_messages(chat_id, limit=1000) or []

                    for msg_data in messages:
                        user_id = msg_data.get("user_id")
                        if user_id and user_id > 0:  # Valid user ID
                            if user_id not in users:
                                users[user_id] = {
                                    "id": user_id,
                                    "username": msg_data.get("username", ""),
                                    "first_name": msg_data.get("first_name", "Unknown"),
                                    "last_name": msg_data.get("last_name", ""),
                                    "source": "history"
                                }
                            # Update with latest info if available
                            elif not users[user_id]["username"] and msg_data.get("username"):
                                users[user_id]["username"] = msg_data.get("username")
                            elif not users[user_id]["first_name"] or users[user_id]["first_name"] == "Unknown":
                                users[user_id]["first_name"] = msg_data.get("first_name", "Unknown")

                except Exception as e:
                    logger.warning(f"Failed to scan chat {chat_id} for users: {e}")

            logger.info(f"Discovered {len(users)} users from message history")

        except Exception as e:
            logger.error(f"Error discovering users from history: {e}")

        return users

    def _discover_users_from_profiles(self) -> Dict[int, Dict]:
        """Discover users from profile files.

        Returns:
            Dict mapping user_id to user info dict with keys: id, username, first_name, last_name, source
        """
        users = {}

        try:
            # Get all user IDs that have profiles
            # We need to scan the profiles/users directory
            import os
            users_dir = profile_manager.users_dir

            if os.path.exists(users_dir):
                for filename in os.listdir(users_dir):
                    if filename.startswith("user_") and filename.endswith(".json"):
                        try:
                            # Extract user ID from filename
                            user_id_str = filename.replace("user_", "").replace(".json", "")
                            user_id = int(user_id_str)

                            # Load profile to get user info
                            profile = profile_manager.load_profile(user_id)

                            users[user_id] = {
                                "id": user_id,
                                "username": profile.username,
                                "first_name": profile.first_name,
                                "last_name": profile.last_name,
                                "source": "profile"
                            }

                        except (ValueError, Exception) as e:
                            logger.warning(f"Failed to process profile file {filename}: {e}")

            logger.info(f"Discovered {len(users)} users from profile files")

        except Exception as e:
            logger.error(f"Error discovering users from profiles: {e}")

        return users

    def _merge_user_data(self, history_users: Dict[int, Dict], profile_users: Dict[int, Dict]) -> Dict[int, Dict]:
        """Merge user data from history and profiles, preferring profile data when available.

        Args:
            history_users: Users discovered from message history
            profile_users: Users discovered from profile files

        Returns:
            Merged user dictionary with combined source info
        """
        merged = {}

        # Start with all history users
        for user_id, user_data in history_users.items():
            merged[user_id] = user_data.copy()

        # Add/update with profile users
        for user_id, user_data in profile_users.items():
            if user_id in merged:
                # User exists in both - merge data and mark as both sources
                merged[user_id].update({
                    "username": user_data.get("username") or merged[user_id].get("username", ""),
                    "first_name": user_data.get("first_name") or merged[user_id].get("first_name", "Unknown"),
                    "last_name": user_data.get("last_name") or merged[user_id].get("last_name", ""),
                    "source": "both"
                })
            else:
                # Only in profiles
                merged[user_id] = user_data.copy()

        return merged

    def _format_user_list(self, users: Dict[int, Dict]) -> str:
        """Format user list for display.

        Args:
            users: Dictionary of user data

        Returns:
            Formatted string listing all users
        """
        if not users:
            return "Пользователи не найдены."

        # Sort users by ID for consistent output
        sorted_users = sorted(users.items(), key=lambda x: x[0])

        lines = []
        for user_id, user_data in sorted_users:
            # Format display name
            display_name = user_data.get("first_name", "Unknown")
            if user_data.get("last_name"):
                display_name += f" {user_data['last_name']}"

            # Format username
            username_part = ""
            if user_data.get("username"):
                username_part = f" (@{user_data['username']})"

            # Format source
            source = user_data.get("source", "unknown")
            source_emoji = {
                "history": "💬",
                "profile": "📁",
                "both": "📁💬"
            }.get(source, "❓")

            # Create user line
            line = f"• {display_name}{username_part} (ID: {user_id}) {source_emoji}"
            lines.append(line)

        # Add summary
        total_count = len(users)
        history_count = sum(1 for u in users.values() if u["source"] in ["history", "both"])
        profile_count = sum(1 for u in users.values() if u["source"] in ["profile", "both"])
        both_count = sum(1 for u in users.values() if u["source"] == "both")

        summary = f"\n📊 Total: {total_count} users"
        if history_count > 0:
            summary += f" | 💬 History: {history_count}"
        if profile_count > 0:
            summary += f" | 📁 Profiles: {profile_count}"
        if both_count > 0:
            summary += f" | 📁💬 Both: {both_count}"

        return "\n".join(lines) + summary

    def _split_message(self, text: str, max_length: int) -> List[str]:
        """Split a long message into chunks at word boundaries.

        Args:
            text: Text to split
            max_length: Maximum length per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        remaining = text

        while len(remaining) > max_length:
            # Find the last newline or space before max_length
            split_pos = remaining.rfind('\n', 0, max_length)
            if split_pos == -1:
                split_pos = remaining.rfind(' ', 0, max_length)
            if split_pos == -1:
                split_pos = max_length

            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos:].lstrip()

        if remaining:
            chunks.append(remaining)

        return chunks


# Create and register the command instance
users_command = UsersCommand()
