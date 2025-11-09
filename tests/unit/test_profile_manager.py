"""Unit tests for profile management functionality."""
import json
import os
import tempfile
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from telegram import Message, User, Chat

from utils.profile_manager import (
    ProfileManager, UserProfile, SpeakingStyle, UserWeaknesses,
    UserPatterns, ReactionPatterns, RoastHistory
)


class TestUserProfile:
    """Test UserProfile dataclass."""

    def test_profile_creation(self):
        """Test creating a new user profile."""
        profile = UserProfile(user_id=12345, username="testuser", first_name="Test")
        assert profile.user_id == 12345
        assert profile.username == "testuser"
        assert profile.first_name == "Test"
        assert profile.message_count == 0
        assert profile.language_preference == "en"

    def test_profile_to_dict(self):
        """Test converting profile to dictionary."""
        profile = UserProfile(user_id=12345, first_name="Test")
        data = profile.to_dict()
        assert data["user_id"] == 12345
        assert data["first_name"] == "Test"
        assert isinstance(data["speaking_style"], dict)

    def test_profile_from_dict(self):
        """Test creating profile from dictionary."""
        data = {
            "user_id": 12345,
            "first_name": "Test",
            "speaking_style": {"tone": "casual"},
            "weaknesses": {"technical": [], "personal": []},
            "patterns": {"common_mistakes": []},
            "roast_history": {"successful_roasts": 0},
            "reaction_patterns": {"total_reactions": 0}
        }
        profile = UserProfile.from_dict(data)
        assert profile.user_id == 12345
        assert profile.first_name == "Test"
        assert profile.speaking_style.tone == "casual"


