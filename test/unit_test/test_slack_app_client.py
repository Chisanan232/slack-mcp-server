"""Unit tests for Slack client functions in slack_app.py."""

from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.web.async_client import AsyncWebClient

from slack_mcp import slack_app
from slack_mcp.client.manager import SlackClientManager


@pytest.fixture
def clean_global_client() -> Generator[None, None, None]:
    """Reset the global slack_client variable after each test."""
    # Save original
    original_client = slack_app.slack_client

    # Reset for test
    slack_app.slack_client = None

    # Also reset the SlackClientManager singleton
    with patch("slack_mcp.client.manager.SlackClientManager._instance", None):
        yield

    # Restore original
    slack_app.slack_client = original_client


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove Slack token environment variables."""
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_TOKEN", raising=False)


class TestInitializeSlackClient:
    """Tests for initialize_slack_client function."""

    def test_initialize_with_explicit_token(self, clean_global_client: None) -> None:
        """Should initialize client with explicitly provided token."""
        mock_client = MagicMock(spec=AsyncWebClient)
        mock_client.token = "test-token-123"

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            client = slack_app.initialize_slack_client(token="test-token-123")

        assert client is mock_client
        assert client.token == "test-token-123"
        assert slack_app.slack_client is client  # Global variable should be set
        mock_manager.get_async_client.assert_called_once_with("test-token-123", False)

    def test_initialize_with_bot_token_env(self, clean_global_client: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use SLACK_BOT_TOKEN from environment when no token provided."""
        monkeypatch.setenv("SLACK_BOT_TOKEN", "env-bot-token")

        mock_client = MagicMock(spec=AsyncWebClient)
        mock_client.token = "env-bot-token"

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            client = slack_app.initialize_slack_client()

        assert client.token == "env-bot-token"
        assert slack_app.slack_client is client
        mock_manager.get_async_client.assert_called_once_with(None, False)

    def test_initialize_with_fallback_token_env(
        self, clean_global_client: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use SLACK_TOKEN from environment when no SLACK_BOT_TOKEN or explicit token provided."""
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.setenv("SLACK_TOKEN", "fallback-token")

        mock_client = MagicMock(spec=AsyncWebClient)
        mock_client.token = "fallback-token"

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            client = slack_app.initialize_slack_client()

        assert client.token == "fallback-token"
        assert slack_app.slack_client is client
        mock_manager.get_async_client.assert_called_once_with(None, False)

    def test_initialize_token_resolution_priority(
        self, clean_global_client: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should prioritize explicit token over environment variables."""
        # Set both environment variables
        monkeypatch.setenv("SLACK_BOT_TOKEN", "env-bot-token")
        monkeypatch.setenv("SLACK_TOKEN", "fallback-token")

        mock_client = MagicMock(spec=AsyncWebClient)
        mock_client.token = "explicit-token"

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            # Provide explicit token
            client = slack_app.initialize_slack_client(token="explicit-token")

        # Explicit token should take precedence
        assert client.token == "explicit-token"
        mock_manager.get_async_client.assert_called_once_with("explicit-token", False)

    def test_initialize_without_token_raises_error(self, clean_global_client: None, clean_env: None) -> None:
        """Should raise ValueError when no token is available."""
        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.side_effect = ValueError("Slack token not found")

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            with pytest.raises(ValueError) as excinfo:
                slack_app.initialize_slack_client()

        assert "Slack token not found" in str(excinfo.value)
        assert slack_app.slack_client is None  # Global variable should remain None

    def test_initialize_with_negative_retry_raises_error(self, clean_global_client: None) -> None:
        """Should raise ValueError when retry count is negative."""
        with pytest.raises(ValueError) as excinfo:
            slack_app.initialize_slack_client(token="test-token", retry=-1)

        assert "Retry count must be non-negative" in str(excinfo.value)
        assert slack_app.slack_client is None  # Global variable should remain None

    def test_initialize_with_zero_retry(self, clean_global_client: None) -> None:
        """Should create standard client when retry=0."""
        mock_client = MagicMock(spec=AsyncWebClient)

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            client = slack_app.initialize_slack_client(token="test-token", retry=0)

        assert isinstance(client, AsyncWebClient)
        mock_manager.get_async_client.assert_called_once_with("test-token", False)
        # The default AsyncWebClient may have some built-in retry handlers regardless of our retry setting
        # We're just checking it was created correctly without using RetryableSlackClientFactory

    def test_initialize_with_positive_retry(self, clean_global_client: None) -> None:
        """Should create client with retry capability when retry>0."""
        # Create a mock client to be returned
        mock_client = MagicMock(spec=AsyncWebClient)

        # Mock the SlackClientManager's get_async_client method
        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0  # Different from what we'll set
        mock_manager.get_async_client.return_value = mock_client

        # Patch get_client_manager to return our mock
        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            client = slack_app.initialize_slack_client(token="test-token", retry=3)

        # Verify manager was used correctly
        assert client is mock_client
        mock_manager.update_retry_count.assert_called_once_with(3)
        mock_manager.get_async_client.assert_called_once_with("test-token", True)

    def test_initialize_overwrites_existing_client(self, clean_global_client: None) -> None:
        """Should replace existing global client when called multiple times."""
        mock_first_client = MagicMock(spec=AsyncWebClient)
        mock_first_client.token = "first-token"

        mock_second_client = MagicMock(spec=AsyncWebClient)
        mock_second_client.token = "second-token"

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.side_effect = [mock_first_client, mock_second_client]

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            # Initialize first client
            first_client = slack_app.initialize_slack_client(token="first-token")

            # Initialize second client
            second_client = slack_app.initialize_slack_client(token="second-token")

        # Second client should replace the first one
        assert slack_app.slack_client is second_client
        assert slack_app.slack_client is not first_client
        assert slack_app.slack_client.token == "second-token"


class TestGetSlackClient:
    """Tests for get_slack_client function."""

    def test_get_initialized_client(self, clean_global_client: None) -> None:
        """Should return the initialized client."""
        mock_client = MagicMock(spec=AsyncWebClient)

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            # Initialize the client first
            slack_app.initialize_slack_client(token="test-token")

            # Then get it
            client = slack_app.get_slack_client()

        assert client is mock_client

    def test_get_uninitialized_client_raises_error(self, clean_global_client: None) -> None:
        """Should raise ValueError when client is not initialized."""
        with pytest.raises(ValueError) as excinfo:
            slack_app.get_slack_client()

        assert "Slack client not initialized" in str(excinfo.value)

    def test_get_client_after_reinitialization(self, clean_global_client: None) -> None:
        """Should return the most recently initialized client."""
        mock_first_client = MagicMock(spec=AsyncWebClient)
        mock_second_client = MagicMock(spec=AsyncWebClient)

        mock_manager = MagicMock(spec=SlackClientManager)
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.side_effect = [mock_first_client, mock_second_client]

        with patch("slack_mcp.slack_app.get_client_manager", return_value=mock_manager):
            # Initialize first client
            slack_app.initialize_slack_client(token="first-token")

            # Initialize second client
            slack_app.initialize_slack_client(token="second-token")

            # Get client should return the second one
            client = slack_app.get_slack_client()

        assert client is mock_second_client
