"""
Contract tests for the SlackClientFactory abstract interface.

These tests verify that any implementation of the SlackClientFactory interface
adheres to the expected contract behavior. They focus on interface behavior
rather than implementation details.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type

import pytest
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp.client_factory import DefaultSlackClientFactory, SlackClientFactory
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

    def test_factory_creates_async_web_client(self, factory):
        """
        CONTRACT: A factory must create an AsyncWebClient instance when
        create_async_client is called with a valid token.
        """
        client = factory.create_async_client("xoxb-valid-test-token")
        assert isinstance(client, AsyncWebClient)

    def test_factory_creates_web_client(self, factory):
        """
        CONTRACT: A factory must create a WebClient instance when
        create_sync_client is called with a valid token.
        """
        client = factory.create_sync_client("xoxb-valid-test-token")
        assert isinstance(client, WebClient)

    def test_factory_creates_client_with_provided_token(self, factory):
        """
        CONTRACT: A factory must use the provided token when creating clients.
        """
        test_token = "xoxb-provided-token"
        async_client = factory.create_async_client(test_token)
        sync_client = factory.create_sync_client(test_token)

        assert async_client.token == test_token
        assert sync_client.token == test_token

    def test_client_creation_from_input(self, factory, monkeypatch):
        """
        CONTRACT: A factory must be able to create clients from standard input objects.
        """
        # Set safe fallback token to test empty/missing token case
        monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fallback-token")

        # Test with SlackPostMessageInput
        post_message_input = SlackPostMessageInput(
            token="xoxb-test-post-message", channel="test-channel", text="Test message"
        )

        async_client_1 = factory.create_async_client_from_input(post_message_input)
        assert isinstance(async_client_1, AsyncWebClient)
        assert async_client_1.token == "xoxb-test-post-message"

        # Test with SlackThreadReplyInput
        thread_reply_input = SlackThreadReplyInput(
            token="xoxb-test-thread-reply", channel="test-channel", thread_ts="1234.5678", texts=["Test reply"]
        )

        async_client_2 = factory.create_async_client_from_input(thread_reply_input)
        assert isinstance(async_client_2, AsyncWebClient)
        assert async_client_2.token == "xoxb-test-thread-reply"

        # Test with input that has no token
        no_token_input = SlackPostMessageInput(channel="test-channel", text="Test with no token")

        async_client_3 = factory.create_async_client_from_input(no_token_input)
        assert isinstance(async_client_3, AsyncWebClient)
        # Should use fallback token
        assert async_client_3.token == "xoxb-fallback-token"

    def test_required_token_error(self, factory, monkeypatch):
        """
        CONTRACT: A factory must raise a ValueError when no token
        is available and one is required.
        """
        # Clear environment tokens
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_TOKEN", raising=False)

        # Should raise ValueError when no token is provided
        with pytest.raises(ValueError) as excinfo:
            factory.create_async_client()

        assert "token" in str(excinfo.value).lower()

    # === BEHAVIORAL CONTRACTS ===

    @pytest.mark.asyncio
    async def test_async_slack_message_behavior(self, factory, monkeypatch):
        """
        CONTRACT: A factory must produce clients that can be used to send messages
        in the expected manner using async patterns.
        """
        test_token = "xoxb-test-async"
        test_channel = "C12345678"
        test_text = "Test message"

        # Create a post message input
        input_obj = SlackPostMessageInput(token=test_token, channel=test_channel, text=test_text)

        # Mock async client to verify expected behavior
        class MockAsyncWebClient:
            def __init__(self, token):
                self.token = token
                self.chat_postMessage_called = False
                self.last_args = None

            async def chat_postMessage(self, **kwargs):
                self.chat_postMessage_called = True
                self.last_args = kwargs
                return {"ok": True, "channel": kwargs.get("channel"), "ts": "1234.5678"}

        # Patch AsyncWebClient
        monkeypatch.setattr("slack_mcp.client_factory.AsyncWebClient", MockAsyncWebClient)

        # Get client from factory and use it
        client = factory.create_async_client_from_input(input_obj)
        response = await client.chat_postMessage(channel=input_obj.channel, text=input_obj.text)

        # Verify the contract behavior
        assert client.chat_postMessage_called
        assert client.last_args["channel"] == test_channel
        assert client.last_args["text"] == test_text
        assert response["ok"] is True
        assert response["ts"] == "1234.5678"

    def test_sync_slack_message_behavior(self, factory, monkeypatch):
        """
        CONTRACT: A factory must produce clients that can be used to send messages
        in the expected manner using sync patterns.
        """
        test_token = "xoxb-test-sync"
        test_channel = "C12345678"
        test_text = "Test message"

        # Create a post message input
        input_obj = SlackPostMessageInput(token=test_token, channel=test_channel, text=test_text)

        # Mock sync client to verify expected behavior
        class MockWebClient:
            def __init__(self, token):
                self.token = token
                self.chat_postMessage_called = False
                self.last_args = None

            def chat_postMessage(self, **kwargs):
                self.chat_postMessage_called = True
                self.last_args = kwargs
                return {"ok": True, "channel": kwargs.get("channel"), "ts": "1234.5678"}

        # Patch WebClient
        monkeypatch.setattr("slack_mcp.client_factory.WebClient", MockWebClient)

        # Create client using factory with explicit token instead of input
        client = factory.create_sync_client(test_token)
        response = client.chat_postMessage(channel=test_channel, text=test_text)

        # Verify the contract behavior
        assert client.chat_postMessage_called
        assert client.last_args["channel"] == test_channel
        assert client.last_args["text"] == test_text
        assert response["ok"] is True
        assert response["ts"] == "1234.5678"


class TestDefaultSlackClientFactoryContract(SlackClientFactoryContractTest):
    """Concrete contract tests for DefaultSlackClientFactory."""

    def factory_class(self):
        return DefaultSlackClientFactory


# === MOCK IMPLEMENTATION FOR TESTING ===


class MockSlackClientFactory(SlackClientFactory):
    """
    A mock implementation of SlackClientFactory used to validate
    that the contract tests properly catch deviations.

    This implementation deliberately violates the contract by always
    using a fixed token instead of respecting the provided one.
    """

    def create_async_client(self, token: Optional[str] = None) -> AsyncWebClient:
        """Create an async Slack client."""
        # Always use a fixed token, ignoring the provided one
        return AsyncWebClient(token="xoxb-mock-fixed-token")

    def create_sync_client(self, token: Optional[str] = None) -> WebClient:
        """Create a sync Slack client."""
        # Always use a fixed token, ignoring the provided one
        return WebClient(token="xoxb-mock-fixed-token")

    def create_async_client_from_input(self, input_obj: Any) -> AsyncWebClient:
        """Create an async client from an input object."""
        # Always use a fixed token, ignoring the input object
        return self.create_async_client()


@pytest.mark.xfail(reason="Mock implementation deliberately violates contract")
class TestMockSlackClientFactoryFailsContract(SlackClientFactoryContractTest):
    """
    A test class that demonstrates the contract tests will fail
    for implementations that don't respect the contract.

    This class is marked to expect failures since the MockSlackClientFactory
    deliberately violates the contract by not using provided tokens.
    """

    def factory_class(self):
        return MockSlackClientFactory
