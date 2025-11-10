"""Shared pytest fixtures and configuration for all tests."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass

from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes


@dataclass
class MockConfig:
    """Mock configuration for testing."""

    telegram_token: str = "test_token_123"
    bot_username: str = "@testbot"
    ai_provider: str = "local"
    api_key: str = "test_key"
    model_name: str = "test_model"
    context_messages_count: int = 5
    admin_user_ids: list = None

    def __post_init__(self):
        if self.admin_user_ids is None:
            self.admin_user_ids = [123456789]


@pytest.fixture
def mock_config():
    """Provide a mock configuration for tests."""
    return MockConfig()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_ai_provider():
    """Mock AI provider for testing."""
    provider = MagicMock()
    provider.generate_joke = AsyncMock(return_value="Test joke response")
    provider.free_request = AsyncMock(return_value="Test AI response")
    provider.get_provider_name = MagicMock(return_value="MockProvider")
    return provider


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user."""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_bot = False
    return user


@pytest.fixture
def mock_telegram_chat():
    """Create a mock Telegram chat."""
    chat = MagicMock(spec=Chat)
    chat.id = -1001234567890
    chat.type = "group"
    chat.title = "Test Group"
    return chat


@pytest.fixture
def mock_telegram_message(mock_telegram_user, mock_telegram_chat):
    """Create a mock Telegram message."""
    message = MagicMock(spec=Message)
    message.message_id = 123
    message.from_user = mock_telegram_user
    message.chat = mock_telegram_chat
    message.chat_id = mock_telegram_chat.id
    message.text = "Test message"
    message.date = None
    return message


@pytest.fixture
def mock_telegram_update(mock_telegram_message):
    """Create a mock Telegram update."""
    update = MagicMock(spec=Update)
    update.update_id = 1
    update.message = mock_telegram_message
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    bot = MagicMock()
    bot.id = 987654321
    context.bot = bot
    return context


# Remove custom event_loop fixture to let pytest-asyncio handle it


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state here
    from config import _config
    import sys

    # Clear config singleton
    if "config" in sys.modules:
        config_module = sys.modules["config"]
        if hasattr(config_module, "_config"):
            config_module._config = None

    yield

    # Cleanup after test
    pass
