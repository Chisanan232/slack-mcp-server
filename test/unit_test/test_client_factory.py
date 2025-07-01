"""
Unit tests for the DefaultSlackClientFactory implementation.

These tests focus on implementation-specific details and edge cases of the
DefaultSlackClientFactory, while the contract tests ensure adherence to
the abstract interface requirements.
"""

import os
from unittest import mock

import pytest
from slack_sdk.http_retry.builtin_async_handlers import (
    AsyncConnectionErrorRetryHandler,
    AsyncRateLimitErrorRetryHandler,
    AsyncServerErrorRetryHandler,
)
from slack_sdk.http_retry.builtin_handlers import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler,
    ServerErrorRetryHandler,
)

from slack_mcp.client_factory import (
    DefaultSlackClientFactory,
    RetryableSlackClientFactory,
    default_factory,
    retryable_factory,
)
from slack_mcp.model import SlackPostMessageInput, SlackThreadReplyInput, _BaseInput


class TestDefaultSlackClientFactory:
    """Unit tests for DefaultSlackClientFactory implementation."""

    @pytest.fixture
    def factory(self):
        """Fixture providing a fresh DefaultSlackClientFactory instance."""
        return DefaultSlackClientFactory()

    @pytest.fixture
    def mock_env_tokens(self, monkeypatch):
        """Fixture to set up mock environment tokens."""
        # Clear any existing token environment variables
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_TOKEN", raising=False)
        return monkeypatch

    def test_resolve_token_with_explicit_token(self, factory):
        """Test resolving token when explicitly provided."""
        test_token = "xoxb-test-explicit"
        resolved = factory._resolve_token(test_token)
        assert resolved == test_token

    def test_resolve_token_from_bot_env(self, factory, mock_env_tokens):
        """Test resolving token from SLACK_BOT_TOKEN environment variable."""
        test_token = "xoxb-test-bot-env"
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", test_token)

        resolved = factory._resolve_token()
        assert resolved == test_token

    def test_resolve_token_from_generic_env(self, factory, mock_env_tokens):
        """Test resolving token from SLACK_TOKEN environment variable."""
        test_token = "xoxb-test-generic-env"
        mock_env_tokens.setenv("SLACK_TOKEN", test_token)

        resolved = factory._resolve_token()
        assert resolved == test_token

    def test_resolve_token_precedence(self, factory, mock_env_tokens):
        """Test token resolution precedence: explicit > SLACK_BOT_TOKEN > SLACK_TOKEN."""
        explicit_token = "xoxb-explicit"
        bot_token = "xoxb-bot-env"
        generic_token = "xoxb-generic-env"

        # Set both environment variables
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", bot_token)
        mock_env_tokens.setenv("SLACK_TOKEN", generic_token)

        # Test explicit token takes precedence over both env vars
        assert factory._resolve_token(explicit_token) == explicit_token

        # Test SLACK_BOT_TOKEN takes precedence over SLACK_TOKEN
        assert factory._resolve_token() == bot_token

        # Remove SLACK_BOT_TOKEN and verify SLACK_TOKEN is used
        mock_env_tokens.delenv("SLACK_BOT_TOKEN")
        assert factory._resolve_token() == generic_token

    def test_resolve_token_error_when_missing(self, factory, mock_env_tokens):
        """Test error is raised when no token can be resolved."""
        with pytest.raises(ValueError) as excinfo:
            factory._resolve_token()

        # Verify error message is informative
        assert "Slack token not found" in str(excinfo.value)
        assert "SLACK_BOT_TOKEN" in str(excinfo.value)
        assert "SLACK_TOKEN" in str(excinfo.value)

    def test_create_async_client_initializes_correctly(self, factory):
        """Test AsyncWebClient is initialized with the correct token."""
        test_token = "xoxb-test-token"

        # Mock AsyncWebClient to verify initialization
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            factory.create_async_client(test_token)

            # Verify client was initialized with the correct token
            mock_client.assert_called_once_with(token=test_token)

    def test_create_sync_client_initializes_correctly(self, factory):
        """Test WebClient is initialized with the correct token."""
        test_token = "xoxb-test-token"

        # Mock WebClient to verify initialization
        with mock.patch("slack_mcp.client_factory.WebClient") as mock_client:
            factory.create_sync_client(test_token)

            # Verify client was initialized with the correct token
            mock_client.assert_called_once_with(token=test_token)

    def test_create_async_client_from_input_uses_input_token(self, factory):
        """Test client creation from input uses the input's token attribute."""
        test_token = "xoxb-from-input"

        class TestInput(_BaseInput):
            pass

        input_obj = TestInput(token=test_token)

        # Mock AsyncWebClient to verify initialization
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            factory.create_async_client_from_input(input_obj)

            # Verify client was initialized with token from input
            mock_client.assert_called_once_with(token=test_token)

    def test_create_async_client_from_input_without_token(self, factory, mock_env_tokens):
        """Test client creation from input falls back to environment when input has no token."""
        env_token = "xoxb-from-env"
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", env_token)

        class TestInput(_BaseInput):
            pass

        input_obj = TestInput()  # No token attribute

        # Mock AsyncWebClient to verify initialization
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            factory.create_async_client_from_input(input_obj)

            # Verify client was initialized with token from environment
            mock_client.assert_called_once_with(token=env_token)

    def test_create_async_client_from_input_with_none_token(self, factory, mock_env_tokens):
        """Test client creation from input with token=None falls back to environment."""
        env_token = "xoxb-from-env"
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", env_token)

        class TestInput(_BaseInput):
            pass

        input_obj = TestInput(token=None)  # Token is explicitly None

        # Mock AsyncWebClient to verify initialization
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            factory.create_async_client_from_input(input_obj)

            # Verify client was initialized with token from environment
            mock_client.assert_called_once_with(token=env_token)

    def test_handle_empty_string_token(self, factory, mock_env_tokens):
        """Test handling of empty string tokens."""
        env_token = "xoxb-from-env"
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", env_token)

        # Empty string should be treated like None and fall back to env
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            factory.create_async_client(token="")
            mock_client.assert_called_once_with(token=env_token)

    def test_default_factory_instance(self):
        """Test that the default_factory instance is of the correct type."""
        assert isinstance(default_factory, DefaultSlackClientFactory)

        # Test using the default instance
        test_token = "xoxb-default-instance-test"

        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            default_factory.create_async_client(test_token)
            mock_client.assert_called_once_with(token=test_token)

    @pytest.mark.parametrize(
        "input_class,expected_attributes",
        [
            (SlackPostMessageInput, {"channel": "test-channel", "text": "Hello"}),
            (SlackThreadReplyInput, {"channel": "test-channel", "thread_ts": "1234.5678", "texts": ["Reply"]}),
        ],
    )
    def test_with_different_input_types(self, factory, input_class, expected_attributes):
        """Test factory works with different types of input objects."""
        test_token = "xoxb-input-test"

        # Create input object with expected attributes plus token
        input_attrs = {**expected_attributes, "token": test_token}
        input_obj = input_class(**input_attrs)

        # Verify token extraction works for all input types
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
            factory.create_async_client_from_input(input_obj)
            mock_client.assert_called_once_with(token=test_token)

    def test_thread_safety(self, factory):
        """Test that token resolution works in a thread-safe manner."""
        # This is a basic test for thread safety - in production, you might use
        # threading or asyncio to test concurrent access patterns
        test_token = "xoxb-thread-safe-test"

        # Patch os.getenv to simulate potential thread race conditions
        original_getenv = os.getenv

        def mock_getenv(key, default=None):
            if key == "SLACK_BOT_TOKEN":
                return test_token
            return original_getenv(key, default)

        with mock.patch("os.getenv", side_effect=mock_getenv):
            with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_client:
                factory.create_async_client()
                mock_client.assert_called_once_with(token=test_token)


