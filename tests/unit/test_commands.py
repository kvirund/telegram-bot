"""Unit tests for command system functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from telegram import BotCommand

from handlers.commands.base import Command, FunctionCommand
from handlers.commands.registry import CommandRegistry


class MockCommand(Command):
    """Mock command for testing."""

    def __init__(self, name: str, description: str, description_ru: str = None):
        super().__init__(name, description, description_ru=description_ru)

    async def execute(self, update, context):
        """Mock execute method."""
        pass


class TestCommand:
    """Test cases for the Command base class."""

    def test_get_description_english_default(self):
        """Test get_description returns English when no Russian provided."""
        cmd = MockCommand("test", "Test command")
        assert cmd.get_description() == "Test command"
        assert cmd.get_description("en") == "Test command"

    def test_get_description_russian_fallback(self):
        """Test get_description falls back to English when Russian requested but not provided."""
        cmd = MockCommand("test", "Test command")
        assert cmd.get_description("ru") == "Test command"

    def test_get_description_russian_provided(self):
        """Test get_description returns Russian when provided."""
        cmd = MockCommand("test", "Test command", description_ru="Тестовая команда")
        assert cmd.get_description("ru") == "Тестовая команда"
        assert cmd.get_description("en") == "Test command"

    def test_get_description_invalid_language(self):
        """Test get_description falls back to English for invalid language."""
        cmd = MockCommand("test", "Test command", description_ru="Тестовая команда")
        assert cmd.get_description("invalid") == "Test command"


class TestCommandRegistry:
    """Test cases for the CommandRegistry class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()

        # Create test commands and manually register them in our test registry
        self.cmd1 = MockCommand("test1", "Test command 1", description_ru="Тестовая команда 1")
        self.cmd2 = MockCommand("test2", "Test command 2", description_ru="Тестовая команда 2")

        # Manually register in our test registry (they auto-registered in global registry)
        self.registry.register_command(self.cmd1)
        self.registry.register_command(self.cmd2)

    def test_get_bot_commands_english(self):
        """Test get_bot_commands returns English descriptions."""
        commands = self.registry.get_bot_commands("en")

        # Should return BotCommand objects with English descriptions
        assert len(commands) >= 2  # At least our test commands
        cmd_names = [cmd.command for cmd in commands]
        assert "test1" in cmd_names
        assert "test2" in cmd_names

        # Find our test commands
        test1_cmd = next(cmd for cmd in commands if cmd.command == "test1")
        test2_cmd = next(cmd for cmd in commands if cmd.command == "test2")

        assert test1_cmd.description == "Test command 1"
        assert test2_cmd.description == "Test command 2"

    def test_get_bot_commands_russian(self):
        """Test get_bot_commands returns Russian descriptions."""
        commands = self.registry.get_bot_commands("ru")

        # Should return BotCommand objects with Russian descriptions
        assert len(commands) >= 2  # At least our test commands
        cmd_names = [cmd.command for cmd in commands]
        assert "test1" in cmd_names
        assert "test2" in cmd_names

        # Find our test commands
        test1_cmd = next(cmd for cmd in commands if cmd.command == "test1")
        test2_cmd = next(cmd for cmd in commands if cmd.command == "test2")

        assert test1_cmd.description == "Тестовая команда 1"
        assert test2_cmd.description == "Тестовая команда 2"

    def test_get_bot_commands_default_language(self):
        """Test get_bot_commands defaults to English."""
        commands = self.registry.get_bot_commands()

        # Should return BotCommand objects with English descriptions
        assert len(commands) >= 2
        test1_cmd = next(cmd for cmd in commands if cmd.command == "test1")
        assert test1_cmd.description == "Test command 1"

    def test_get_bot_commands_invalid_language(self):
        """Test get_bot_commands falls back to English for invalid language."""
        commands = self.registry.get_bot_commands("invalid")

        # Should return BotCommand objects with English descriptions
        assert len(commands) >= 2
        test1_cmd = next(cmd for cmd in commands if cmd.command == "test1")
        assert test1_cmd.description == "Test command 1"


class TestCommandIntegration:
    """Integration tests for command system."""

    def test_command_registration_and_description(self):
        """Test that commands are properly registered and descriptions work."""
        registry = CommandRegistry()

        # Create a test command
        cmd = MockCommand("integration_test", "Integration test", description_ru="Интеграционный тест")

        # Manually register in our test registry
        registry.register_command(cmd)

        # Verify it's registered
        retrieved_cmd = registry.get_command("integration_test")
        assert retrieved_cmd is not None
        assert retrieved_cmd.name == "integration_test"

        # Test descriptions
        assert retrieved_cmd.get_description("en") == "Integration test"
        assert retrieved_cmd.get_description("ru") == "Интеграционный тест"

        # Test bot commands
        bot_commands = registry.get_bot_commands("en")
        integration_cmd = next((c for c in bot_commands if c.command == "integration_test"), None)
        assert integration_cmd is not None
        assert integration_cmd.description == "Integration test"

        bot_commands_ru = registry.get_bot_commands("ru")
        integration_cmd_ru = next((c for c in bot_commands_ru if c.command == "integration_test"), None)
        assert integration_cmd_ru is not None
        assert integration_cmd_ru.description == "Интеграционный тест"
