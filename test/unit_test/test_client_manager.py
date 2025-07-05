"""
Unit tests for the SlackClientManager implementation.

These tests focus on implementation-specific details and edge cases of the
SlackClientManager, ensuring it correctly manages Slack web client instances.
"""

from typing import Generator
from unittest import mock

import pytest
from _pytest.monkeypatch import MonkeyPatch
from slack_sdk.http_retry.builtin_async_handlers import AsyncRateLimitErrorRetryHandler
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp.client_manager import SlackClientManager, get_client_manager


class TestSlackClientManager:
    """Unit tests for SlackClientManager implementation."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> Generator[None, None, None]:
        """Reset the singleton instance before each test."""
        # Reset the singleton instance
        SlackClientManager._instance = None
        yield
        # Clean up after test
        SlackClientManager._instance = None

    @pytest.fixture
    def manager(self) -> SlackClientManager:
        """Fixture providing a fresh SlackClientManager instance."""
        return SlackClientManager()

    @pytest.fixture
    def mock_env_tokens(self, monkeypatch: MonkeyPatch) -> MonkeyPatch:
        """Fixture to set up mock environment tokens."""
        # Clear any existing token environment variables
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_TOKEN", raising=False)
        return monkeypatch

    def test_initialization(self) -> None:
        """Test that the manager initializes with correct default values."""
        manager = SlackClientManager()

        # Check default retry count
        assert manager._default_retry_count == 3

        # Check that caches are empty
        assert len(manager._async_clients) == 0
        assert len(manager._sync_clients) == 0

    def test_initialization_with_custom_retry_count(self) -> None:
        """Test initialization with custom retry count."""
        manager = SlackClientManager(retry_count=5)
        assert manager._default_retry_count == 5

    def test_singleton_pattern(self) -> None:
        """Test that SlackClientManager implements the singleton pattern correctly."""
        manager1 = SlackClientManager()
        manager2 = SlackClientManager()

        # Both references should point to the same instance
        assert manager1 is manager2

        # Changing retry count on one should affect the other
        manager1._default_retry_count = 10
        assert manager2._default_retry_count == 10

    def test_singleton_initialization_happens_once(self) -> None:
        """Test that initialization only happens once for the singleton."""
        # Create first instance
        manager1 = SlackClientManager(retry_count=5)
        assert manager1._default_retry_count == 5

        # Create second instance with different retry count
        manager2 = SlackClientManager(retry_count=10)

        # The retry count should not change as initialization should be skipped
        assert manager2._default_retry_count == 5
        assert manager1 is manager2

    def test_get_async_client_with_explicit_token(self, manager: SlackClientManager) -> None:
        """Test getting an async client with an explicitly provided token."""
        test_token = "xoxb-test-explicit"

        # Mock RetryableSlackClientFactory and its create_async_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_async_client.return_value = mock_client

            client = manager.get_async_client(test_token)

            # Verify factory was created with correct retry count
            mock_factory_class.assert_called_once_with(max_retry_count=3)

            # Verify client was created with the correct token
            mock_factory.create_async_client.assert_called_once_with(test_token)
            assert client is mock_client

            # Verify client is cached
            assert f"{test_token}:True" in manager._async_clients
            assert manager._async_clients[f"{test_token}:True"] is mock_client

    def test_get_sync_client_with_explicit_token(self, manager: SlackClientManager) -> None:
        """Test getting a sync client with an explicitly provided token."""
        test_token = "xoxb-test-explicit"

        # Mock RetryableSlackClientFactory and its create_sync_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_sync_client.return_value = mock_client

            client = manager.get_sync_client(test_token)

            # Verify factory was created with correct retry count
            mock_factory_class.assert_called_once_with(max_retry_count=3)

            # Verify client was created with the correct token
            mock_factory.create_sync_client.assert_called_once_with(test_token)
            assert client is mock_client

            # Verify client is cached
            assert f"{test_token}:True" in manager._sync_clients
            assert manager._sync_clients[f"{test_token}:True"] is mock_client

    def test_get_async_client_from_env(self, manager: SlackClientManager, mock_env_tokens: MonkeyPatch) -> None:
        """Test getting an async client using environment variables."""
        test_token = "xoxb-test-env"
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", test_token)

        # Mock RetryableSlackClientFactory and its create_async_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_async_client.return_value = mock_client

            client = manager.get_async_client()

            # Verify client was created with the token from env
            mock_factory.create_async_client.assert_called_once_with(test_token)
            assert client is mock_client

            # Verify client is cached
            assert f"{test_token}:True" in manager._async_clients

    def test_get_sync_client_from_env(self, manager: SlackClientManager, mock_env_tokens: MonkeyPatch) -> None:
        """Test getting a sync client using environment variables."""
        test_token = "xoxb-test-env"
        mock_env_tokens.setenv("SLACK_BOT_TOKEN", test_token)

        # Mock RetryableSlackClientFactory and its create_sync_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_sync_client.return_value = mock_client

            client = manager.get_sync_client()

            # Verify client was created with the token from env
            mock_factory.create_sync_client.assert_called_once_with(test_token)
            assert client is mock_client

            # Verify client is cached
            assert f"{test_token}:True" in manager._sync_clients

    def test_get_async_client_without_retries(self, manager: SlackClientManager) -> None:
        """Test getting an async client without retries."""
        test_token = "xoxb-test-no-retries"

        # Mock DefaultSlackClientFactory and its create_async_client method
        with mock.patch("slack_mcp.client_manager.DefaultSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_async_client.return_value = mock_client

            client = manager.get_async_client(test_token, use_retries=False)

            # Verify default factory was used
            mock_factory_class.assert_called_once()
            mock_factory.create_async_client.assert_called_once_with(test_token)
            assert client is mock_client

            # Verify client is cached with the correct key
            assert f"{test_token}:False" in manager._async_clients

    def test_get_sync_client_without_retries(self, manager: SlackClientManager) -> None:
        """Test getting a sync client without retries."""
        test_token = "xoxb-test-no-retries"

        # Mock DefaultSlackClientFactory and its create_sync_client method
        with mock.patch("slack_mcp.client_manager.DefaultSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_sync_client.return_value = mock_client

            client = manager.get_sync_client(test_token, use_retries=False)

            # Verify default factory was used
            mock_factory_class.assert_called_once()
            mock_factory.create_sync_client.assert_called_once_with(test_token)
            assert client is mock_client

            # Verify client is cached with the correct key
            assert f"{test_token}:False" in manager._sync_clients

    def test_client_caching(self, manager: SlackClientManager) -> None:
        """Test that clients are properly cached and reused."""
        test_token = "xoxb-test-cache"

        # Mock RetryableSlackClientFactory and its create_async_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_async_client.return_value = mock_client

            # Get client first time - should create new
            client1 = manager.get_async_client(test_token)
            assert mock_factory_class.call_count == 1
            assert mock_factory.create_async_client.call_count == 1

            # Get client second time - should reuse cached
            client2 = manager.get_async_client(test_token)
            assert mock_factory_class.call_count == 1  # No additional calls
            assert mock_factory.create_async_client.call_count == 1  # No additional calls

            # Verify both references are the same
            assert client1 is client2

    def test_sync_client_caching(self, manager: SlackClientManager) -> None:
        """Test that sync clients are properly cached and reused."""
        test_token = "xoxb-test-sync-cache"

        # Mock RetryableSlackClientFactory and its create_sync_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_sync_client.return_value = mock_client

            # Get client first time - should create new
            client1 = manager.get_sync_client(test_token)
            assert mock_factory_class.call_count == 1
            assert mock_factory.create_sync_client.call_count == 1

            # Get client second time - should reuse cached
            client2 = manager.get_sync_client(test_token)
            assert mock_factory_class.call_count == 1  # No additional calls
            assert mock_factory.create_sync_client.call_count == 1  # No additional calls

            # Verify both references are the same
            assert client1 is client2

            # Verify the client is returned from cache
            with mock.patch.dict(manager._sync_clients, {f"{test_token}:True": mock_client}):
                # This should return the cached client without calling the factory again
                cached_client = manager.get_sync_client(test_token)
                assert cached_client is mock_client
                # Factory should not be called again
                assert mock_factory.create_sync_client.call_count == 1

    def test_different_tokens_different_clients(self, manager: SlackClientManager) -> None:
        """Test that different tokens result in different clients."""
        token1 = "xoxb-test-token1"
        token2 = "xoxb-test-token2"

        # Mock RetryableSlackClientFactory and its create_async_client method
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client1 = mock.MagicMock()
            mock_client1.retry_handlers = []
            mock_client2 = mock.MagicMock()
            mock_client2.retry_handlers = []
            mock_factory.create_async_client.side_effect = [mock_client1, mock_client2]

            client1 = manager.get_async_client(token1)
            client2 = manager.get_async_client(token2)

            # Verify different clients were created
            assert client1 is not client2
            assert mock_factory_class.call_count == 2
            assert mock_factory.create_async_client.call_count == 2

            # Verify both are cached
            assert f"{token1}:True" in manager._async_clients
            assert f"{token2}:True" in manager._async_clients

    def test_clear_clients(self, manager: SlackClientManager) -> None:
        """Test clearing client caches."""
        test_token = "xoxb-test-clear"

        # Mock clients
        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_retryable_factory:
            with mock.patch("slack_mcp.client_manager.DefaultSlackClientFactory") as mock_default_factory:
                mock_retryable = mock.MagicMock()
                mock_retryable_factory.return_value = mock_retryable
                mock_async = mock.MagicMock()
                mock_async.retry_handlers = []
                mock_retryable.create_async_client.return_value = mock_async

                mock_default = mock.MagicMock()
                mock_default_factory.return_value = mock_default
                mock_sync = mock.MagicMock()
                mock_sync.retry_handlers = []
                mock_default.create_sync_client.return_value = mock_sync

                # Create both types of clients
                manager.get_async_client(test_token)
                manager.get_sync_client(test_token, use_retries=False)

                # Verify clients are cached
                assert len(manager._async_clients) == 1
                assert len(manager._sync_clients) == 1

                # Clear caches
                manager.clear_clients()

                # Verify caches are empty
                assert len(manager._async_clients) == 0
                assert len(manager._sync_clients) == 0

    def test_update_retry_count(self, manager: SlackClientManager) -> None:
        """Test updating retry count."""
        # Update retry count
        manager.update_retry_count(10)

        # Verify retry count was updated
        assert manager._default_retry_count == 10

        # Verify caches were cleared
        assert len(manager._async_clients) == 0
        assert len(manager._sync_clients) == 0

        # Test that new clients use the updated retry count
        test_token = "xoxb-test-retry"

        with mock.patch("slack_mcp.client_manager.RetryableSlackClientFactory") as mock_factory_class:
            mock_factory = mock.MagicMock()
            mock_factory_class.return_value = mock_factory

            mock_client = mock.MagicMock()
            mock_client.retry_handlers = []
            mock_factory.create_async_client.return_value = mock_client

            manager.get_async_client(test_token)

            # Verify factory was created with updated retry count
            mock_factory_class.assert_called_once_with(max_retry_count=10)

    def test_update_retry_count_negative(self, manager: SlackClientManager) -> None:
        """Test updating retry count with negative value raises error."""
        with pytest.raises(ValueError) as excinfo:
            manager.update_retry_count(-1)

        assert "Retry count must be non-negative" in str(excinfo.value)

    def test_update_client_async(self, manager: SlackClientManager) -> None:
        """Test updating an async client in the cache."""
        test_token = "xoxb-test-update"

        # Create a mock client
        mock_client = mock.MagicMock(spec=AsyncWebClient)
        mock_client.retry_handlers = [mock.MagicMock(spec=AsyncRateLimitErrorRetryHandler)]

        # Update the client
        manager.update_client(test_token, mock_client, is_async=True)

        # Verify client is cached
        assert f"{test_token}:True" in manager._async_clients
        assert manager._async_clients[f"{test_token}:True"] is mock_client

    def test_update_client_sync(self, manager: SlackClientManager) -> None:
        """Test updating a sync client in the cache."""
        test_token = "xoxb-test-update"

        # Create a mock client
        mock_client = mock.MagicMock(spec=WebClient)
        mock_client.retry_handlers = [mock.MagicMock(spec=RateLimitErrorRetryHandler)]

        # Update the client
        manager.update_client(test_token, mock_client, is_async=False)

        # Verify client is cached
        assert f"{test_token}:True" in manager._sync_clients
        assert manager._sync_clients[f"{test_token}:True"] is mock_client

    def test_update_client_empty_token(self, manager: SlackClientManager) -> None:
        """Test updating a client with empty token raises error."""
        mock_client = mock.MagicMock(spec=AsyncWebClient)

        with pytest.raises(ValueError) as excinfo:
            manager.update_client("", mock_client)

        assert "Token cannot be empty or None" in str(excinfo.value)

    def test_update_client_wrong_type(self, manager: SlackClientManager) -> None:
        """Test updating a client with wrong type raises error."""
        test_token = "xoxb-test-type-error"

        # Create mock clients of wrong types
        mock_async_client = mock.MagicMock(spec=AsyncWebClient)
        mock_sync_client = mock.MagicMock(spec=WebClient)

        # Test wrong type for async
        with pytest.raises(TypeError) as excinfo:
            manager.update_client(test_token, mock_sync_client, is_async=True)
        assert "Client must be an AsyncWebClient" in str(excinfo.value)

        # Test wrong type for sync
        with pytest.raises(TypeError) as excinfo:
            manager.update_client(test_token, mock_async_client, is_async=False)
        assert "Client must be a WebClient" in str(excinfo.value)

    def test_no_token_error(self, manager: SlackClientManager, mock_env_tokens: MonkeyPatch) -> None:
        """Test error when no token is available."""
        with pytest.raises(ValueError) as excinfo:
            manager.get_async_client()

        assert "Slack token not found" in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            manager.get_sync_client()

        assert "Slack token not found" in str(excinfo.value)


class TestGetClientManager:
    """Tests for the get_client_manager singleton function."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> Generator[None, None, None]:
        """Reset the singleton instance before each test."""
        # Reset the singleton instance
        SlackClientManager._instance = None
        yield
        # Clean up after test
        SlackClientManager._instance = None

    def test_get_client_manager_returns_singleton(self) -> None:
        """Test that get_client_manager returns the singleton instance."""
        # Get instance directly and through function
        direct_instance = SlackClientManager()
        function_instance = get_client_manager()

        # Verify both references are the same
        assert direct_instance is function_instance
        assert isinstance(direct_instance, SlackClientManager)

    def test_get_client_manager_consistent(self) -> None:
        """Test that get_client_manager returns the same instance each time."""
        # Get instance twice through function
        manager1 = get_client_manager()
        manager2 = get_client_manager()

        # Verify both references are the same
        assert manager1 is manager2
        assert isinstance(manager1, SlackClientManager)