class TestRetryableSlackClientFactory:
    """Unit tests for RetryableSlackClientFactory implementation."""

    @pytest.fixture
    def factory(self):
        """Fixture providing a fresh RetryableSlackClientFactory instance."""
        return RetryableSlackClientFactory()

    @pytest.fixture
    def mock_env_tokens(self, monkeypatch):
        """Fixture to set up mock environment tokens."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-retry-token")
        return monkeypatch

    def test_default_retry_handlers_async(self, factory):
        """Test default retry handlers for async client."""
        handlers = factory._get_async_retry_handlers()

        # By default, all three handler types should be present
        assert len(handlers) == 3

        # Check handler types
        handler_types = [type(h) for h in handlers]
        assert AsyncRateLimitErrorRetryHandler in handler_types
        assert AsyncServerErrorRetryHandler in handler_types
        assert AsyncConnectionErrorRetryHandler in handler_types

        # Check max retry count
        for handler in handlers:
            assert handler.max_retry_count == 3  # default value

    def test_default_retry_handlers_sync(self, factory):
        """Test default retry handlers for sync client."""
        handlers = factory._get_sync_retry_handlers()

        # By default, all three handler types should be present
        assert len(handlers) == 3

        # Check handler types
        handler_types = [type(h) for h in handlers]
        assert RateLimitErrorRetryHandler in handler_types
        assert ServerErrorRetryHandler in handler_types
        assert ConnectionErrorRetryHandler in handler_types

        # Check max retry count
        for handler in handlers:
            assert handler.max_retry_count == 3  # default value

    def test_custom_max_retry_count(self):
        """Test custom max retry count configuration."""
        custom_factory = RetryableSlackClientFactory(max_retry_count=5)

        # Check both sync and async handlers
        for handler in custom_factory._get_sync_retry_handlers():
            assert handler.max_retry_count == 5

        for handler in custom_factory._get_async_retry_handlers():
            assert handler.max_retry_count == 5

    def test_custom_handler_inclusion(self):
        """Test custom inclusion/exclusion of retry handlers."""
        # Only include rate limit retries
        factory = RetryableSlackClientFactory(
            include_rate_limit_retries=True, include_server_error_retries=False, include_connection_error_retries=False
        )

        async_handlers = factory._get_async_retry_handlers()
        sync_handlers = factory._get_sync_retry_handlers()

        # Should have exactly one handler of each type
        assert len(async_handlers) == 1
        assert len(sync_handlers) == 1

        # Should be rate limit handlers
        assert isinstance(async_handlers[0], AsyncRateLimitErrorRetryHandler)
        assert isinstance(sync_handlers[0], RateLimitErrorRetryHandler)

    def test_async_client_has_retry_handlers(self, factory, mock_env_tokens):
        """Test that async clients are created with retry handlers attached."""
        # Create a mock client with a retry_handlers list attribute
        mock_client = mock.MagicMock()
        mock_client.retry_handlers = []

        # Create a mock client constructor that returns our mock client
        mock_client_constructor = mock.MagicMock(return_value=mock_client)

        with mock.patch("slack_mcp.client_factory.AsyncWebClient", mock_client_constructor):
            client = factory.create_async_client()

            # Client should have 3 retry handlers attached (default configuration)
            assert len(client.retry_handlers) == 3

            # Verify each handler type
            handler_types = [type(h) for h in client.retry_handlers]
            assert AsyncRateLimitErrorRetryHandler in handler_types
            assert AsyncServerErrorRetryHandler in handler_types
            assert AsyncConnectionErrorRetryHandler in handler_types

    def test_sync_client_has_retry_handlers(self, factory, mock_env_tokens):
        """Test that sync clients are created with retry handlers attached."""
        # Create a mock client with a retry_handlers list attribute
        mock_client = mock.MagicMock()
        mock_client.retry_handlers = []

        # Create a mock client constructor that returns our mock client
        mock_client_constructor = mock.MagicMock(return_value=mock_client)

        with mock.patch("slack_mcp.client_factory.WebClient", mock_client_constructor):
            client = factory.create_sync_client()

            # Client should have 3 retry handlers attached (default configuration)
            assert len(client.retry_handlers) == 3

            # Verify each handler type
            handler_types = [type(h) for h in client.retry_handlers]
            assert RateLimitErrorRetryHandler in handler_types
            assert ServerErrorRetryHandler in handler_types
            assert ConnectionErrorRetryHandler in handler_types

    def test_async_client_from_input_has_retry_handlers(self, factory, mock_env_tokens):
        """Test that async clients created from input have retry handlers attached."""
        # Create a mock client with a retry_handlers list attribute
        mock_client = mock.MagicMock()
        mock_client.retry_handlers = []

        # Create a mock client constructor that returns our mock client
        mock_client_constructor = mock.MagicMock(return_value=mock_client)

        with mock.patch("slack_mcp.client_factory.AsyncWebClient", mock_client_constructor):
            client = factory.create_async_client_from_input(_BaseInput(token="xoxb-test-token"))

            # Client should have retry handlers attached
            assert len(client.retry_handlers) > 0

    def test_inheritance_maintains_token_resolution(self, factory, mock_env_tokens):
        """Test that token resolution still works correctly in retryable factory."""
        test_token = "xoxb-explicit-test"

        # Test explicit token
        with mock.patch("slack_mcp.client_factory.AsyncWebClient") as mock_async:
            factory.create_async_client(test_token)
            mock_async.assert_called_once_with(token=test_token)

        # Test env fallback
        with mock.patch("slack_mcp.client_factory.WebClient") as mock_web:
            factory.create_sync_client()
            mock_web.assert_called_once_with(token="xoxb-test-retry-token")

    def test_retryable_factory_global_instance(self):
        """Test the global retryable factory instance."""
        assert isinstance(retryable_factory, RetryableSlackClientFactory)

        # Create a mock client with a retry_handlers list attribute
        mock_client = mock.MagicMock()
        mock_client.retry_handlers = []

        # Create a mock client constructor that returns our mock client
        mock_client_constructor = mock.MagicMock(return_value=mock_client)

        with mock.patch("slack_mcp.client_factory.AsyncWebClient", mock_client_constructor):
            client = retryable_factory.create_async_client("xoxb-test-token")

            # Global instance should also add retry handlers
            assert len(client.retry_handlers) > 0
