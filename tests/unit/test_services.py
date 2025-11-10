"""Unit tests for service classes."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from services.bot_service import BotService
from services.profile_regeneration_service import ProfileRegenerationService


class TestBotService:
    """Test the BotService class."""

    @pytest.fixture
    def bot_service(self):
        """Create a BotService instance."""
        with patch("services.bot_service.get_config"):
            service = BotService()
            return service

    @pytest.mark.asyncio
    async def test_initialization(self, bot_service):
        """Test bot service initialization."""
        with patch("services.bot_service.Application.builder") as mock_builder:
            mock_app = Mock()
            mock_builder.return_value.token.return_value.post_init.return_value.build.return_value = mock_app

            app = await bot_service.initialize()

            assert bot_service.app == mock_app
            assert app == mock_app
            mock_builder.assert_called_once()

    def test_register_handlers(self, bot_service):
        """Test handler registration."""
        mock_app = Mock()
        bot_service.app = mock_app

        bot_service._register_handlers()

        # Should have registered 3 handlers: 1 for text messages, 1 for reactions, 1 for help callbacks
        assert mock_app.add_handler.call_count == 3

    @pytest.mark.asyncio
    async def test_shutdown(self, bot_service):
        """Test bot service shutdown."""
        mock_app = AsyncMock()
        bot_service.app = mock_app

        with patch("services.bot_service.profile_manager") as mock_pm, patch(
            "services.bot_service.message_history"
        ) as mock_mh:

            mock_pm.save_all_profiles.return_value = 5

            await bot_service.shutdown()

            mock_pm.save_all_profiles.assert_called_once()
            mock_mh.save_all.assert_called_once()
            mock_app.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_without_app(self, bot_service):
        """Test running bot without initialized app."""
        with patch.object(bot_service, "run") as mock_run:
            # This should not raise any event loop errors
            bot_service.start()

            # Verify run was called
            mock_run.assert_called_once()

    def test_start_method_calls_run(self, bot_service):
        """Test that start() method calls run() without event loop conflicts."""
        with patch.object(bot_service, "run") as mock_run:
            # This should not raise any event loop errors
            bot_service.start()

            # Verify run was called
            mock_run.assert_called_once()


class TestProfileRegenerationService:
    """Test the ProfileRegenerationService class."""

    @pytest.fixture
    def regen_service(self):
        """Create a ProfileRegenerationService instance."""
        mock_config = Mock()
        mock_config.ai_provider = "groq"
        mock_config.api_key = "test_key"
        mock_config.model_name = "test_model"
        mock_config.base_url = "http://localhost:8000"

        with patch("services.profile_regeneration_service.get_config", return_value=mock_config):
            service = ProfileRegenerationService()
            return service

    @pytest.mark.asyncio
    async def test_regenerate_all_profiles_success(self, regen_service):
        """Test successful profile regeneration."""
        with patch("services.profile_regeneration_service.message_history") as mock_mh, patch(
            "services.profile_regeneration_service.profile_manager"
        ) as mock_pm, patch("services.profile_regeneration_service.create_provider") as mock_create_provider:

            # Mock message history - need at least 5 messages per user
            mock_mh.get_all_chat_ids.return_value = [123]
            mock_mh.get_recent_messages.return_value = [
                {
                    "user_id": 111,
                    "text": "Hello world 1",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 2",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 3",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 4",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 5",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 222,
                    "text": "Test message 1",
                    "username": "user2",
                    "first_name": "User",
                    "last_name": "Two",
                },
                {
                    "user_id": 222,
                    "text": "Test message 2",
                    "username": "user2",
                    "first_name": "User",
                    "last_name": "Two",
                },
                {
                    "user_id": 222,
                    "text": "Test message 3",
                    "username": "user2",
                    "first_name": "User",
                    "last_name": "Two",
                },
                {
                    "user_id": 222,
                    "text": "Test message 4",
                    "username": "user2",
                    "first_name": "User",
                    "last_name": "Two",
                },
                {
                    "user_id": 222,
                    "text": "Test message 5",
                    "username": "user2",
                    "first_name": "User",
                    "last_name": "Two",
                },
            ]

            # Mock AI provider
            mock_ai = AsyncMock()
            mock_ai.free_request.return_value = '{"interests": ["test"], "technical_weaknesses": [], "personal_weaknesses": [], "speaking_tone": "casual", "humor_type": "sarcastic", "common_mistakes": [], "embarrassing_moments": []}'
            mock_create_provider.return_value = mock_ai

            # Mock profile manager
            mock_profile = Mock()
            mock_pm.load_profile.return_value = mock_profile
            mock_pm.enrich_profile_with_ai = AsyncMock()
            mock_pm.save_profile = Mock()

            result = await regen_service.regenerate_all_profiles()

            assert result["processed"] == 2
            assert result["total"] == 2
            assert "message" not in result

    @pytest.mark.asyncio
    async def test_regenerate_all_profiles_no_messages(self, regen_service):
        """Test profile regeneration with no messages."""
        with patch("services.profile_regeneration_service.message_history") as mock_mh:
            mock_mh.get_all_chat_ids.return_value = []
            mock_mh.get_recent_messages.return_value = []

            result = await regen_service.regenerate_all_profiles()

            assert result["processed"] == 0
            assert result["total"] == 0
            assert result["message"] == "No user messages found"

    @pytest.mark.asyncio
    async def test_regenerate_all_profiles_ai_error(self, regen_service):
        """Test profile regeneration with AI errors."""
        with patch("services.profile_regeneration_service.message_history") as mock_mh, patch(
            "services.profile_regeneration_service.profile_manager"
        ) as mock_pm, patch("services.profile_regeneration_service.create_provider") as mock_create_provider:

            # Mock message history - need at least 5 messages
            mock_mh.get_all_chat_ids.return_value = [123]
            mock_mh.get_recent_messages.return_value = [
                {
                    "user_id": 111,
                    "text": "Hello world 1",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 2",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 3",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 4",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
                {
                    "user_id": 111,
                    "text": "Hello world 5",
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One",
                },
            ]

            # Mock AI provider that fails
            mock_ai = AsyncMock()
            mock_ai.free_request.side_effect = Exception("AI Error")
            mock_create_provider.return_value = mock_ai

            # Mock profile manager
            mock_profile = Mock()
            mock_pm.load_profile.return_value = mock_profile

            result = await regen_service.regenerate_all_profiles()

            assert result["processed"] == 0
            assert result["failed"] == 1
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_regenerate_all_profiles_skip_few_messages(self, regen_service):
        """Test skipping users with too few messages."""
        with patch("services.profile_regeneration_service.message_history") as mock_mh, patch(
            "services.profile_regeneration_service.profile_manager"
        ) as mock_pm, patch("services.profile_regeneration_service.create_provider") as mock_create_provider:

            # Mock message history with user having only 3 messages
            mock_mh.get_all_chat_ids.return_value = [123]
            mock_mh.get_recent_messages.return_value = [
                {"user_id": 111, "text": "Hi", "username": "user1", "first_name": "User", "last_name": "One"},
                {"user_id": 111, "text": "Hello", "username": "user1", "first_name": "User", "last_name": "One"},
                {"user_id": 111, "text": "Hey", "username": "user1", "first_name": "User", "last_name": "One"},
            ]

            # Mock AI provider
            mock_ai = AsyncMock()
            mock_create_provider.return_value = mock_ai

            # Mock profile manager
            mock_profile = Mock()
            mock_pm.load_profile.return_value = mock_profile

            result = await regen_service.regenerate_all_profiles()

            assert result["processed"] == 0
            assert result["skipped"] == 1
            assert result["total"] == 1

            # AI should not have been called
            mock_ai.free_request.assert_not_called()
