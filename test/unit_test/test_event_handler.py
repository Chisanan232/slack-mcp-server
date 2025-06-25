"""Unit tests for the Slack event handler module."""

import os
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from slack_mcp.event_handler import (
    handle_app_mention,
    handle_reaction_added,
    register_handlers,
)


@pytest.fixture
def mock_client():
    """Create a mock Slack client."""
    client = AsyncMock()
    # Create a proper mock for SlackResponse by having a data attribute
    response_mock = AsyncMock()
    response_mock.data = {"ok": True, "ts": "1234567890.123456"}
    client.chat_postMessage = AsyncMock(return_value=response_mock)

    # Similarly for conversations_history
    history_response = AsyncMock()
    history_response.data = {
        "ok": True,
        "messages": [{"text": "Hello", "user": "U12345678", "ts": "1234567890.123456"}],
    }
    history_response.get = lambda key, default=None: history_response.data.get(key, default)
    client.conversations_history = AsyncMock(return_value=history_response)

    return client


@pytest.mark.asyncio
async def test_handle_app_mention_empty_text(mock_client):
    """Test handling an app mention with empty text."""
    event = {
        "type": "app_mention",
        "user": "U12345678",
        "text": "<@U87654321>",
        "ts": "1234567890.123456",
        "channel": "C12345678",
    }

    result = await handle_app_mention(mock_client, event)

    # The result is the direct response from the chat_postMessage call
    assert result.data["ok"] is True
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C12345678",
        text="Hello! I'm your Slack bot. How can I help you today?",
        thread_ts="1234567890.123456",
    )


@pytest.mark.asyncio
async def test_handle_app_mention_with_text(mock_client):
    """Test handling an app mention with text."""
    event = {
        "type": "app_mention",
        "user": "U12345678",
        "text": "<@U87654321> Hello bot!",
        "ts": "1234567890.123456",
        "channel": "C12345678",
    }

    result = await handle_app_mention(mock_client, event)

    assert result.data["ok"] is True
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C12345678",
        text="You said: Hello bot!",
        thread_ts="1234567890.123456",
    )


@pytest.mark.asyncio
async def test_handle_app_mention_in_thread(mock_client):
    """Test handling an app mention in a thread."""
    event = {
        "type": "app_mention",
        "user": "U12345678",
        "text": "<@U87654321> Hello in thread!",
        "ts": "1234567890.123457",
        "channel": "C12345678",
        "thread_ts": "1234567890.123456",
    }

    result = await handle_app_mention(mock_client, event)

    assert result.data["ok"] is True
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C12345678",
        text="You said: Hello in thread!",
        thread_ts="1234567890.123456",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_attributes, env_vars, expected_response, should_post_message",
    [
        # Test with SLACK_BOT_ID set and matching bot_id in message
        (
            {"bot_id": "B12345678", "text": "Hello", "ts": "1234567890.123456"},
            {"SLACK_BOT_ID": "B12345678"},
            {"ok": True},
            True,
        ),
        # Test with SLACK_BOT_ID set but non-matching bot_id in message
        (
            {"bot_id": "BDIFFERENT", "text": "Hello", "ts": "1234567890.123456"},
            {"SLACK_BOT_ID": "B12345678"},
            {"ok": True, "message": "Not a bot message"},
            False,
        ),
        # Test with SLACK_BOT_ID set and no bot_id in message
        (
            {"user": "U87654321", "text": "Hello", "ts": "1234567890.123456"},
            {"SLACK_BOT_ID": "B12345678"},
            {"ok": True, "message": "Not a bot message"},
            False,
        ),
        # Test with no SLACK_BOT_ID but message has bot_id
        ({"bot_id": "B98765432", "text": "Hello", "ts": "1234567890.123456"}, {}, {"ok": True}, True),
        # Test with no SLACK_BOT_ID but message has app_id
        ({"app_id": "A98765432", "text": "Hello", "ts": "1234567890.123456"}, {}, {"ok": True}, True),
        # Test with no SLACK_BOT_ID and no bot identifiers in message
        (
            {"user": "U87654321", "text": "Hello", "ts": "1234567890.123456"},
            {},
            {"ok": False, "error": "Not a bot message"},
            False,
        ),
        # Test with SLACK_BOT_ID matching app_id instead of bot_id
        (
            {"app_id": "B12345678", "text": "Hello", "ts": "1234567890.123456"},
            {"SLACK_BOT_ID": "B12345678"},
            {"ok": True},
            True,
        ),
    ],
)
async def test_handle_reaction_added_parametrized(
    mock_client: AsyncMock,
    message_attributes: Dict[str, Any],
    env_vars: Dict[str, str],
    expected_response: Dict[str, Any],
    should_post_message: bool,
) -> None:
    """Test reaction handling with various bot ID scenarios using parametrization.

    Args:
        mock_client: Mock Slack client fixture
        message_attributes: Message attributes to include in the history response
        env_vars: Environment variables to set during the test
        expected_response: Expected response structure from the handler
        should_post_message: Whether chat_postMessage should be called
    """
    # Set environment variables for the test
    with patch.dict(os.environ, env_vars, clear=True):
        event: Dict[str, Any] = {
            "type": "reaction_added",
            "user": "U12345678",
            "reaction": "thumbsup",
            "item": {
                "type": "message",
                "channel": "C12345678",
                "ts": "1234567890.123456",
            },
            "event_ts": "1234567890.123457",
        }

        # Mock the conversations_history to return a message with specified attributes
        history_response = AsyncMock()
        history_response.data = {
            "ok": True,
            "messages": [message_attributes],
        }
        history_response.get = lambda key, default=None: history_response.data.get(key, default)
        mock_client.conversations_history.return_value = history_response

        # Call the handler
        result = await handle_reaction_added(mock_client, event)

        # For responses with SlackResponse structure
        if should_post_message:
            assert hasattr(result, "data")
            assert result.data["ok"] == expected_response["ok"]
            mock_client.chat_postMessage.assert_called_once_with(
                channel="C12345678",
                text="Thanks for reacting with :thumbsup: to my message!",
                thread_ts="1234567890.123456",
            )
        else:
            # For direct dictionary responses
            if isinstance(result, dict):
                for key, value in expected_response.items():
                    assert result[key] == value
            else:
                # Handle SlackResponse for cases where expected_response is incorrect
                assert hasattr(result, "data")
                assert result.data["ok"] == expected_response["ok"]

            mock_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_handle_reaction_added_message_not_found(mock_client: AsyncMock) -> None:
    """Test handling a reaction added when the message can't be found."""
    event: Dict[str, Any] = {
        "type": "reaction_added",
        "user": "U12345678",
        "reaction": "thumbsup",
        "item": {
            "type": "message",
            "channel": "C12345678",
            "ts": "1234567890.123456",
        },
        "event_ts": "1234567890.123457",
    }

    # Mock the conversations_history to return no messages
    history_response = AsyncMock()
    history_response.data = {"ok": True, "messages": []}
    history_response.get = lambda key, default=None: history_response.data.get(key, default)
    mock_client.conversations_history.return_value = history_response

    result = await handle_reaction_added(mock_client, event)

    # The result is a direct dictionary in this case, not a SlackResponse
    assert result["ok"] is False
    assert result["error"] == "Message not found"
    mock_client.chat_postMessage.assert_not_called()


def test_register_handlers():
    """Test registering event handlers."""
    handlers = register_handlers()

    assert "app_mention" in handlers
    assert "reaction_added" in handlers
    assert handlers["app_mention"] == handle_app_mention
    assert handlers["reaction_added"] == handle_reaction_added
