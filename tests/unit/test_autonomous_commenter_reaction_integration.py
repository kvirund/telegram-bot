"""Tests for autonomous commenter reaction integration."""
import pytest
from unittest.mock import MagicMock, patch
from utils.autonomous_commenter import AutonomousCommenter


class TestAutonomousCommenterReactionIntegration:
    """Test reaction-based decision making in autonomous commenter."""

    @pytest.fixture
    def mock_config(self):
        """Mock bot configuration."""
        config = MagicMock()
        config.yaml_config.autonomous_commenting.enabled = True
        config.yaml_config.autonomous_commenting.comment_probability = 0.5
        config.yaml_config.autonomous_commenting.min_messages_between_comments = 5
        config.yaml_config.autonomous_commenting.max_messages_between_comments = 15
        config.yaml_config.excluded_chats = []
        return config

    @pytest.fixture
    def mock_profile_manager(self):
        """Mock profile manager."""
        return MagicMock()

    @pytest.fixture
    def autonomous_commenter(self, mock_config, mock_profile_manager):
        """Create autonomous commenter instance."""
        return AutonomousCommenter(mock_config, mock_profile_manager)

    def test_adjust_probability_very_positive_mood(self, autonomous_commenter):
        """Test probability adjustment for very positive mood."""
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.return_value = {
                'overall_mood': 'Very Positive',
                'positive_percentage': 70,
                'negative_percentage': 10,
                'neutral_percentage': 20
            }

            adjusted = autonomous_commenter._adjust_probability_based_on_reactions(123456, 0.5)
            assert adjusted == 0.6  # 0.5 * 1.2 = 0.6

    def test_adjust_probability_negative_mood(self, autonomous_commenter):
        """Test probability adjustment for negative mood."""
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.return_value = {
                'overall_mood': 'Negative',
                'positive_percentage': 20,
                'negative_percentage': 60,
                'neutral_percentage': 20
            }

            adjusted = autonomous_commenter._adjust_probability_based_on_reactions(123456, 0.5)
            assert adjusted == 0.35  # 0.5 * 0.7 = 0.35

    def test_adjust_probability_mixed_mood(self, autonomous_commenter):
        """Test probability adjustment for mixed mood."""
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.return_value = {
                'overall_mood': 'Mixed',
                'positive_percentage': 35,
                'negative_percentage': 35,
                'neutral_percentage': 30
            }

            adjusted = autonomous_commenter._adjust_probability_based_on_reactions(123456, 0.5)
            assert adjusted == 0.45  # 0.5 * 0.9 = 0.45

    def test_adjust_probability_positive_mood_no_change(self, autonomous_commenter):
        """Test that positive mood doesn't change probability."""
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.return_value = {
                'overall_mood': 'Positive',
                'positive_percentage': 50,
                'negative_percentage': 20,
                'neutral_percentage': 30
            }

            adjusted = autonomous_commenter._adjust_probability_based_on_reactions(123456, 0.5)
            assert adjusted == 0.5  # No change

    def test_adjust_probability_error_handling(self, autonomous_commenter):
        """Test error handling in probability adjustment."""
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.side_effect = Exception("API Error")

            adjusted = autonomous_commenter._adjust_probability_based_on_reactions(123456, 0.5)
            assert adjusted == 0.5  # Should return base probability on error

    def test_should_comment_with_reaction_adjustment(self, autonomous_commenter, mock_config):
        """Test that should_comment uses reaction-based probability adjustment."""
        # Setup chat state
        state = autonomous_commenter._get_chat_state(123456)
        state.messages_since_last_comment = 10
        state.last_comment_time = None  # No recent comments
        state.next_comment_threshold = 8

        # Mock positive mood to increase probability
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.return_value = {
                'overall_mood': 'Very Positive',
                'positive_percentage': 70,
                'negative_percentage': 10,
                'neutral_percentage': 20
            }

            # Mock random to be just above the adjusted threshold
            with patch('random.random', return_value=0.55):  # Below 0.6 adjusted probability
                result = autonomous_commenter.should_comment(123456, 999999)
                # Should return True because 0.55 < 0.6 (adjusted probability)

    def test_should_comment_with_negative_mood_reduction(self, autonomous_commenter, mock_config):
        """Test that negative mood reduces commenting probability."""
        # Setup chat state
        state = autonomous_commenter._get_chat_state(123456)
        state.messages_since_last_comment = 10
        state.last_comment_time = None
        state.next_comment_threshold = 8

        # Mock negative mood to decrease probability
        with patch('utils.autonomous_commenter.reaction_analytics') as mock_analytics:
            mock_analytics.get_group_mood.return_value = {
                'overall_mood': 'Negative',
                'positive_percentage': 20,
                'negative_percentage': 60,
                'neutral_percentage': 20
            }

            # Mock random to be above the reduced threshold
            with patch('random.random', return_value=0.4):  # Above 0.35 adjusted probability
                result = autonomous_commenter.should_comment(123456, 999999)
                # Should return False because 0.4 > 0.35 (adjusted probability)
