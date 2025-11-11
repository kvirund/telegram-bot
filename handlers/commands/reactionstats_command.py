"""Reaction statistics command handler."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import get_config
from utils.reaction_analytics import reaction_analytics
from .base import Command

logger = logging.getLogger(__name__)
config = get_config()


class ReactionStatsCommand(Command):
    """ReactionStats command for viewing user reaction patterns.

    Usage: /reactionstats @username or /reactionstats (for self)
    """

    def __init__(self):
        super().__init__(name="reactionstats", description="Show user's reaction patterns", admin_only=False, description_ru="Показать паттерны реакций пользователя")

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reactionstats command to show user's reaction patterns.

        Usage: /reactionstats @username or /reactionstats (for self)
        """
        if not update.message or not update.message.from_user:
            return

        chat_id = update.message.chat_id
        requesting_user = update.message.from_user

        # Parse target user
        args = context.args or []
        target_user_id = None
        target_username = None

        if args:
            # Try to find user by username in the current chat
            username = args[0].lstrip("@")

            try:
                # Get chat member to resolve username to user ID
                chat_member = await update.message.chat.get_member(username=username)
                if chat_member and chat_member.user:
                    target_user_id = chat_member.user.id
                    target_username = chat_member.user.username or chat_member.user.first_name
                else:
                    await update.message.reply_text(f"❌ Пользователь @{username} не найден в этом чате.")
                    return
            except Exception as e:
                logger.error(f"Error looking up user @{username}: {e}")
                await update.message.reply_text(f"❌ Не удалось найти пользователя @{username} в этом чате.")
                return
        else:
            # Default to command sender
            target_user_id = requesting_user.id
            target_username = requesting_user.username or requesting_user.first_name

        try:
            # Get reaction statistics for the target user
            stats = reaction_analytics.get_user_reaction_stats(target_user_id)

            # Build response message
            if target_user_id == requesting_user.id:
                stats_message = f"📊 Ваша статистика реакций\n\n"
            else:
                stats_message = f"📊 Статистика реакций для {target_username}\n\n"

            # Total reactions
            stats_message += f"🔢 Всего реакций: {stats['total_reactions']}\n"
            stats_message += f"📈 Частота реакций: {stats['reaction_rate']} на сообщение\n\n"

            # Favorite reactions
            if stats["favorite_reactions"]:
                stats_message += f"❤️ Любимые реакции:\n"
                for emoji, count in stats["favorite_reactions"][:3]:  # Top 3
                    percentage = (count / stats["total_reactions"]) * 100 if stats["total_reactions"] > 0 else 0
                    stats_message += f"  {emoji} {count} раз ({percentage:.1f}%)\n"
                stats_message += "\n"
            else:
                stats_message += "❤️ Любимые реакции: Пока нет\n\n"

            # Emotional distribution
            if stats["emotional_distribution"]:
                stats_message += f"😊 Эмоциональное распределение:\n"
                for emotion, percentage in stats["emotional_distribution"].items():
                    emoji_map = {"positive": "😀", "negative": "😞", "neutral": "😐", "thoughtful": "🤔"}
                    emoji = emoji_map.get(emotion, "❓")
                    stats_message += f"  {emoji} {emotion.title()}: {percentage}%\n"
                stats_message += "\n"
            else:
                stats_message += "😊 Эмоциональное распределение: Данных пока нет\n\n"

            # Reaction targets
            if stats["reaction_targets"]:
                stats_message += f"🎯 Типы контента с реакциями:\n"
                for target, percentage in stats["reaction_targets"].items():
                    stats_message += f"  • {target.title()}: {percentage}%\n"
                stats_message += "\n"
            else:
                stats_message += "🎯 Типы контента с реакциями: Данных пока нет\n\n"

            # Personality insights
            if stats["personality_insights"]:
                stats_message += f"🔍 Анализ личности:\n"
                for insight in stats["personality_insights"][:3]:  # Top 3 insights
                    stats_message += f"  • {insight}\n"
            else:
                stats_message += "🔍 Анализ личности: Анализируем...\n"

            await update.message.reply_text(stats_message)

        except Exception as e:
            logger.error(f"Error in reactionstats command: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики реакций.")


# Create and register the command instance
reactionstats_command = ReactionStatsCommand()


# Legacy function for backward compatibility during transition
async def handle_reactionstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Legacy function for backward compatibility."""
    await reactionstats_command.execute(update, context)
