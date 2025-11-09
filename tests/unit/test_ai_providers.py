"""Unit tests for AI provider abstractions."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from ai_providers import create_provider, GroqProvider, OpenRouterProvider, LocalProvider


class TestCreateProvider:
    """Test the create_provider factory function."""

    def test_create_groq_provider(self):
        """Test creating a Groq provider."""
        with patch('ai_providers.groq_provider.Groq'):
            provider = create_provider("groq", "test_key", "test_model")
            assert isinstance(provider, GroqProvider)
            assert provider.api_key == "test_key"
            assert provider.model == "test_model"

    def test_create_openrouter_provider(self):
        """Test creating an OpenRouter provider."""
        with patch('ai_providers.openrouter_provider.AsyncOpenAI'):
            provider = create_provider("openrouter", "test_key", "test_model")
            assert isinstance(provider, OpenRouterProvider)
            assert provider.api_key == "test_key"
            assert provider.model == "test_model"

    def test_create_local_provider(self):
        """Test creating a Local provider."""
        with patch('ai_providers.local_provider.OpenAI'):
            provider = create_provider("local", "test_key", "test_model", "http://localhost:8000")
            assert isinstance(provider, LocalProvider)
            assert provider.api_key == "test_key"
            assert provider.model == "test_model"
            assert provider.base_url == "http://localhost:8000"

    def test_create_local_provider_default_url(self):
        """Test creating a Local provider with default URL."""
        with patch('ai_providers.local_provider.OpenAI'):
            provider = create_provider("local", "test_key", "test_model")
            assert provider.base_url == "http://localhost:8000/v1"

    def test_create_provider_case_insensitive(self):
        """Test that provider type is case insensitive."""
        with patch('ai_providers.groq_provider.Groq'):
            provider = create_provider("GROQ", "test_key", "test_model")
            assert isinstance(provider, GroqProvider)

    def test_create_provider_invalid_type(self):
        """Test creating provider with invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported provider type: invalid"):
            create_provider("invalid", "test_key", "test_model")


class TestGroqProvider:
    """Test the GroqProvider class."""

    @pytest.fixture
    def provider(self):
        """Create a GroqProvider instance with mocked client."""
        with patch('ai_providers.groq_provider.Groq') as mock_groq:
            provider = GroqProvider("test_key", "test_model")
            return provider

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.api_key == "test_key"
        assert provider.model == "test_model"
        assert provider.get_provider_name() == "Groq"

    def test_build_prompt_basic(self, provider):
        """Test building basic prompt without context."""
        messages = provider._build_prompt()
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "анекдот" in messages[1]["content"].lower()

    def test_build_prompt_with_context(self, provider):
        """Test building prompt with user-provided context."""
        messages = provider._build_prompt("test context")
        assert len(messages) == 2
        assert "test context" in messages[1]["content"]

    def test_build_prompt_contextual(self, provider):
        """Test building contextual prompt."""
        messages = provider._build_prompt("test context", is_contextual=True)
        assert len(messages) == 2
        assert "связанный с этим контекстом" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_generate_joke_success(self, provider):
        """Test successful joke generation."""
        # Mock the API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test joke"

        provider.client.chat.completions.create = Mock(return_value=mock_response)

        result = await provider.generate_joke()
        assert result == "Test joke"
        provider.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_joke_failure(self, provider):
        """Test joke generation failure."""
        provider.client.chat.completions.create = Mock(side_effect=Exception("API Error"))

        with pytest.raises(Exception, match="Groq API error: API Error"):
            await provider.generate_joke()

    @pytest.mark.asyncio
    async def test_free_request_success(self, provider):
        """Test successful free request."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"

        provider.client.chat.completions.create = Mock(return_value=mock_response)

        result = await provider.free_request("test message")
        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_free_request_with_system_message(self, provider):
        """Test free request with system message."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"

        provider.client.chat.completions.create = Mock(return_value=mock_response)

        result = await provider.free_request("test message", "system prompt")
        assert result == "Test response"

        # Check that system message was included
        call_args = provider.client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "system prompt"

    @pytest.mark.asyncio
    async def test_generate_autonomous_comment_success(self, provider):
        """Test successful autonomous comment generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"comment": "test"}'

        provider.client.chat.completions.create = Mock(return_value=mock_response)

        result = await provider.generate_autonomous_comment("test prompt")
        assert result == '{"comment": "test"}'


class TestOpenRouterProvider:
    """Test the OpenRouterProvider class."""

    @pytest.fixture
    def provider(self):
        """Create an OpenRouterProvider instance with mocked client."""
        with patch('ai_providers.openrouter_provider.AsyncOpenAI') as mock_openai:
            provider = OpenRouterProvider("test_key", "test_model")
            return provider

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.api_key == "test_key"
        assert provider.model == "test_model"
        assert provider.get_provider_name() == "OpenRouter"

    @pytest.mark.asyncio
    async def test_generate_joke_success(self, provider):
        """Test successful joke generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test joke"

        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.generate_joke()
        assert result == "Test joke"


class TestLocalProvider:
    """Test the LocalProvider class."""

    @pytest.fixture
    def provider(self):
        """Create a LocalProvider instance with mocked client."""
        with patch('ai_providers.local_provider.OpenAI') as mock_openai:
            provider = LocalProvider("test_key", "test_model", "http://localhost:8000")
            return provider

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.api_key == "test_key"
        assert provider.model == "test_model"
        assert provider.base_url == "http://localhost:8000"
        assert provider.get_provider_name() == "Local"

    @pytest.mark.asyncio
    async def test_generate_joke_success(self, provider):
        """Test successful joke generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test joke"

        provider.client.chat.completions.create = Mock(return_value=mock_response)

        result = await provider.generate_joke()
        assert result == "Test joke"
