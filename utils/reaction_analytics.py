"""Reaction analytics and reporting utilities."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from config import get_config
from utils.profile_manager import profile_manager

logger = logging.getLogger(__name__)
config = get_config()


class ReactionAnalytics:
    """Analytics engine for reaction data and sentiment analysis."""

    def __init__(self, profile_manager_instance=None):
        """Initialize reaction analytics.

        Args:
            profile_manager_instance: Profile manager instance (optional, uses global if None)
        """
        self.profile_manager = profile_manager_instance or profile_manager
        logger.info("ReactionAnalytics initialized")

    def get_group_mood(self, chat_id: int) -> Dict[str, Any]:
        """Analyze current group sentiment based on recent reactions.

        Args:
            chat_id: Chat ID to analyze

        Returns:
            Dict with mood analysis data
        """
        try:
            # Get recent reactions from all users in this chat
            recent_reactions = self._get_recent_reactions(chat_id, hours=24)

            if not recent_reactions:
                return self._get_empty_mood_data("No recent reactions to analyze")

            # Analyze sentiment distribution
            sentiment_counts = Counter()
            total_reactions = len(recent_reactions)

            for reaction_data in recent_reactions:
                emoji = reaction_data["emoji"]
                sentiment = self._classify_emoji_sentiment(emoji)
                sentiment_counts[sentiment] += 1

            # Calculate percentages
            positive_pct = (sentiment_counts["positive"] / total_reactions) * 100
            negative_pct = (sentiment_counts["negative"] / total_reactions) * 100
            neutral_pct = (sentiment_counts["neutral"] / total_reactions) * 100

            # Determine overall mood
            overall_mood = self._determine_overall_mood(positive_pct, negative_pct, neutral_pct)

            # Get active users count (users who reacted in last 24h)
            active_users = len(set(r["user_id"] for r in recent_reactions))

            # Generate insight message
            message = self._generate_mood_insight(overall_mood, positive_pct, negative_pct, total_reactions)

            return {
                "overall_mood": overall_mood,
                "positive_percentage": round(positive_pct, 1),
                "negative_percentage": round(negative_pct, 1),
                "neutral_percentage": round(neutral_pct, 1),
                "active_users": active_users,
                "recent_reactions": total_reactions,
                "message": message,
            }

        except Exception as e:
            logger.error(f"Error analyzing group mood for chat {chat_id}: {e}")
            return self._get_empty_mood_data("Error analyzing mood")

    def get_user_reaction_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive reaction statistics for a user.

        Args:
            user_id: User ID to analyze

        Returns:
            Dict with user reaction statistics
        """
        try:
            profile = self.profile_manager.load_profile(user_id)
            patterns = profile.reaction_patterns

            if patterns.total_reactions == 0:
                return self._get_empty_user_stats()

            # Calculate favorite reactions (top 5)
            favorite_reactions = sorted(patterns.favorite_reactions.items(), key=lambda x: x[1], reverse=True)[:5]

            # Calculate emotional distribution
            emotional_dist = {}
            total_emotions = sum(patterns.emotional_responses.values())
            if total_emotions > 0:
                for emotion, count in patterns.emotional_responses.items():
                    emotional_dist[emotion] = round((count / total_emotions) * 100, 1)

            # Calculate reaction targets distribution
            target_dist = {}
            if patterns.reaction_targets:
                target_counter = Counter(patterns.reaction_targets)
                total_targets = sum(target_counter.values())
                for target, count in target_counter.most_common():
                    target_dist[target] = round((count / total_targets) * 100, 1)

            # Generate personality insights
            personality_insights = self._analyze_reaction_personality(patterns)

            return {
                "total_reactions": patterns.total_reactions,
                "favorite_reactions": favorite_reactions,
                "emotional_distribution": emotional_dist,
                "reaction_targets": target_dist,
                "personality_insights": personality_insights,
                "reaction_rate": self._calculate_reaction_rate(user_id),
            }

        except Exception as e:
            logger.error(f"Error getting reaction stats for user {user_id}: {e}")
            return self._get_empty_user_stats()

    def get_reaction_effectiveness(self, chat_id: int) -> Dict[str, Any]:
        """Analyze how effective bot's reactions are in the group.

        Args:
            chat_id: Chat ID to analyze

        Returns:
            Dict with reaction effectiveness data
        """
        try:
            # This would analyze bot's reaction patterns and responses
            # For now, return placeholder data
            return {
                "bot_reactions_sent": 0,
                "average_response_time": 0,
                "engagement_rate": 0,
                "top_performing_emojis": [],
                "insights": ["Reaction effectiveness tracking not yet implemented"],
            }

        except Exception as e:
            logger.error(f"Error analyzing reaction effectiveness for chat {chat_id}: {e}")
            return {
                "bot_reactions_sent": 0,
                "average_response_time": 0,
                "engagement_rate": 0,
                "top_performing_emojis": [],
                "insights": ["Error analyzing effectiveness"],
            }

    def _get_recent_reactions(self, chat_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent reactions from users in a chat.

        Args:
            chat_id: Chat ID
            hours: Hours to look back

        Returns:
            List of recent reaction data
        """
        try:
            # Get real reaction data from profile manager
            return self.profile_manager.get_recent_chat_reactions(chat_id, hours)
        except Exception as e:
            logger.error(f"Error getting recent reactions for chat {chat_id}: {e}")
            return []

    def _classify_emoji_sentiment(self, emoji: str) -> str:
        """Classify emoji sentiment.

        Args:
            emoji: Emoji to classify

        Returns:
            str: 'positive', 'negative', or 'neutral'
        """
        positive_emojis = {"👍", "❤️", "🔥", "😊", "😂", "🎉", "✅", "💯", "😄", "😍", "🥰", "🤗"}
        negative_emojis = {"👎", "😠", "😢", "💔", "❌", "😞", "😔", "😕", "😣", "😖"}

        if emoji in positive_emojis:
            return "positive"
        elif emoji in negative_emojis:
            return "negative"
        else:
            return "neutral"

    def _determine_overall_mood(self, positive_pct: float, negative_pct: float, neutral_pct: float) -> str:
        """Determine overall group mood.

        Args:
            positive_pct: Percentage of positive reactions
            negative_pct: Percentage of negative reactions
            neutral_pct: Percentage of neutral reactions

        Returns:
            str: Overall mood description
        """
        if positive_pct > 60:
            return "Very Positive"
        elif positive_pct > 40:
            return "Positive"
        elif negative_pct > 40:
            return "Negative"
        elif positive_pct > 25:
            return "Mixed"
        else:
            return "Neutral"

    def _generate_mood_insight(self, mood: str, positive_pct: float, negative_pct: float, total: int) -> str:
        """Generate human-readable mood insight.

        Args:
            mood: Overall mood
            positive_pct: Positive percentage
            negative_pct: Negative percentage
            total: Total reactions

        Returns:
            str: Insight message
        """
        if mood == "Very Positive":
            return f"🎉 The group is in great spirits with {positive_pct:.1f}% positive reactions!"
        elif mood == "Positive":
            return f"😊 The mood is generally positive with {positive_pct:.1f}% positive reactions."
        elif mood == "Negative":
            return f"😞 The group seems down with {negative_pct:.1f}% negative reactions."
        elif mood == "Mixed":
            return f"😐 Mixed feelings in the group - {positive_pct:.1f}% positive, {negative_pct:.1f}% negative."
        else:
            return f"🤔 Neutral mood overall from {total} recent reactions."

    def _get_empty_mood_data(self, message: str) -> Dict[str, Any]:
        """Get empty mood data structure.

        Args:
            message: Message to include

        Returns:
            Dict with empty mood data
        """
        return {
            "overall_mood": "Unknown",
            "positive_percentage": 0.0,
            "negative_percentage": 0.0,
            "neutral_percentage": 0.0,
            "active_users": 0,
            "recent_reactions": 0,
            "message": message,
        }

    def _get_empty_user_stats(self) -> Dict[str, Any]:
        """Get empty user stats structure.

        Returns:
            Dict with empty user statistics
        """
        return {
            "total_reactions": 0,
            "favorite_reactions": [],
            "emotional_distribution": {},
            "reaction_targets": {},
            "personality_insights": ["No reaction data available"],
            "reaction_rate": 0.0,
        }

    def _analyze_reaction_personality(self, patterns) -> List[str]:
        """Analyze user's reaction personality.

        Args:
            patterns: ReactionPatterns object

        Returns:
            List of personality insights
        """
        insights = []

        # Analyze favorite reactions
        if patterns.favorite_reactions:
            top_emoji = max(patterns.favorite_reactions.items(), key=lambda x: x[1])[0]
            if top_emoji in ["😂", "😄", "🤣"]:
                insights.append("Has a great sense of humor and appreciates jokes")
            elif top_emoji in ["❤️", "🥰", "😍"]:
                insights.append("Very affectionate and shows appreciation often")
            elif top_emoji in ["👍", "✅", "💯"]:
                insights.append("Supportive and encouraging of others")
            elif top_emoji in ["🤔", "💭", "🧐"]:
                insights.append("Thoughtful and contemplative")

        # Analyze emotional distribution
        if patterns.emotional_responses:
            positive_count = patterns.emotional_responses.get("positive", 0)
            negative_count = patterns.emotional_responses.get("negative", 0)
            thoughtful_count = patterns.emotional_responses.get("thoughtful", 0)

            total = positive_count + negative_count + thoughtful_count
            if total > 0:
                if positive_count / total > 0.7:
                    insights.append("Overwhelmingly positive and upbeat")
                elif thoughtful_count / total > 0.4:
                    insights.append("Tends to think deeply about content")

        # Analyze reaction targets
        if "humor" in patterns.reaction_targets:
            insights.append("Really enjoys humorous content")
        if "questions" in patterns.reaction_targets:
            insights.append("Engages with thoughtful questions")

        if not insights:
            insights.append("Reaction patterns still developing")

        return insights

    def _calculate_reaction_rate(self, user_id: int) -> float:
        """Calculate user's reaction rate (reactions per message).

        Args:
            user_id: User ID

        Returns:
            float: Reactions per message ratio
        """
        try:
            profile = self.profile_manager.load_profile(user_id)
            if profile.message_count == 0:
                return 0.0

            return round(profile.reaction_patterns.total_reactions / profile.message_count, 2)
        except Exception:
            return 0.0


# Global reaction analytics instance
reaction_analytics = ReactionAnalytics()
