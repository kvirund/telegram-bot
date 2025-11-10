"""Group mood command handler."""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.reaction_analytics import reaction_analytics
from .base import Command

logger = logging.getLogger(__name__)
config = get_config()


class GroupMoodCommand(Command):
    """GroupMood command for showing current group sentiment.

    Usage:
    - /groupmood - Show current group mood
    - /groupmood reset - Clear all reaction data for this chat (admin only)
    - /groupmood rebuild - Rebuild all user profiles using full chat history (admin only)
    """

    def __init__(self):
        super().__init__(
            name="groupmood",
            description="Show current group sentiment (/groupmood [reset|rebuild])",
            admin_only=False
        )

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /groupmood command to show current group sentiment.

        Usage:
        - /groupmood - Show current group mood
        - /groupmood reset - Clear all reaction data for this chat (admin only)
        - /groupmood rebuild - Rebuild all user profiles using full chat history (admin only)
        """
        if not update.message:
            return

        message = update.message
        chat_id = message.chat_id
        user_id = message.from_user.id if message.from_user else 0

        try:
            # Parse command arguments
            command_text = message.text.strip()
            parts = command_text.split()
            subcommand = parts[1] if len(parts) > 1 else None

            if subcommand == "reset":
                # Admin-only: Clear reaction data for this chat
                if user_id not in config.admin_user_ids:
                    await message.reply_text("❌ Only administrators can reset group mood data.")
                    return

                await self._reset_group_mood(chat_id, message)

            elif subcommand == "rebuild":
                # Admin-only: Rebuild profiles using full chat history
                if user_id not in config.admin_user_ids:
                    await message.reply_text("❌ Only administrators can rebuild profiles.")
                    return

                await self._rebuild_profiles_from_history(chat_id, message)

            else:
                # Default: Show current group mood
                await self._show_group_mood(chat_id, message)

        except Exception as e:
            logger.error(f"Error in groupmood command: {e}")
            await message.reply_text("❌ Error analyzing group mood.")

    async def _show_group_mood(self, chat_id: int, message) -> None:
        """Show current group mood analysis."""
        # Get group mood analysis
        mood_data = reaction_analytics.get_group_mood(chat_id)

        mood_message = f"😊 Group Mood Analysis\n\n"
        mood_message += f"📍 Current Mood: {mood_data['overall_mood'].title()}\n\n"
        mood_message += f"📊 Sentiment Distribution:\n"
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
                f"✅ Group mood data reset for this chat!\n\n"
                f"🗑️ Cleared all stored reaction data\n"
                f"🔄 Fresh analysis will start from new reactions\n\n"
                f"Use `/groupmood` to see the current (empty) state."
            )

        except Exception as e:
            logger.error(f"Error resetting group mood for chat {chat_id}: {e}")
            await message.reply_text("❌ Error resetting group mood data.")

    async def _rebuild_profiles_from_history(self, chat_id: int, message) -> None:
        """Rebuild all user profiles using full chat message history."""
        try:
            from utils.context_extractor import message_history
            from utils.profile_manager import profile_manager
            from ai_providers import create_provider

            # Get all messages from this chat's history
            all_messages = message_history.get_all_messages_for_chat(chat_id)

            if not all_messages:
                await message.reply_text("❌ No message history available for this chat.")
                return

            await message.reply_text(
                f"🔄 Starting profile rebuild using {len(all_messages)} messages from chat history...\n\n"
                f"This may take a few moments."
            )

            # Get AI provider for profile enrichment
            ai_provider = create_provider(
                provider_type=config.ai_provider,
                api_key=config.api_key,
                model=config.model_name,
                base_url=config.base_url
            )

            # Group messages by user
            messages_by_user = {}
            for msg in all_messages:
                user_id = msg.get('from', {}).get('id')
                if user_id:
                    if user_id not in messages_by_user:
                        messages_by_user[user_id] = []
                    messages_by_user[user_id].append(msg)

            # Rebuild profiles for each user
            rebuilt_count = 0
            for user_id, user_messages in messages_by_user.items():
                try:
                    # Convert messages to text for AI analysis
                    message_texts = []
                    for msg in user_messages[-50:]:  # Use last 50 messages for analysis
                        if 'text' in msg and msg['text']:
                            # Include sender info for context
                            sender_name = msg.get('from', {}).get('first_name', 'User')
                            message_texts.append(f"{sender_name}: {msg['text']}")

                    if message_texts:
                        message_history_text = "\n".join(message_texts)

                        # Enrich profile with AI
                        await profile_manager.enrich_profile_with_ai(
                            user_id=user_id,
                            recent_messages=message_history_text,
                            ai_analyzer=ai_provider
                        )

                        rebuilt_count += 1

                except Exception as e:
                    logger.warning(f"Failed to rebuild profile for user {user_id}: {e}")

            # Save all updated profiles
            profile_manager.save_all_profiles()

            await message.reply_text(
                f"✅ Profile rebuild completed!\n\n"
                f"👥 Rebuilt profiles for {rebuilt_count} users\n"
                f"📊 Used {len(all_messages)} messages from chat history\n"
                f"💾 All profile data saved to disk"
            )

            logger.info(f"Rebuilt {rebuilt_count} profiles using full chat history for chat {chat_id}")

        except Exception as e:
            logger.error(f"Error rebuilding profiles for chat {chat_id}: {e}")
            await message.reply_text("❌ Error rebuilding profiles from chat history.")


# Create and register the command instance
groupmood_command = GroupMoodCommand()


# Legacy function for backward compatibility during transition
async def handle_groupmood_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await groupmood_command.execute(update, context)
