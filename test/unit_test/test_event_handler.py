"""Unit tests for the Slack event handler module."""

import os
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
async def test_handle_reaction_added_bot_message_with_id(mock_client):
    """Test handling a reaction added to a bot message when BOT_ID is available."""
    # Set environment variable
    with patch.dict(os.environ, {"SLACK_BOT_ID": "B12345678"}):
        event = {
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

        # Mock the conversations_history to return a message from our bot
        history_response = AsyncMock()
        history_response.data = {
            "ok": True,
            "messages": [{"text": "Hello", "bot_id": "B12345678", "ts": "1234567890.123456"}],
        }
        history_response.get = lambda key, default=None: history_response.data.get(key, default)
        mock_client.conversations_history.return_value = history_response

        result = await handle_reaction_added(mock_client, event)

        assert result.data["ok"] is True
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C12345678",
            text="Thanks for reacting with :thumbsup: to my message!",
            thread_ts="1234567890.123456",
        )


@pytest.mark.asyncio
async def test_handle_reaction_added_not_bot_message(mock_client):
    """Test handling a reaction added to a non-bot message."""
    # Set environment variable
    with patch.dict(os.environ, {"SLACK_BOT_ID": "B12345678"}):
        event = {
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

        # Mock the conversations_history to return a message not from our bot
        history_response = AsyncMock()
        history_response.data = {
            "ok": True,
            "messages": [{"text": "Hello", "user": "U87654321", "ts": "1234567890.123456"}],
        }
        history_response.get = lambda key, default=None: history_response.data.get(key, default)
        mock_client.conversations_history.return_value = history_response

        result = await handle_reaction_added(mock_client, event)

        # The result is a direct dictionary in this case, not a SlackResponse
        assert result["ok"] is True
        assert result["message"] == "Not a bot message"
        mock_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_handle_reaction_added_message_not_found(mock_client):
    """Test handling a reaction added when the message can't be found."""
    event = {
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
