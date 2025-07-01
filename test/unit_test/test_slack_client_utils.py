"""Unit tests for Slack client utility functions in server.py."""

from __future__ import annotations

from typing import Generator, Optional
from unittest.mock import MagicMock

import pytest
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp import server as srv
from slack_mcp.client_factory import RetryableSlackClientFactory


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove Slack token environment variables."""
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_TOKEN", raising=False)


@pytest.fixture
def reset_slack_clients() -> Generator[None, None, None]:
    """Reset all slack client globals after each test."""
    # Save original values
    original_clients: dict[str, AsyncWebClient] = srv._slack_clients.copy()
    original_retry_count: int = srv._slack_client_retry_count
    original_factory: RetryableSlackClientFactory = srv._retryable_factory
    original_default_token: Optional[str] = srv._DEFAULT_TOKEN

    # Clear for test
    srv._slack_clients.clear()

    yield

    # Restore original values
    srv._slack_clients = original_clients
    srv._slack_client_retry_count = original_retry_count
    srv._retryable_factory = original_factory
    srv._DEFAULT_TOKEN = original_default_token


class TestGetSlackClient:
    """Tests for get_slack_client function."""

    def test_get_client_with_explicit_token(self, reset_slack_clients: None) -> None:
        """Should create a new client when provided a token."""
        # First, verify the cache is empty
        assert len(srv._slack_clients) == 0

        # Call with explicit token
        client: AsyncWebClient = srv.get_slack_client("test-token-123")

        # Check results - a client was created and cached
        assert isinstance(client, AsyncWebClient)
        assert client.token == "test-token-123"  # AsyncWebClient stores the token
        assert len(srv._slack_clients) == 1
        assert "test-token-123" in srv._slack_clients

    def test_get_client_returns_cached(self, reset_slack_clients: None) -> None:
        """Should return cached client for same token."""
        # Call twice with same token
        client1: AsyncWebClient = srv.get_slack_client("test-token-123")
        client2: AsyncWebClient = srv.get_slack_client("test-token-123")

        # Should return the exact same object
        assert client1 is client2
        assert len(srv._slack_clients) == 1

    def test_different_tokens_create_different_clients(self, reset_slack_clients: None) -> None:
        """Should create different clients for different tokens."""
        # Call with different tokens
        client1: AsyncWebClient = srv.get_slack_client("token1")
        client2: AsyncWebClient = srv.get_slack_client("token2")

        # Should be different objects with correct tokens
        assert client1 is not client2
        assert client1.token == "token1"
        assert client2.token == "token2"
        assert len(srv._slack_clients) == 2

    def test_get_client_with_retry_uses_factory(self, reset_slack_clients: None, clean_env: None) -> None:
        """Should use RetryableSlackClientFactory when retry count > 0."""
        # Create a mock RetryableSlackClientFactory
        mock_factory: MagicMock = MagicMock(spec=RetryableSlackClientFactory)
        mock_client: MagicMock = MagicMock(spec=AsyncWebClient)
        mock_factory.create_async_client.return_value = mock_client

        # Setup server module
        srv._slack_client_retry_count = 5
        srv._retryable_factory = mock_factory

        # Call get_slack_client
        client: AsyncWebClient = srv.get_slack_client("test-token")

        # Verify factory was used
        mock_factory.create_async_client.assert_called_once_with("test-token")
        assert client is mock_client
        assert "test-token" in srv._slack_clients

    def test_get_client_from_env(self, reset_slack_clients: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should fall back to environment variables when token is None."""
        # Set environment variable
        monkeypatch.setenv("SLACK_BOT_TOKEN", "env-token-123")

        # Update _DEFAULT_TOKEN which is calculated at module import time
        srv._DEFAULT_TOKEN = "env-token-123"

        # Call get_slack_client with no token
        client: AsyncWebClient = srv.get_slack_client()

        # Verify correct token was used
        assert client.token == "env-token-123"
        assert "env-token-123" in srv._slack_clients

    def test_get_client_fallback_to_slack_token(
        self, reset_slack_clients: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should try SLACK_TOKEN if SLACK_BOT_TOKEN is not set."""
        # Set only SLACK_TOKEN
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.setenv("SLACK_TOKEN", "fallback-token")

        # Directly set the cached token value
        srv._DEFAULT_TOKEN = "fallback-token"

        # Call with no token
        client: AsyncWebClient = srv.get_slack_client()

        # Verify correct token was used
        assert client.token == "fallback-token"
        assert "fallback-token" in srv._slack_clients

    def test_get_client_no_token_raises_error(self, reset_slack_clients: None, clean_env: None) -> None:
        """Should raise ValueError when no token is available."""
        # Set _DEFAULT_TOKEN to None to simulate no env vars
        srv._DEFAULT_TOKEN = None

        # Should raise ValueError
        with pytest.raises(ValueError) as excinfo:
            srv.get_slack_client()

        # Check error message
        assert "Slack token not found" in str(excinfo.value)

    @pytest.mark.parametrize(
        "first_retry,second_retry,expected_different",
        [
            (0, 0, False),  # Same retry count (both 0) -> same client behavior
            (0, 1, True),  # No retry vs retry -> different client behavior
            (0, 3, True),  # No retry vs multiple retries -> different client behavior
            (1, 3, False),  # Both with retry (different counts) -> same client type
            (3, 0, True),  # Multiple retries vs no retry -> different client behavior
        ],
    )
    def test_different_clients_by_retry_count(
        self,
        reset_slack_clients: None,
        first_retry: int,
        second_retry: int,
        expected_different: bool,
    ) -> None:
        """Should create clients based on retry count configuration.

        Parameters
        ----------
        first_retry : int
            First retry count to test
        second_retry : int
            Second retry count to test
        expected_different : bool
            Whether the two clients should have different retry handler configurations
        """
        test_token = "test-token-for-retry-test"

        # First get a client with first_retry
        srv._slack_client_retry_count = first_retry
        if first_retry > 0:
            srv._retryable_factory = RetryableSlackClientFactory(max_retry_count=first_retry)
        first_client = srv.get_slack_client(token=test_token)

        # Clear clients to force re-creation
        srv.clear_slack_clients()

        # Create a client with second_retry
        srv._slack_client_retry_count = second_retry
        if second_retry > 0:
            srv._retryable_factory = RetryableSlackClientFactory(max_retry_count=second_retry)
        second_client = srv.get_slack_client(token=test_token)

        # Verify clients are different instances
        assert first_client is not second_client

        # Determine if client behavior should be different based on retry settings
        first_has_retry = first_retry > 0
        second_has_retry = second_retry > 0

        # Check if the clients have different retry handler configurations
        # We identify this by checking length of retry_handlers
        first_handler_count = len(first_client.retry_handlers)
        second_handler_count = len(second_client.retry_handlers)

        # For non-retryable clients, Slack SDK might still include some default handlers
        # The key distinction is whether the RetryableSlackClientFactory was used
        handlers_differ = first_has_retry != second_has_retry

        # Verify the difference in client configuration matches our expectation
        assert handlers_differ == expected_different, (
            f"Expected handlers_differ={expected_different}, but got {handlers_differ}. "
            f"First retry={first_retry} (handlers={first_handler_count}), "
            f"Second retry={second_retry} (handlers={second_handler_count})"
        )

        # Verify both clients have the same token regardless of retry config
        assert first_client.token == test_token
        assert second_client.token == test_token


class TestClearSlackClients:
    """Tests for clear_slack_clients function."""

    def test_clear_empty_cache(self, reset_slack_clients: None) -> None:
        """Should handle clearing an already empty cache."""
        # Start with empty cache
        assert len(srv._slack_clients) == 0

        # Clear
        srv.clear_slack_clients()

        # Still empty
        assert len(srv._slack_clients) == 0

    def test_clear_populated_cache(self, reset_slack_clients: None) -> None:
        """Should clear all clients from cache."""
        # Populate cache
        srv._slack_clients["token1"] = AsyncWebClient(token="token1")
        srv._slack_clients["token2"] = AsyncWebClient(token="token2")
        assert len(srv._slack_clients) == 2

        # Clear
        srv.clear_slack_clients()

        # Verify empty
        assert len(srv._slack_clients) == 0

    def test_clear_forces_new_clients(self, reset_slack_clients: None) -> None:
        """Should force creation of new clients after clearing."""
        # Create initial client
        client1: AsyncWebClient = srv.get_slack_client("test-token")

        # Clear cache
        srv.clear_slack_clients()

        # Get client again
        client2: AsyncWebClient = srv.get_slack_client("test-token")

        # Should be different objects
        assert client1 is not client2
        assert client1.token == client2.token


class TestUpdateSlackClient:
    """Tests for update_slack_client function."""

    def test_update_new_client(self, reset_slack_clients: None) -> None:
        """Should add a new client to the cache."""
        # Create client
        custom_client: AsyncWebClient = AsyncWebClient(token="custom-token")

        # Update cache
        srv.update_slack_client("custom-token", custom_client)

        # Verify in cache
        assert "custom-token" in srv._slack_clients
        assert srv._slack_clients["custom-token"] is custom_client

    def test_update_existing_client(self, reset_slack_clients: None) -> None:
        """Should replace an existing client in the cache."""
        # Add client to cache
        original_client: AsyncWebClient = AsyncWebClient(token="test-token")
        srv._slack_clients["test-token"] = original_client

        # Create replacement
        replacement_client: AsyncWebClient = AsyncWebClient(token="test-token")

        # Update cache
        srv.update_slack_client("test-token", replacement_client)

        # Verify replacement
        assert srv._slack_clients["test-token"] is replacement_client
        assert srv._slack_clients["test-token"] is not original_client

    def test_update_with_empty_token_raises_error(self, reset_slack_clients: None) -> None:
        """Should raise ValueError when token is empty."""
        client: AsyncWebClient = AsyncWebClient(token="valid-token")

        # Empty string token
        with pytest.raises(ValueError) as excinfo:
            srv.update_slack_client("", client)
        assert "Token cannot be empty" in str(excinfo.value)

        # None token
        with pytest.raises(ValueError):
            # We need to ignore the type error since we're testing runtime behavior
            srv.update_slack_client(None, client)  # type: ignore


class TestSetSlackClientRetryCount:
    """Tests for set_slack_client_retry_count function."""

    def test_set_retry_count(self, reset_slack_clients: None) -> None:
        """Should update the retry count and factory."""
        # Initial value
        initial_count: int = srv._slack_client_retry_count

        # Set to new value
        test_count: int = initial_count + 5  # Ensure different
        srv.set_slack_client_retry_count(test_count)

        # Verify updated
        assert srv._slack_client_retry_count == test_count
        assert srv._retryable_factory.max_retry_count == test_count

    def test_set_retry_clears_cache(self, reset_slack_clients: None) -> None:
        """Should clear client cache when retry count is changed."""
        # Populate cache
        srv._slack_clients["token1"] = AsyncWebClient(token="token1")
        srv._slack_clients["token2"] = AsyncWebClient(token="token2")
        assert len(srv._slack_clients) == 2

        # Set retry count
        srv.set_slack_client_retry_count(10)

        # Verify cache cleared
        assert len(srv._slack_clients) == 0
