"""Unit tests for configuration management."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from config import BotConfig, load_yaml_config, get_config, reload_config


class TestBotConfig:
    """Test BotConfig dataclass."""

    def test_valid_config_creation(self, mock_config):
        """Test creating a valid BotConfig."""
        config = BotConfig(
            telegram_token=mock_config.telegram_token,
            bot_username=mock_config.bot_username,
            ai_provider=mock_config.ai_provider,
            api_key=mock_config.api_key,
            model_name=mock_config.model_name,
            context_messages_count=mock_config.context_messages_count,
            admin_user_ids=mock_config.admin_user_ids,
        )

        assert config.telegram_token == mock_config.telegram_token
        assert config.bot_username == mock_config.bot_username
        assert config.ai_provider == mock_config.ai_provider
        assert config.api_key == mock_config.api_key
        assert config.model_name == mock_config.model_name
        assert config.context_messages_count == mock_config.context_messages_count
        assert config.admin_user_ids == mock_config.admin_user_ids

    def test_config_validation_missing_token(self):
        """Test config validation fails with missing token."""
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is required"):
            BotConfig(
                telegram_token="",
                bot_username="@testbot",
                ai_provider="local",
                api_key="test_key",
                model_name="test_model",
            )

    def test_config_validation_missing_username(self):
        """Test config validation fails with missing username."""
        with pytest.raises(ValueError, match="BOT_USERNAME is required"):
            BotConfig(
                telegram_token="test_token",
                bot_username="",
                ai_provider="local",
                api_key="test_key",
                model_name="test_model",
            )

    def test_config_validation_invalid_provider(self):
        """Test config validation fails with invalid AI provider."""
        with pytest.raises(ValueError, match="AI_PROVIDER must be"):
            BotConfig(
                telegram_token="test_token",
                bot_username="@testbot",
                ai_provider="invalid_provider",
                api_key="test_key",
                model_name="test_model",
            )

    def test_config_validation_missing_api_key(self):
        """Test config validation fails with missing API key."""
        with pytest.raises(ValueError, match="API key for local is required"):
            BotConfig(
                telegram_token="test_token",
                bot_username="@testbot",
                ai_provider="local",
                api_key="",
                model_name="test_model",
            )

    def test_config_validation_missing_model(self):
        """Test config validation fails with missing model name."""
        with pytest.raises(ValueError, match="MODEL_NAME is required"):
            BotConfig(
                telegram_token="test_token",
                bot_username="@testbot",
                ai_provider="local",
                api_key="test_key",
                model_name="",
            )

    def test_config_validation_invalid_context_count(self):
        """Test config validation fails with invalid context count."""
        with pytest.raises(ValueError, match="CONTEXT_MESSAGES_COUNT must be at least 1"):
            BotConfig(
                telegram_token="test_token",
                bot_username="@testbot",
                ai_provider="local",
                api_key="test_key",
                model_name="test_model",
                context_messages_count=0,
            )

    def test_config_validation_invalid_retries(self):
        """Test config validation fails with invalid max retries."""
        with pytest.raises(ValueError, match="MAX_RETRIES must be at least 1"):
            BotConfig(
                telegram_token="test_token",
                bot_username="@testbot",
                ai_provider="local",
                api_key="test_key",
                model_name="test_model",
                max_retries=0,
            )


class TestYamlConfigLoading:
    """Test YAML configuration loading."""

    def test_load_yaml_config_missing_file(self):
        """Test loading config when file doesn't exist."""
        with patch("config.os.path.join", return_value="/nonexistent/config.yaml"):
            yaml_config = load_yaml_config()
            # Should return default config when file doesn't exist
            assert yaml_config.bot.telegram_token == ""
            assert yaml_config.bot.bot_username == ""
            assert yaml_config.ai.provider == "local"

    def test_load_yaml_config_valid_file(self, temp_dir):
        """Test loading valid YAML configuration."""
        config_content = """
bot:
  telegram_token: "test_token_123"
  bot_username: "@testbot"
  admin_user_ids: [123456789]

ai:
  provider: "local"
  context_messages_count: 10
  max_retries: 3
  local:
    api_key: "test_key"
    api_url: "http://localhost:11434/v1"
    model: "test_model"

autonomous_commenting:
  enabled: true
  roasting_enabled: true
  roasting_aggression: 0.7

user_profiling:
  enabled: true

conversation_monitoring:
  context_window_size: 15

reaction_system:
  enabled: true

system_prompts:
  joke_generation: "Test prompt"
  conversation: "Test conversation"
  autonomous_comment: "Test comment"
  ai_decision: "Test decision"
  mention_response: "Test mention"
"""

        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)

        with patch("config.os.path.dirname", return_value=str(temp_dir)):
            yaml_config = load_yaml_config()

            assert yaml_config.bot.telegram_token == "test_token_123"
            assert yaml_config.bot.bot_username == "@testbot"
            assert yaml_config.bot.admin_user_ids == [123456789]
            assert yaml_config.ai.provider == "local"
            assert yaml_config.ai.context_messages_count == 10
            assert yaml_config.autonomous_commenting.enabled is True
            assert yaml_config.autonomous_commenting.roasting_enabled is True
            assert yaml_config.autonomous_commenting.roasting_aggression == 0.7


class TestConfigSingleton:
    """Test configuration singleton behavior."""

    @patch("config.load_config")
    def test_get_config_singleton(self, mock_load_config, mock_config):
        """Test that get_config returns singleton instance."""
        from config import _config

        # Reset singleton
        import config

        config._config = None

        # Mock the load_config to return our mock config
        mock_config_obj = MagicMock()
        mock_config_obj.telegram_token = mock_config.telegram_token
        mock_config_obj.bot_username = mock_config.bot_username
        mock_load_config.return_value = mock_config_obj

        # First call should load config
        config1 = get_config()
        assert mock_load_config.call_count == 1

        # Second call should return cached instance
        config2 = get_config()
        assert mock_load_config.call_count == 1  # Should not be called again
        assert config1 is config2

    @patch("config.load_config")
    def test_reload_config(self, mock_load_config, mock_config):
        """Test that reload_config forces reload."""
        from config import _config

        # Reset singleton
        import config

        config._config = None

        # Mock the load_config to return different objects each time
        def mock_load_config_func():
            mock_config_obj = MagicMock()
            mock_config_obj.telegram_token = mock_config.telegram_token
            return mock_config_obj

        mock_load_config.side_effect = mock_load_config_func

        # First call
        config1 = get_config()
        assert mock_load_config.call_count == 1

        # Reload should force new load
        config2 = reload_config()
        assert mock_load_config.call_count == 2
        assert config1 is not config2
