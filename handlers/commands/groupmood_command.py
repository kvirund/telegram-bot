"""Group mood command handler."""

import logging
import html
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.reaction_analytics import reaction_analytics
from .base import Command
from .arguments import ArgumentDefinition, ArgumentType

logger = logging.getLogger(__name__)
config = get_config()


class GroupMoodCommand(Command):
    """GroupMood command for showing current group sentiment.

    USAGE VARIANTS:

    1. Show current mood: /groupmood
       - Displays current group sentiment analysis (public command)
       - Shows positive/neutral/negative percentages and active users

    2. Reset reaction data: /groupmood <user> <channel> reset
       - Clears all stored reaction data for the specified chat (admin only)
       - Example: /groupmood all 123456789 reset

    3. Rebuild user profiles: /groupmood <user> <channel> rebuild [mode]
       - Rebuilds AI profiles using message history (admin only)
       - Modes: 'N' (last 100 messages) or 'full' (all history)
       - Example: /groupmood 987654321 -123456789 rebuild full

    PARAMETERS:
    - <user>: User ID (e.g., 123456789) or 'all' for all users
    - <channel>: Chat/channel ID (defaults to current chat if omitted)
    - <operation>: 'reset' (clear data) or 'rebuild' (rebuild profiles)
    - [rebuild_mode]: Optional, 'N' (100 msgs) or 'full' (all history)
    """

    def __init__(self):
        # Define proper argument structure for better help display
        arguments = [
            ArgumentDefinition(
                name="user",
                type=ArgumentType.STRING,
                required=False,
                description="User ID or 'all' (default: all). Examples: 123456789, all"
            ),
            ArgumentDefinition(
                name="channel",
                type=ArgumentType.STRING,
                required=False,
                description="Chat/channel ID (default: current chat). Example: -123456789"
            ),
            ArgumentDefinition(
                name="operation",
                type=ArgumentType.CHOICE,
                required=False,
                choices=["reset", "rebuild"],
                description="Operation: 'reset' (clear data) or 'rebuild' (rebuild profiles)"
            ),
            ArgumentDefinition(
                name="rebuild_mode",
                type=ArgumentType.CHOICE,
                required=False,
                choices=["N", "full"],
                description="'N' (last 100 msgs) or 'full' (all history), default: current context"
            )
        ]
        super().__init__(
            name="groupmood",
            description="Show/manage group sentiment analysis and user profiles",
            admin_only=False,  # Will be checked dynamically in execute()
            arguments=arguments
        )

    def get_help_text(self, language: str = "en") -> str:
        """Get comprehensive help text for the groupmood command."""
        help_lines = [
            f"{self.command_name} - {self.description}",
            "",
            "USAGE VARIANTS:",
            "",
            "1. Show current mood: /groupmood",
            "   - Displays current group sentiment analysis (public command)",
            "   - Shows positive/neutral/negative percentages and active users",
            "",
            "2. Reset reaction data: /groupmood <user> <channel> reset",
            "   - Clears all stored reaction data for the specified chat (admin only)",
            "   - Example: /groupmood all 123456789 reset",
            "",
            "3. Rebuild user profiles: /groupmood <user> <channel> rebuild [mode]",
            "   - Rebuilds AI profiles using message history (admin only)",
            "   - Modes: 'N' (last 100 messages) or 'full' (all history)",
            "   - Example: /groupmood 987654321 -123456789 rebuild full",
            "",
            "PARAMETERS:",
            "- <user>: User ID (e.g., 123456789) or 'all' for all users",
            "- <channel>: Chat/channel ID (defaults to current chat if omitted)",
            "- <operation>: 'reset' (clear data) or 'rebuild' (rebuild profiles)",
            "- [rebuild_mode]: Optional, 'N' (100 msgs) or 'full' (all history)"
        ]

        return html.escape("\n".join(help_lines))

    def can_execute(self, user_id: int, config) -> bool:
        """Check if user can execute this command.

        /groupmood without arguments is public.
        /groupmood with arguments requires admin privileges.
        """
        # For now, allow all users - admin check will be done in execute()
        # This is because we need to parse the message to determine if args are provided
        return True

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /groupmood command with custom syntax parsing.

        Supports syntax:
        - /groupmood - Show current group mood
        - /groupmood <user>/all <channel> reset - Reset data
        - /groupmood <user>/all <channel> rebuild [N|full] - Rebuild profiles
        """
        if not update.message:
            return

        message = update.message
        current_chat_id = message.chat_id
        user_id = message.from_user.id if message.from_user else 0

        try:
            # Custom parsing for the specific syntax
            command_text = message.text.strip()
            parts = command_text.split()

            if len(parts) == 1:
                # Just /groupmood - show current mood
                await self._show_group_mood(current_chat_id, message)
                return

            # Parse arguments: <user>/all <channel> <operation> [rebuild_mode]
            args = parts[1:]

            if len(args) < 3:
                await message.reply_text(
                    "❌ Invalid syntax. Use:\n"
                    "/groupmood - Show current mood\n"
                    "/groupmood <user>/all <channel> reset\n"
                    "/groupmood <user>/all <channel> rebuild [N|full]"
                )
                return

            target_user = args[0]
            channel = args[1]
            operation = args[2]
            rebuild_mode = args[3] if len(args) > 3 else None

            # Validate operation
            if operation not in ["reset", "rebuild"]:
                await message.reply_text(f"❌ Unknown operation: {operation}. Use 'reset' or 'rebuild'.")
                return

            # Validate rebuild_mode if provided
            if rebuild_mode and rebuild_mode not in ["N", "full"]:
                await message.reply_text(f"❌ Invalid rebuild mode: {rebuild_mode}. Use 'N' or 'full'.")
                return

            # Convert channel to int if it's a numeric string
            try:
                target_chat_id = int(channel)
            except ValueError:
                target_chat_id = current_chat_id  # fallback to current chat

            # Handle operations
            if operation == "reset":
                # Admin-only: Clear reaction data
                if user_id not in config.admin_user_ids:
                    await message.reply_text("❌ Only administrators can reset group mood data.")
                    return

                await self._reset_group_mood(target_chat_id, message)

            elif operation == "rebuild":
                # Admin-only: Rebuild profiles
                if user_id not in config.admin_user_ids:
                    await message.reply_text("❌ Only administrators can rebuild profiles.")
                    return

                await self._rebuild_profiles_from_history(target_chat_id, message, rebuild_mode)

        except Exception as e:
            logger.error(f"Error in groupmood command: {e}")
            await message.reply_text("❌ Error analyzing group mood.")

    async def _show_group_mood(self, chat_id: int, message) -> None:
        """Show current group mood analysis."""
        # Get group mood analysis
        mood_data = reaction_analytics.get_group_mood(chat_id)

        mood_message = "😊 Group Mood Analysis\n\n"
        mood_message += f"📍 Current Mood: {mood_data['overall_mood'].title()}\n\n"
        mood_message += "📊 Sentiment Distribution:\n"
        mood_message += f"😀 Positive: {mood_data['positive_percentage']}%\n"
        mood_message += f"😐 Neutral: {mood_data['neutral_percentage']}%\n"
        mood_message += f"😞 Negative: {mood_data['negative_percentage']}%\n\n"
        mood_message += f"👥 Active Users: {mood_data['active_users']}\n"
        mood_message += f"💬 Recent Reactions: {mood_data['recent_reactions']}\n\n"
        mood_message += f"💡 {mood_data['message']}"

        await message.reply_text(mood_message)

    async def _reset_group_mood(self, chat_id: int, message) -> None:
        """Reset/clear all reaction data for this chat."""
        try:
            from utils.profile_manager import profile_manager

            # Clear chat reactions
            chat_reactions = profile_manager.load_chat_reactions(chat_id)
            chat_reactions.reactions.clear()
            chat_reactions.last_updated = datetime.utcnow().isoformat()

            # Save the cleared data
            profile_manager.save_chat_reactions(chat_id)

            logger.info(f"Cleared reaction data for chat {chat_id}")

            await message.reply_text(
                "✅ Group mood data reset for this chat!\n\n"
                "🗑️ Cleared all stored reaction data\n"
                "🔄 Fresh analysis will start from new reactions\n\n"
                "Use `/groupmood` to see the current (empty) state."
            )

        except Exception as e:
            logger.error(f"Error resetting group mood for chat {chat_id}: {e}")
            await message.reply_text("❌ Error resetting group mood data.")

    async def _rebuild_profiles_from_history(self, chat_id: int, message, rebuild_mode: str = None) -> None:
        """Rebuild user profiles using different message sources based on rebuild_mode.

        Args:
            chat_id: Chat ID to rebuild profiles for
            message: Telegram message object
            rebuild_mode: "N", "full", or None (default: current context)
        """
        try:
            from utils.context_extractor import message_history
            from utils.profile_manager import profile_manager
            from ai_providers import create_provider

            # Determine message source based on rebuild_mode
            if rebuild_mode == "full":
                # Use full chat history
                all_messages = message_history.get_all_messages_for_chat(chat_id)
                mode_description = "full chat history"
            elif rebuild_mode == "N":
                # Use N messages from history (let's use 100 for now, could be made configurable)
                all_messages = message_history.get_recent_messages(chat_id, limit=100) or []
                mode_description = "last 100 messages from history"
            else:
                # Default: use current context messages (stored messages)
                all_messages = message_history.get_recent_messages(chat_id) or []
                mode_description = "current context messages"

            if not all_messages:
                await message.reply_text(f"❌ No {mode_description} available for this chat.")
                return

            await message.reply_text(
                f"🔄 Starting profile rebuild using {mode_description}...\n\n"
                f"📊 Found {len(all_messages)} messages\n"
                f"This may take a few moments."
            )

            # Get AI provider for profile enrichment
            ai_provider = create_provider(
                provider_type=config.ai_provider,
                api_key=config.api_key,
                model=config.model_name,
                base_url=config.base_url,
            )

            # Group messages by user
            messages_by_user = {}
            for msg in all_messages:
                user_id = msg.get("from", {}).get("id")
                if user_id:
                    if user_id not in messages_by_user:
                        messages_by_user[user_id] = []
                    messages_by_user[user_id].append(msg)

            # Rebuild profiles for each user
            rebuilt_count = 0
            for user_id, user_messages in messages_by_user.items():
                try:
                    # Convert messages to text for AI analysis
                    # Use different message limits based on rebuild mode
                    if rebuild_mode == "full":
                        # For full rebuild, use more messages but limit to avoid token limits
                        messages_to_use = user_messages[-100:]  # Last 100 messages per user
                    else:
                        # For other modes, use last 50 messages
                        messages_to_use = user_messages[-50:]

                    message_texts = []
                    for msg in messages_to_use:
                        if "text" in msg and msg["text"]:
                            # Include sender info for context
                            sender_name = msg.get("from", {}).get("first_name", "User")
                            message_texts.append(f"{sender_name}: {msg['text']}")

                    if message_texts:
                        message_history_text = "\n".join(message_texts)

                        # Enrich profile with AI
                        await profile_manager.enrich_profile_with_ai(
                            user_id=user_id, recent_messages=message_history_text, ai_analyzer=ai_provider
                        )

                        rebuilt_count += 1

                except Exception as e:
                    logger.warning(f"Failed to rebuild profile for user {user_id}: {e}")

            # Save all updated profiles
            profile_manager.save_all_profiles()

            await message.reply_text(
                f"✅ Profile rebuild completed!\n\n"
                f"👥 Rebuilt profiles for {rebuilt_count} users\n"
                f"📊 Used {mode_description}\n"
                f"💾 All profile data saved to disk"
            )

            logger.info(f"Rebuilt {rebuilt_count} profiles using {mode_description} for chat {chat_id}")

        except Exception as e:
            logger.error(f"Error rebuilding profiles for chat {chat_id}: {e}")
            await message.reply_text("❌ Error rebuilding profiles from chat history.")


# Create and register the command instance
groupmood_command = GroupMoodCommand()


# Legacy function for backward compatibility during transition
async def handle_groupmood_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await groupmood_command.execute(update, context)
