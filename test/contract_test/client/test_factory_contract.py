"""
Contract tests for the SlackClientFactory abstract interface.

These tests verify that any implementation of the SlackClientFactory interface
adheres to the expected contract behavior. They focus on interface behavior
rather than implementation details.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp.client.factory import (
    DefaultSlackClientFactory,
    RetryableSlackClientFactory,
    SlackClientFactory,
)
from slack_mcp.model import SlackPostMessageInput, SlackThreadReplyInput


class SlackClientFactoryContractTest(ABC):
    """
    Base contract test class for SlackClientFactory implementations.

    Any implementation of SlackClientFactory should be able to pass these tests
    if it correctly fulfills the interface contract.
    """

    @abstractmethod
    def factory_class(self) -> Type[SlackClientFactory]:
        """Return the factory class to be tested."""

    @pytest.fixture
    def factory(self):
        """Return a fresh instance of the factory implementation."""
        return self.factory_class()()

    # === CORE CONTRACT REQUIREMENTS ===

    @patch("slack_mcp.client_factory.AsyncWebClient")
    def test_factory_creates_async_web_client(self, mock_async_client_class, factory):
        """
        CONTRACT: A factory must create an AsyncWebClient instance when
        create_async_client is called with a valid token.
        """
        # Setup mock to track instantiation
        mock_instance = MagicMock()
        mock_instance.retry_handlers = []
        mock_async_client_class.return_value = mock_instance

        client = factory.create_async_client("xoxb-valid-test-token")

        # Verify AsyncWebClient was instantiated with correct token
        mock_async_client_class.assert_called_once()
        args, kwargs = mock_async_client_class.call_args
        assert kwargs.get("token") == "xoxb-valid-test-token"

    @patch("slack_mcp.client_factory.WebClient")
    def test_factory_creates_web_client(self, mock_web_client_class, factory):
        """
        CONTRACT: A factory must create a WebClient instance when
        create_sync_client is called with a valid token.
        """
        # Setup mock to track instantiation
        mock_instance = MagicMock()
        mock_instance.retry_handlers = []
        mock_web_client_class.return_value = mock_instance

        client = factory.create_sync_client("xoxb-valid-test-token")

        # Verify WebClient was instantiated with correct token
        mock_web_client_class.assert_called_once()
        args, kwargs = mock_web_client_class.call_args
        assert kwargs.get("token") == "xoxb-valid-test-token"

    @patch("slack_mcp.client_factory.AsyncWebClient")
    @patch("slack_mcp.client_factory.WebClient")
    def test_factory_creates_client_with_provided_token(
        self, mock_web_client_class, mock_async_client_class, factory, monkeypatch
    ):
        """
        CONTRACT: A factory must use the token explicitly provided to it
        when creating clients, rather than falling back to environment
        variables or other sources.
        """
        # Set environment variables that should be ignored when token is provided
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-env-token-should-not-be-used")
        monkeypatch.setenv("SLACK_TOKEN", "xoxb-env-token-should-not-be-used")

        # Setup mocks
        mock_async_instance = MagicMock()
        mock_async_instance.retry_handlers = []
        mock_async_client_class.return_value = mock_async_instance

        mock_sync_instance = MagicMock()
        mock_sync_instance.retry_handlers = []
        mock_web_client_class.return_value = mock_sync_instance

        test_token = "xoxb-explicit-test-token"

        # Test both sync and async clients
        async_client = factory.create_async_client(test_token)
        sync_client = factory.create_sync_client(test_token)

        # Verify correct token was used
        async_args, async_kwargs = mock_async_client_class.call_args
        assert async_kwargs.get("token") == test_token

        sync_args, sync_kwargs = mock_web_client_class.call_args
        assert sync_kwargs.get("token") == test_token

    @patch("slack_mcp.client_factory.AsyncWebClient")
    def test_client_creation_from_input(self, mock_async_client_class, factory, monkeypatch):
        """
        CONTRACT: A factory must be able to create a client from an input object
        and use the default token from environment for the client.
        """
        # Setup mock
        mock_async_instance = MagicMock()
        mock_async_instance.retry_handlers = []
        mock_async_client_class.return_value = mock_async_instance

        test_token = "xoxb-from-env"

        # Set the environment token
        monkeypatch.setenv("SLACK_BOT_TOKEN", test_token)

        # Patch the SlackClientManager._default_token property
        from slack_mcp.client.manager import SlackClientManager

        def mock_env_token(self):
            return test_token

        monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

        # Create input objects without token
        message_input = SlackPostMessageInput(channel="test-channel", text="test message")
        thread_input = SlackThreadReplyInput(
            channel="test-channel", thread_ts="1234.5678", texts=["Reply 1", "Reply 2"]
        )

        # Reset the mock between calls
        inputs = [message_input, thread_input]
        for input_obj in inputs:
            mock_async_client_class.reset_mock()
            client = factory.create_async_client_from_input(input_obj)

            # Verify correct token from environment was used
            mock_async_client_class.assert_called_once()
            args, kwargs = mock_async_client_class.call_args
            assert kwargs.get("token") == test_token

    def test_required_token_error(self, factory, monkeypatch):
        """
        CONTRACT: A factory must raise a ValueError when no token is provided
        and none can be resolved from environment.
        """
        # Ensure no token environment variables are set
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_TOKEN", raising=False)

        # Should raise ValueError when no token is available
        with pytest.raises(ValueError) as excinfo:
            factory.create_async_client()

        assert "token" in str(excinfo.value).lower()

    # === BEHAVIORAL CONTRACT REQUIREMENTS ===

    @pytest.mark.asyncio
    @patch("slack_mcp.client_factory.AsyncWebClient")
    async def test_async_slack_message_behavior(self, mock_async_client_class, factory):
        """
        CONTRACT: A factory must produce AsyncWebClient instances that can
        correctly send messages to Slack channels.
        """
        test_token = "xoxb-async-test-token"
        test_channel = "C123456789"
        test_message = "Hello from async test"

        # Mock response data
        expected_response = {
            "ok": True,
            "channel": test_channel,
            "ts": "1234.5678",
            "message": {"text": test_message, "user": "U123456"},
        }

        # Create a mock AsyncWebClient that returns our expected response
        mock_instance = AsyncMock()
        mock_instance.retry_handlers = []
        mock_instance.chat_postMessage = AsyncMock(return_value=expected_response)
        mock_async_client_class.return_value = mock_instance

        # Create client using factory
        client = factory.create_async_client(test_token)

        # Send message
        response = await client.chat_postMessage(channel=test_channel, text=test_message)

        # Verify message was sent with correct parameters
        client.chat_postMessage.assert_called_once()
        args, kwargs = client.chat_postMessage.call_args
        assert kwargs.get("channel") == test_channel
        assert kwargs.get("text") == test_message
        assert response == expected_response

    @patch("slack_mcp.client_factory.WebClient")
    def test_sync_slack_message_behavior(self, mock_web_client_class, factory):
        """
        CONTRACT: A factory must produce WebClient instances that can
        correctly send messages to Slack channels.
        """
        test_token = "xoxb-sync-test-token"
        test_channel = "C123456789"
        test_message = "Hello from sync test"

        # Mock response data
        expected_response = {
            "ok": True,
            "channel": test_channel,
            "ts": "1234.5678",
            "message": {"text": test_message, "user": "U123456"},
        }

        # Create a mock WebClient that returns our expected response
        mock_instance = MagicMock()
        mock_instance.retry_handlers = []
        mock_instance.chat_postMessage = MagicMock(return_value=expected_response)
        mock_web_client_class.return_value = mock_instance

        # Create client using factory
        client = factory.create_sync_client(test_token)

        # Send message
        response = client.chat_postMessage(channel=test_channel, text=test_message)

        # Verify message was sent with correct parameters
        client.chat_postMessage.assert_called_once()
        args, kwargs = client.chat_postMessage.call_args
        assert kwargs.get("channel") == test_channel
        assert kwargs.get("text") == test_message
        assert response == expected_response


class TestDefaultSlackClientFactoryContract(SlackClientFactoryContractTest):
    """Concrete contract tests for DefaultSlackClientFactory."""

    def factory_class(self) -> Type[SlackClientFactory]:
        """Return the DefaultSlackClientFactory class."""
        return DefaultSlackClientFactory


class TestRetryableSlackClientFactoryContract(SlackClientFactoryContractTest):
    """Concrete contract tests for RetryableSlackClientFactory.

    This ensures that the retry-enhanced factory correctly implements
    the SlackClientFactory contract.
    """

    def factory_class(self) -> Type[SlackClientFactory]:
        """Return the RetryableSlackClientFactory class."""
        return RetryableSlackClientFactory


# === MOCK IMPLEMENTATION FOR TESTING ===


class MockSlackClientFactory(SlackClientFactory):
    """A mock implementation of SlackClientFactory used to validate
    that the contract tests properly catch deviations.

    This implementation deliberately violates the contract by always
    using a fixed token instead of respecting the provided one.
    """

    def create_async_client(self, token: Optional[str] = None) -> AsyncWebClient:
        """Create an async Slack client.

        This implementation deliberately ignores the provided token.
        """
        # Deliberately violate contract by using a fixed token
        return AsyncWebClient(token="xoxb-fixed-token")

    def create_sync_client(self, token: Optional[str] = None) -> WebClient:
        """Create a sync Slack client.

        This implementation deliberately ignores the provided token.
        """
        # Deliberately violate contract by using a fixed token
        return WebClient(token="xoxb-fixed-token")

    def create_async_client_from_input(self, input_obj: Any) -> AsyncWebClient:
        """Create an async client from an input object.

        This implementation deliberately ignores any token in the input.
        """
        # Deliberately violate contract by using a fixed token
        return self.create_async_client()


@pytest.mark.xfail(reason="Mock implementation deliberately violates contract")
class TestMockSlackClientFactoryFailsContract(SlackClientFactoryContractTest):
    """A test class that demonstrates the contract tests will fail
    for implementations that don't respect the contract.

    This class is marked to expect failures since the MockSlackClientFactory
    deliberately violates the contract by not using provided tokens.
    """

    def factory_class(self) -> Type[SlackClientFactory]:
        """Return the MockSlackClientFactory class."""
        return MockSlackClientFactory
