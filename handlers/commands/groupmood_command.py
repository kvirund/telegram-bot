"""Group mood command handler - Public command to show current group sentiment."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils.reaction_analytics import reaction_analytics
from .base import Command

logger = logging.getLogger(__name__)


class GroupMoodCommand(Command):
    """GroupMood command for showing current group sentiment.

    Public command that displays current group mood analysis.
    Shows positive/neutral/negative percentages and active users.
    """

    def __init__(self):
        super().__init__(
            name="groupmood",
            description="Show current group sentiment analysis",
            admin_only=False,
            description_ru="Показать текущий анализ настроения группы"
        )

    def _get_raw_help_text(self, language: str = "en") -> str:
        """Get raw help text for the groupmood command."""
        help_lines = [
            f"{self.command_name} - {self.description}",
            "",
            "USAGE:",
            "/groupmood",
            "",
            "DESCRIPTION:",
            "Displays current group sentiment analysis showing:",
            "• Overall mood (positive/neutral/negative)",
            "• Sentiment distribution percentages",
            "• Number of active users",
            "• Recent reaction count",
            "",
            "This is a public command - no admin privileges required."
        ]

        return "\n".join(help_lines)

    def can_execute(self, user_id: int, config) -> bool:
        """Check if user can execute this command - public command."""
        return True

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /groupmood command - show current group mood."""
        if not update.message:
            return

        message = update.message
        chat_id = message.chat_id

        try:
            await self._show_group_mood(chat_id, message)
        except Exception as e:
            logger.error(f"Error in groupmood command: {e}")
            await message.reply_text("❌ Ошибка анализа настроения группы.")

    async def _show_group_mood(self, chat_id: int, message) -> None:
        """Show current group mood analysis."""
        # Get group mood analysis
        mood_data = reaction_analytics.get_group_mood(chat_id)

        mood_message = "😊 Анализ настроения группы\n\n"
        mood_message += f"📍 Текущее настроение: {mood_data['overall_mood'].title()}\n\n"
        mood_message += "📊 Распределение настроений:\n"
        mood_message += f"😀 Положительное: {mood_data['positive_percentage']}%\n"
        mood_message += f"😐 Нейтральное: {mood_data['neutral_percentage']}%\n"
        mood_message += f"😞 Отрицательное: {mood_data['negative_percentage']}%\n\n"
        mood_message += f"👥 Активные пользователи: {mood_data['active_users']}\n"
        mood_message += f"💬 Недавние реакции: {mood_data['recent_reactions']}\n\n"
        mood_message += f"💡 {mood_data['message']}"

        await message.reply_text(mood_message)


# Create and register the command instance
groupmood_command = GroupMoodCommand()


# Legacy function for backward compatibility during transition
async def handle_groupmood_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await groupmood_command.execute(update, context)
