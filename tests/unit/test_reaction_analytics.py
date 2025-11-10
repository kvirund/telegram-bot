"""Unit tests for reaction analytics functionality."""

import pytest
from unittest.mock import MagicMock, patch
from utils.reaction_analytics import ReactionAnalytics


class TestReactionAnalytics:
    """Test cases for ReactionAnalytics class."""

    @pytest.fixture
    def mock_profile_manager(self):
        """Mock profile manager for testing."""
        mock_pm = MagicMock()
        mock_profile = MagicMock()
        mock_profile.reaction_patterns.total_reactions = 10
        mock_profile.reaction_patterns.favorite_reactions = {"👍": 5, "😂": 3, "❤️": 2}
        mock_profile.reaction_patterns.emotional_responses = {"positive": 7, "neutral": 2, "negative": 1}
        mock_profile.reaction_patterns.reaction_targets = ["humor", "humor", "questions"]
        mock_profile.message_count = 50
        mock_pm.load_profile.return_value = mock_profile
        return mock_pm

    @pytest.fixture
    def reaction_analytics(self, mock_profile_manager):
        """Create ReactionAnalytics instance with mocked dependencies."""
        return ReactionAnalytics(mock_profile_manager)

    def test_initialization(self):
        """Test ReactionAnalytics initialization."""
        analytics = ReactionAnalytics()
        assert analytics is not None
        assert hasattr(analytics, "profile_manager")

    def test_get_group_mood_no_reactions(self, reaction_analytics):
        """Test group mood analysis when no reactions exist."""
        with patch.object(reaction_analytics, "_get_recent_reactions", return_value=[]):
            mood_data = reaction_analytics.get_group_mood(123456)

            assert mood_data["overall_mood"] == "Unknown"
            assert mood_data["active_users"] == 0
            assert mood_data["recent_reactions"] == 0
            assert "No recent reactions" in mood_data["message"]

    def test_get_group_mood_with_reactions(self, reaction_analytics):
        """Test group mood analysis with reaction data."""
        mock_reactions = [
            {"user_id": 1, "emoji": "👍", "timestamp": "now"},
            {"user_id": 2, "emoji": "😂", "timestamp": "now"},
            {"user_id": 1, "emoji": "❤️", "timestamp": "now"},
        ]

        with patch.object(reaction_analytics, "_get_recent_reactions", return_value=mock_reactions):
            mood_data = reaction_analytics.get_group_mood(123456)

            assert mood_data["overall_mood"] in ["Very Positive", "Positive", "Neutral", "Negative", "Mixed"]
            assert mood_data["active_users"] == 2  # 2 unique users
            assert mood_data["recent_reactions"] == 3
            assert mood_data["positive_percentage"] >= 0
            assert mood_data["negative_percentage"] >= 0
            assert mood_data["neutral_percentage"] >= 0

    def test_get_user_reaction_stats_no_data(self, reaction_analytics, mock_profile_manager):
        """Test user stats when user has no reactions."""
        mock_profile = MagicMock()
        mock_profile.reaction_patterns.total_reactions = 0
        mock_profile_manager.load_profile.return_value = mock_profile

        stats = reaction_analytics.get_user_reaction_stats(123456)

        assert stats["total_reactions"] == 0
        assert stats["favorite_reactions"] == []
        assert "No reaction data available" in stats["personality_insights"][0]

    def test_get_user_reaction_stats_with_data(self, reaction_analytics, mock_profile_manager):
        """Test user stats with reaction data."""
        # Using the mock profile from fixture
        stats = reaction_analytics.get_user_reaction_stats(123456)

        assert stats["total_reactions"] == 10
        assert len(stats["favorite_reactions"]) > 0
        assert stats["reaction_rate"] == 0.2  # 10 reactions / 50 messages
        assert "positive" in stats["emotional_distribution"]
        assert isinstance(stats["personality_insights"], list)

    def test_classify_emoji_sentiment(self, reaction_analytics):
        """Test emoji sentiment classification."""
        assert reaction_analytics._classify_emoji_sentiment("👍") == "positive"
        assert reaction_analytics._classify_emoji_sentiment("❤️") == "positive"
        assert reaction_analytics._classify_emoji_sentiment("😂") == "positive"
        assert reaction_analytics._classify_emoji_sentiment("😠") == "negative"
        assert reaction_analytics._classify_emoji_sentiment("❌") == "negative"
        assert reaction_analytics._classify_emoji_sentiment("😐") == "neutral"
        assert reaction_analytics._classify_emoji_sentiment("🤔") == "neutral"
        assert reaction_analytics._classify_emoji_sentiment("unknown") == "neutral"

    def test_determine_overall_mood(self, reaction_analytics):
        """Test overall mood determination logic."""
        assert reaction_analytics._determine_overall_mood(70, 10, 20) == "Very Positive"
        assert reaction_analytics._determine_overall_mood(50, 20, 30) == "Positive"
        assert reaction_analytics._determine_overall_mood(30, 50, 20) == "Negative"
        assert reaction_analytics._determine_overall_mood(30, 30, 40) == "Mixed"
        assert reaction_analytics._determine_overall_mood(20, 20, 60) == "Neutral"

    def test_analyze_reaction_personality(self, reaction_analytics):
        """Test personality analysis from reaction patterns."""
        mock_patterns = MagicMock()
        mock_patterns.favorite_reactions = {"😂": 5, "👍": 3}
        mock_patterns.emotional_responses = {"positive": 8, "negative": 2}
        mock_patterns.reaction_targets = ["humor", "humor", "questions"]

        insights = reaction_analytics._analyze_reaction_personality(mock_patterns)

        assert isinstance(insights, list)
        assert len(insights) > 0
        # Should contain insights about humor appreciation
        humor_insights = [i for i in insights if "humor" in i.lower()]
        assert len(humor_insights) > 0

    def test_calculate_reaction_rate(self, reaction_analytics, mock_profile_manager):
        """Test reaction rate calculation."""
        # Test normal case
        rate = reaction_analytics._calculate_reaction_rate(123456)
        assert rate == 0.2  # 10 reactions / 50 messages

        # Test zero messages (should return 0)
        mock_profile = MagicMock()
        mock_profile.message_count = 0
        mock_profile_manager.load_profile.return_value = mock_profile

        rate = reaction_analytics._calculate_reaction_rate(999999)
        assert rate == 0.0

    def test_get_reaction_effectiveness_placeholder(self, reaction_analytics):
        """Test reaction effectiveness method (currently placeholder)."""
        result = reaction_analytics.get_reaction_effectiveness(123456)

        assert "bot_reactions_sent" in result
        assert "average_response_time" in result
        assert "engagement_rate" in result
        assert "top_performing_emojis" in result
        assert "insights" in result
        assert "not yet implemented" in result["insights"][0].lower()