class TestProfileManager:
    """Test ProfileManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp:
            yield temp

    @pytest.fixture
    def profile_manager(self, temp_dir):
        """Create a ProfileManager instance with temp directory."""
        return ProfileManager(profile_directory=temp_dir)

    def test_initialization(self, profile_manager, temp_dir):
        """Test profile manager initialization."""
        assert profile_manager.profile_directory == temp_dir
        assert profile_manager.profiles == {}
        assert os.path.exists(os.path.join(temp_dir, "users"))
        assert os.path.exists(os.path.join(temp_dir, "chats"))

    def test_load_new_profile(self, profile_manager):
        """Test loading a new profile creates it."""
        profile = profile_manager.load_profile(12345)
        assert profile.user_id == 12345
        assert profile.message_count == 0
        assert profile.first_seen != ""
        assert 12345 in profile_manager.profiles

    def test_save_and_load_profile(self, profile_manager):
        """Test saving and loading profile from disk."""
        # Create and modify profile
        profile = profile_manager.load_profile(12345)
        profile.first_name = "Test User"
        profile.message_count = 5

        # Save profile
        assert profile_manager.save_profile(12345)

        # Clear cache and reload
        profile_manager.profiles.clear()
        loaded_profile = profile_manager.load_profile(12345)

        assert loaded_profile.first_name == "Test User"
        assert loaded_profile.message_count == 5

    def test_update_profile_from_message(self, profile_manager):
        """Test updating profile from Telegram message."""
        # Create mock message
        mock_user = Mock(spec=User)
        mock_user.id = 12345
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"

        mock_chat = Mock(spec=Chat)
        mock_chat.id = -1001234567890

        mock_message = Mock(spec=Message)
        mock_message.from_user = mock_user
        mock_message.chat_id = mock_chat.id
        mock_message.text = "Hello world"

        # Update profile
        profile_manager.update_profile_from_message(mock_message)

        # Check profile was updated
        profile = profile_manager.profiles[12345]
        assert profile.username == "testuser"
        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.message_count == 1
        assert mock_chat.id in profile.chats
        assert profile.language_preference == "en"  # English text

    def test_update_profile_russian_text(self, profile_manager):
        """Test language detection for Russian text."""
        mock_user = Mock(spec=User)
        mock_user.id = 12346
        mock_user.username = "russianuser"

        mock_message = Mock(spec=Message)
        mock_message.from_user = mock_user
        mock_message.chat_id = -1001234567890
        mock_message.text = "Привет мир"  # Russian text

        profile_manager.update_profile_from_message(mock_message)

        profile = profile_manager.profiles[12346]
        assert profile.language_preference == "ru"

    @pytest.mark.asyncio
    async def test_enrich_profile_with_ai(self, profile_manager):
        """Test AI profile enrichment."""
        # Mock AI provider
        mock_ai = AsyncMock()
        mock_ai.free_request.return_value = '''{
            "interests": ["programming", "gaming"],
            "technical_weaknesses": ["debugging"],
            "personal_weaknesses": ["procrastination"],
            "speaking_tone": "casual",
            "humor_type": "sarcastic",
            "common_mistakes": ["typos"],
            "embarrassing_moments": ["forgot password"]
        }'''

        # Enrich profile
        await profile_manager.enrich_profile_with_ai(12345, "test messages", mock_ai)

        profile = profile_manager.profiles[12345]
        assert "programming" in profile.interests
        assert "debugging" in profile.weaknesses.technical
        assert "procrastination" in profile.weaknesses.personal
        assert profile.speaking_style.tone == "casual"
        assert profile.humor_type == "sarcastic"
        assert "typos" in profile.patterns.common_mistakes
        assert "forgot password" in profile.embarrassing_moments

    @pytest.mark.asyncio
    async def test_enrich_profile_ai_error(self, profile_manager):
        """Test AI enrichment handles errors gracefully."""
        mock_ai = AsyncMock()
        mock_ai.free_request.side_effect = Exception("AI Error")

        # Should not raise exception
        await profile_manager.enrich_profile_with_ai(12345, "test messages", mock_ai)

        # Profile should still exist
        profile = profile_manager.profiles[12345]
        assert profile.user_id == 12345

    def test_get_profile_summary(self, profile_manager):
        """Test getting profile summary."""
        profile = profile_manager.load_profile(12345)
        profile.first_name = "Test"
        profile.username = "testuser"
        profile.message_count = 10
        profile.language_preference = "en"
        profile.interests = ["coding", "gaming"]
        profile.weaknesses.technical = ["debugging"]

        summary = profile_manager.get_profile_summary(12345)
        assert "Test" in summary
        assert "@testuser" in summary
        assert "10" in summary
        assert "coding" in summary

    def test_track_reaction(self, profile_manager):
        """Test tracking user reactions."""
        profile_manager.track_reaction(12345, "👍", "Great job!")

        profile = profile_manager.profiles[12345]
        assert profile.reaction_patterns.favorite_reactions["👍"] == 1
        assert profile.reaction_patterns.total_reactions == 1
        assert "positive" in profile.reaction_patterns.emotional_responses

    def test_track_reaction_humor_content(self, profile_manager):
        """Test reaction tracking categorizes humor content."""
        profile_manager.track_reaction(12345, "😂", "That was so funny!")

        profile = profile_manager.profiles[12345]
        assert "humor" in profile.reaction_patterns.reaction_targets

    def test_record_roast(self, profile_manager):
        """Test recording roast attempts."""
        profile_manager.record_roast(12345, "debugging", success=True)

        profile = profile_manager.profiles[12345]
        assert profile.roast_history.successful_roasts == 1
        assert "debugging" in profile.roast_history.topics_hit
        assert profile.roast_history.last_roasted is not None

    def test_save_all_profiles(self, profile_manager):
        """Test saving all profiles."""
        # Create multiple profiles
        profile_manager.load_profile(12345)
        profile_manager.load_profile(67890)

        saved_count = profile_manager.save_all_profiles()
        assert saved_count == 2

    def test_get_profile_size_kb(self, profile_manager):
        """Test getting profile file size."""
        profile = profile_manager.load_profile(12345)
        profile.first_name = "Test"
        profile_manager.save_profile(12345)

        size_kb = profile_manager.get_profile_size_kb(12345)
        assert size_kb > 0

    def test_get_profile_size_nonexistent(self, profile_manager):
        """Test getting size of nonexistent profile."""
        size_kb = profile_manager.get_profile_size_kb(99999)
        assert size_kb == 0.0
