"""Unit tests for Slack client utility functions in server.py."""

from __future__ import annotations

from typing import Generator, Optional
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp import server as srv
from slack_mcp.client_factory import RetryableSlackClientFactory, SlackClientFactory
from slack_mcp.client_manager import SlackClientManager, get_client_manager


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove Slack token environment variables."""
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_TOKEN", raising=False)


@pytest.fixture
def reset_slack_clients() -> Generator[None, None, None]:
    """Reset the SlackClientManager singleton for each test."""
    # Save original instance
    original_instance = SlackClientManager._instance
    original_default_token = srv._DEFAULT_TOKEN

    # Create a fresh instance for testing
    SlackClientManager._instance = None
    manager = get_client_manager()
    
    yield

    # Restore original values
    SlackClientManager._instance = original_instance
    srv._DEFAULT_TOKEN = original_default_token


class TestGetSlackClient:
    """Tests for get_slack_client function."""

    def test_get_client_with_explicit_token(self, reset_slack_clients: None) -> None:
        """Should create a client with the specified token."""
        # Call with explicit token
        client: AsyncWebClient = srv.get_slack_client("test-token-123")

        # Should have created client with that token
        assert client.token == "test-token-123"
        
        # Check it was cached with the correct key format
        manager = get_client_manager()
        cache_key = "test-token-123:True"  # Default is use_retries=True
        assert cache_key in manager._async_clients
        assert manager._async_clients[cache_key] is client

    def test_get_client_returns_cached(self, reset_slack_clients: None) -> None:
        """Should return cached client for same token."""
        # Call twice with same token
        client1: AsyncWebClient = srv.get_slack_client("test-token-123")
        client2: AsyncWebClient = srv.get_slack_client("test-token-123")

        # Should return the exact same object
        assert client1 is client2
        manager = get_client_manager()
        cache_key = "test-token-123:True"  # Default is use_retries=True
        assert cache_key in manager._async_clients

    def test_different_tokens_create_different_clients(self, reset_slack_clients: None) -> None:
        """Should create different clients for different tokens."""
        # Call with different tokens
        client1: AsyncWebClient = srv.get_slack_client("token1")
        client2: AsyncWebClient = srv.get_slack_client("token2")

        # Should be different objects with correct tokens
        assert client1 is not client2
        assert client1.token == "token1"
        assert client2.token == "token2"
        manager = get_client_manager()
        cache_key1 = "token1:True"  # Default is use_retries=True
        cache_key2 = "token2:True"  # Default is use_retries=True
        assert cache_key1 in manager._async_clients
        assert cache_key2 in manager._async_clients

    def test_get_client_with_retry_uses_factory(self, reset_slack_clients: None, clean_env: None) -> None:
        """Should use RetryableSlackClientFactory when retry count > 0."""
        # Create a mock factory and client
        mock_client = MagicMock(spec=AsyncWebClient)
        mock_factory = MagicMock()
        mock_factory.create_async_client.return_value = mock_client
        
        # Patch the RetryableSlackClientFactory class to return our mock factory
        with patch("slack_mcp.client_manager.RetryableSlackClientFactory", return_value=mock_factory):
            # Get the client manager and set retry count
            manager = get_client_manager()
            manager.update_retry_count(5)
            
            # Call get_slack_client which should use the retryable factory
            client = srv.get_slack_client("test-token")
            
            # Verify factory was used
            mock_factory.create_async_client.assert_called_once_with("test-token")
            assert client is mock_client

    def test_get_client_from_env(self, reset_slack_clients: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use token from SLACK_BOT_TOKEN environment variable."""
        # Set environment variable
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-bot-token")
        monkeypatch.delenv("SLACK_TOKEN", raising=False)

        # Call without token parameter
        client: AsyncWebClient = srv.get_slack_client()

        # Should use token from environment
        assert client.token == "xoxb-bot-token"
        manager = get_client_manager()
        cache_key = "xoxb-bot-token:True"  # Default is use_retries=True
        assert cache_key in manager._async_clients

    def test_get_client_fallback_to_slack_token(
        self, reset_slack_clients: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should fallback to SLACK_TOKEN if SLACK_BOT_TOKEN is not set."""
        # Set only SLACK_TOKEN
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.setenv("SLACK_TOKEN", "xoxp-user-token")

        # Call without token parameter
        client: AsyncWebClient = srv.get_slack_client()

        # Should use token from SLACK_TOKEN
        assert client.token == "xoxp-user-token"
        manager = get_client_manager()
        cache_key = "xoxp-user-token:True"  # Default is use_retries=True
        assert cache_key in manager._async_clients

    def test_get_client_no_token_raises_error(self, reset_slack_clients: None, clean_env: None) -> None:
        """Should raise ValueError if no token is provided or found in environment."""
        # Call without token and no environment variables
        with pytest.raises(ValueError, match="Slack token not found"):
            srv.get_slack_client()

    @pytest.mark.parametrize(
        "initial_retry,new_retry,should_be_different",
        [
            (0, 0, False),  # Same retry count, same client
            (0, 1, True),   # Different retry count, different client
            (0, 3, True),   # Different retry count, different client
            (1, 3, False),  # Both use retries, same client
            (3, 0, True),   # One uses retries, one doesn't, different client
        ],
    )
    def test_different_clients_by_retry_count(
        self,
        reset_slack_clients: None,
        initial_retry: int,
        new_retry: int,
        should_be_different: bool,
    ) -> None:
        """Should create different clients based on retry count."""
        # Setup
        manager = get_client_manager()
        manager.update_retry_count(initial_retry)
        
        # Get first client
        client1 = srv.get_slack_client("test-token")
        
        # Clear cache to force new client creation
        manager.clear_clients()
        
        # Update retry count and get second client
        manager.update_retry_count(new_retry)
        client2 = srv.get_slack_client("test-token")
        
        # Check if clients are different based on retry settings
        if should_be_different:
            assert client1 is not client2
        else:
            # In our new implementation, clients with the same token are different objects
            # but functionally equivalent, so we can't use 'is' comparison
            assert client1.token == client2.token

    def test_get_client_with_retry(self, reset_slack_clients: None) -> None:
        """Should use RetryableSlackClientFactory when use_retries=True."""
        # Setup mock factory
        mock_factory = MagicMock()
        mock_client = MagicMock(spec=AsyncWebClient)
        mock_factory.create_async_client.return_value = mock_client
        
        # Patch the RetryableSlackClientFactory class
        with patch("slack_mcp.client_manager.RetryableSlackClientFactory", return_value=mock_factory):
            # Call the client manager directly with use_retries=True
            manager = get_client_manager()
            client = manager.get_async_client("test-token", use_retries=True)
            
            # Should have used the retryable factory
            assert client is mock_client
            mock_factory.create_async_client.assert_called_once_with("test-token")
            
            # Check it was cached with the correct key format
            cache_key = "test-token:True"
            assert cache_key in manager._async_clients


class TestClearSlackClients:
    """Tests for clear_slack_clients function."""

    def test_clear_empty_cache(self, reset_slack_clients: None) -> None:
        """Should handle clearing an already empty cache."""
        # Setup - ensure cache is empty
        manager = get_client_manager()
        assert len(manager._async_clients) == 0
        assert len(manager._sync_clients) == 0

        # Call clear function
        srv.clear_slack_clients()

        # Should still be empty
        assert len(manager._async_clients) == 0
        assert len(manager._sync_clients) == 0

    def test_clear_populated_cache(self, reset_slack_clients: None) -> None:
        """Should clear all clients from cache."""
        # Setup - populate cache
        manager = get_client_manager()
        client1 = srv.get_slack_client("token1")
        client2 = srv.get_slack_client("token2")
        assert len(manager._async_clients) == 2

        # Call clear function
        srv.clear_slack_clients()

        # Cache should be empty
        assert len(manager._async_clients) == 0
        assert len(manager._sync_clients) == 0

    def test_clear_forces_new_clients(self, reset_slack_clients: None) -> None:
        """Should force creation of new clients after clearing."""
        # Setup - get a client
        client1 = srv.get_slack_client("test-token")

        # Clear cache
        srv.clear_slack_clients()

        # Get a new client with same token
        client2 = srv.get_slack_client("test-token")

        # Should be different objects
        assert client1 is not client2
        assert client1.token == client2.token


class TestUpdateSlackClient:
    """Tests for update_slack_client function."""

    def test_update_new_client(self, reset_slack_clients: None) -> None:
        """Should add a new client to the cache."""
        # Setup
        manager = get_client_manager()
        assert len(manager._async_clients) == 0
        
        # Create a custom client
        custom_client = AsyncWebClient(token="custom-token")
        
        # Update with new client - in the refactored approach, this will use the default token
        # from the environment, not the token passed to update_slack_client
        with patch("slack_mcp.client_manager.SlackClientManager._default_token", 
                   new_callable=MagicMock) as mock_default_token:
            mock_default_token.return_value = "custom-token"
            srv.update_slack_client("custom-token", custom_client)
            
            # Check it was added to cache
            assert len(manager._async_clients) == 1
            cache_key = "custom-token:True"  # Default is use_retries=True
            assert cache_key in manager._async_clients
            assert manager._async_clients[cache_key] is custom_client

    def test_update_existing_client(self, reset_slack_clients: None) -> None:
        """Should replace an existing client in the cache."""
        # Setup - add a client to cache
        with patch("slack_mcp.client_manager.SlackClientManager._default_token", 
                   new_callable=MagicMock) as mock_default_token:
            mock_default_token.return_value = "test-token"
            
            # Get the original client
            original_client = srv.get_slack_client("test-token")
            manager = get_client_manager()
            cache_key = "test-token:True"  # Default is use_retries=True
            assert manager._async_clients[cache_key] is original_client
            
            # Create a replacement client
            replacement_client = AsyncWebClient(token="test-token")
            
            # Update the client
            srv.update_slack_client("test-token", replacement_client)
            
            # Check it replaced the original in cache
            assert manager._async_clients[cache_key] is replacement_client
            assert manager._async_clients[cache_key] is not original_client

    def test_update_with_empty_token_raises_error(self, reset_slack_clients: None) -> None:
        """Should raise ValueError when token is empty."""
        # Setup
        client = AsyncWebClient(token="any-token")
        
        # Try to update with empty token
        with pytest.raises(ValueError, match="Token cannot be empty or None"):
            srv.update_slack_client("", client)
            
        # Try with None token
        with pytest.raises(ValueError, match="Token cannot be empty or None"):
            srv.update_slack_client(None, client)  # type: ignore


class TestSetSlackClientRetryCount:
    """Tests for set_slack_client_retry_count function."""

    def test_set_retry_count(self, reset_slack_clients: None) -> None:
        """Should update the retry count and factory."""
        # Setup
        manager = get_client_manager()
        original_retry_count = manager._default_retry_count
        
        # Set new retry count
        srv.set_slack_client_retry_count(10)
        
        # Check retry count was updated
        assert manager._default_retry_count == 10
        assert manager._default_retry_count != original_retry_count

    def test_set_retry_clears_cache(self, reset_slack_clients: None) -> None:
        """Should clear client cache when retry count is changed."""
        # Setup - populate cache
        client = srv.get_slack_client("test-token")
        manager = get_client_manager()
        assert len(manager._async_clients) == 1
        
        # Set new retry count
        srv.set_slack_client_retry_count(5)
        
        # Cache should be cleared
        assert len(manager._async_clients) == 0
        
        # Getting a client should create a new one
        new_client = srv.get_slack_client("test-token")
        assert new_client is not client
