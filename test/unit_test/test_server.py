"""Unit tests for :pymod:`slack_mcp.server`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Final, Optional

import pytest

import slack_mcp.server as srv
from slack_mcp.model import (
    SlackAddReactionsInput,
    SlackPostMessageInput,
    SlackReadChannelMessagesInput,
    SlackReadEmojisInput,
    SlackReadThreadMessagesInput,
    SlackThreadReplyInput,
    _BaseInput,
)

# Ensure pytest-asyncio plugin is available for async tests
pytest_plugins = ["pytest_asyncio"]


class _FakeSlackResponse:  # noqa: D101 – minimal stub
    """Stand-in for :class:`slack_sdk.web.slack_response.SlackResponse`."""

    def __init__(self, data: dict[str, Any]):  # noqa: D401 – docstring short.
        self.data: Final[dict[str, Any]] = data


class _DummyAsyncWebClient:  # noqa: D101 – simple stub
    """Minimal stub replacing :class:`slack_sdk.web.async_client.AsyncWebClient`."""

    def __init__(self, *args: Any, **kwargs: Any):  # noqa: D401 – docstring short.
        # Accept and ignore all initialisation parameters.
        self.token = kwargs.get("token", "dummy-token")
        pass

    async def chat_postMessage(self, *, channel: str, text: str, thread_ts: Optional[str] = None, **_: Any):
        """Simulate posting a message."""
        response = {
            "ok": True,
            "channel": channel,
            "text": text,
            "ts": "1620000000.000000",
        }
        if thread_ts:
            response["thread_ts"] = thread_ts
        return _FakeSlackResponse(response)

    async def conversations_replies(self, *, channel: str, ts: str, limit: Optional[int] = None, **_: Any):
        """Simulate fetching thread replies."""
        # Create a response with a parent message and replies
        messages = [
            {"text": "Thread parent", "ts": ts},
        ]
        
        return _FakeSlackResponse(
            {
                "ok": True,
                "channel": channel,
                "ts": ts,
                "messages": messages,
            }
        )

    async def conversations_history(self, *, channel: str, limit: Optional[int] = None, **_: Any):
        """Simulate fetching channel history."""
        # Create a response with channel messages
        messages = [
            {"type": "message", "text": "Test message 0", "ts": "165612340.00000", "user": "U123450"},
            {"type": "message", "text": "Test message 1", "ts": "165612341.00000", "user": "U123451"},
            {"type": "message", "text": "Test message 2", "ts": "165612342.00000", "user": "U123452"},
        ]
        
        # If limit is specified, respect it
        if limit is not None:
            messages = messages[:limit]
        
        return _FakeSlackResponse(
            {
                "ok": True,
                "channel": channel,
                "messages": messages,
                "has_more": False,
                "response_metadata": {"next_cursor": ""},
            }
        )

    async def reactions_add(self, *, channel: str, timestamp: str, name: str, **_: Any):
        """Simulate adding a reaction."""
        return _FakeSlackResponse(
            {
                "ok": True,
                "channel": channel,
                "timestamp": timestamp,
                "name": name,
            }
        )

    async def emoji_list(self, **_: Any):
        """Simulate fetching emoji list."""
        return _FakeSlackResponse(
            {
                "ok": True,
                "emoji": {
                    "aliases": {
                        "thumbsup": "+1",
                        "smile": "grinning",
                    },
                    "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
                    "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
                },
            }
        )


@pytest.fixture(autouse=True)
def _patch_slack_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch :pyclass:`AsyncWebClient` with the dummy implementation for tests."""
    # Patch the AsyncWebClient class
    monkeypatch.setattr("slack_mcp.server.AsyncWebClient", _DummyAsyncWebClient)

    # Patch the SlackClientManager's client caches
    from slack_mcp.client_manager import SlackClientManager
    
    # Create a mock instance with empty caches
    mock_manager = SlackClientManager()
    mock_manager._async_clients = {}
    mock_manager._sync_clients = {}
    
    # Set it as the singleton instance
    monkeypatch.setattr("slack_mcp.client_manager.SlackClientManager._instance", mock_manager)
    
    # Mock the default token property by creating a new property that returns our test token
    default_token = "xoxb-default-test-token"
    
    def mock_default_token(self):
        return default_token
    
    # Replace the property with our mock
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_default_token))

    # Also patch the AsyncWebClient in the client_factory module
    from slack_mcp import client_factory

    monkeypatch.setattr(client_factory, "AsyncWebClient", _DummyAsyncWebClient)
    monkeypatch.setattr(client_factory, "WebClient", _DummyAsyncWebClient)  # Use same mock for sync client

    # Default implementation for get_slack_client that works for most tests
    # Tests that need to test specific token behavior will override this
    original_get_slack_client = srv.get_slack_client

    # Store the original function in a module-level variable for tests to access
    global ORIGINAL_GET_SLACK_CLIENT
    ORIGINAL_GET_SLACK_CLIENT = original_get_slack_client

    def patched_get_slack_client(token=None):
        """Return a dummy client for most tests, bypassing token validation."""
        if token:
            return _DummyAsyncWebClient(token=token)
        return _DummyAsyncWebClient(token="xoxb-default-test-token")

    # Patch the _get_default_client function to return a dummy client
    def patched_get_default_client():
        """Return a dummy client for tests, bypassing SlackClientManager."""
        return _DummyAsyncWebClient(token="xoxb-default-test-token")

    # Apply the patches
    monkeypatch.setattr("slack_mcp.server.get_slack_client", patched_get_slack_client)
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

# Create a global reference to the original function that can be restored in tests
ORIGINAL_GET_SLACK_CLIENT: Callable[[Optional[str]], Any] = None  # type: ignore

aSYNC_TOKEN_ENV_VARS = ("SLACK_BOT_TOKEN", "SLACK_TOKEN")


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_send_slack_message_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")
    
    # Update the mock default token property
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_env_token(self):
        return "xoxb-env-token"
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))
    
    # Update the _get_default_client function to use our env token
    def patched_get_default_client():
        return _DummyAsyncWebClient(token="xoxb-env-token")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

    result = await srv.send_slack_message(input_params=SlackPostMessageInput(channel="#general", text="Hello"))
    assert result == {"ok": True, "channel": "#general", "text": "Hello", "ts": "1620000000.000000"}


@pytest.mark.asyncio
async def test_send_slack_message_param() -> None:
    """Message should be sent successfully with default token."""
    result = await srv.send_slack_message(
        input_params=SlackPostMessageInput(channel="C123", text="Hi")
    )
    assert result == {"ok": True, "channel": "C123", "text": "Hi", "ts": "1620000000.000000"}


@pytest.mark.asyncio
async def test_send_slack_message_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    # Remove environment variables
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Make _get_default_client raise ValueError when no token is found
    def patched_get_default_client():
        raise ValueError("Slack token not found. Please provide a token or set environment variables.")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)
    
    # Update the mock default token property to return None
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_none_token(self):
        return None
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.send_slack_message(input_params=SlackPostMessageInput(channel="#general", text="Hello"))


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_thread_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")
    
    # Update the mock default token property
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_env_token(self):
        return "xoxb-env-token"
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))
    
    # Update the _get_default_client function to use our env token
    def patched_get_default_client():
        return _DummyAsyncWebClient(token="xoxb-env-token")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="#general", thread_ts="1620000000.000000")
    )
    assert result == {
        "ok": True,
        "channel": "#general",
        "ts": "1620000000.000000",
        "messages": [{"text": "Thread parent", "ts": "1620000000.000000"}],
    }


@pytest.mark.asyncio
async def test_read_thread_messages_param() -> None:
    """Thread messages should be read successfully with default token."""
    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1620000000.000000")
    )
    assert result == {
        "ok": True,
        "channel": "C123",
        "ts": "1620000000.000000",
        "messages": [{"text": "Thread parent", "ts": "1620000000.000000"}],
    }


@pytest.mark.asyncio
async def test_read_thread_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Make _get_default_client raise ValueError when no token is found
    def patched_get_default_client():
        raise ValueError("Slack token not found. Please provide a token or set environment variables.")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)
    
    # Update the mock default token property to return None
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_none_token(self):
        return None
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.read_thread_messages(
            input_params=SlackReadThreadMessagesInput(channel="#general", thread_ts="1620000000.000000")
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_slack_channel_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")
    
    # Update the mock default token property
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_env_token(self):
        return "xoxb-env-token"
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))
    
    # Update the _get_default_client function to use our env token
    def patched_get_default_client():
        return _DummyAsyncWebClient(token="xoxb-env-token")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="#general"))
    assert result["ok"] is True
    assert result["channel"] == "#general"
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) > 0
    assert "has_more" in result
    assert "response_metadata" in result


@pytest.mark.asyncio
async def test_read_slack_channel_messages_limit() -> None:
    """Channel messages should be limited by the limit parameter."""
    result = await srv.read_slack_channel_messages(
        input_params=SlackReadChannelMessagesInput(channel="#general", limit=1)
    )
    assert result == {
        "ok": True,
        "channel": "#general",
        "messages": [{"type": "message", "text": "Test message 0", "ts": "165612340.00000", "user": "U123450"}],
        "has_more": False,
        "response_metadata": {"next_cursor": ""},
    }


@pytest.mark.asyncio
async def test_read_slack_channel_messages_param() -> None:
    """Channel messages should be read successfully with default token."""
    result = await srv.read_slack_channel_messages(
        input_params=SlackReadChannelMessagesInput(channel="C123")
    )
    assert result == {
        "ok": True,
        "channel": "C123",
        "messages": [
            {"type": "message", "text": "Test message 0", "ts": "165612340.00000", "user": "U123450"},
            {"type": "message", "text": "Test message 1", "ts": "165612341.00000", "user": "U123451"},
            {"type": "message", "text": "Test message 2", "ts": "165612342.00000", "user": "U123452"},
        ],
        "has_more": False,
        "response_metadata": {"next_cursor": ""},
    }


@pytest.mark.asyncio
async def test_read_slack_channel_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Make _get_default_client raise ValueError when no token is found
    def patched_get_default_client():
        raise ValueError("Slack token not found. Please provide a token or set environment variables.")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)
    
    # Update the mock default token property to return None
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_none_token(self):
        return None
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="#general"))


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_send_slack_thread_reply_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")
    
    # Update the mock default token property
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_env_token(self):
        return "xoxb-env-token"
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))
    
    # Update the _get_default_client function to use our env token
    def patched_get_default_client():
        return _DummyAsyncWebClient(token="xoxb-env-token")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="#general", thread_ts=thread_ts, texts=["Hello"])
    )
    assert result == {
        "responses": [
            {
                "ok": True,
                "channel": "#general",
                "text": "Hello",
                "thread_ts": thread_ts,
                "ts": "1620000000.000000",
            }
        ]
    }


@pytest.mark.asyncio
async def test_send_slack_thread_reply_param() -> None:
    """Thread replies should be sent successfully with default token."""
    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="C123", thread_ts=thread_ts, texts=["Hello"])
    )
    assert result == {
        "responses": [
            {
                "ok": True,
                "channel": "C123",
                "text": "Hello",
                "thread_ts": thread_ts,
                "ts": "1620000000.000000",
            }
        ]
    }


@pytest.mark.asyncio
async def test_send_slack_thread_reply_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Make _get_default_client raise ValueError when no token is found
    def patched_get_default_client():
        raise ValueError("Slack token not found. Please provide a token or set environment variables.")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)
    
    # Update the mock default token property to return None
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_none_token(self):
        return None
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    thread_ts = "1620000000.000000"
    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.send_slack_thread_reply(
            input_params=SlackThreadReplyInput(channel="#general", thread_ts=thread_ts, texts=["Hello"])
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_slack_emojis_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")
    
    # Update the mock default token property
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_env_token(self):
        return "xoxb-env-token"
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))
    
    # Update the _get_default_client function to use our env token
    def patched_get_default_client():
        return _DummyAsyncWebClient(token="xoxb-env-token")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

    result = await srv.read_slack_emojis(input_params=SlackReadEmojisInput())
    assert result == {
        "ok": True,
        "emoji": {
            "aliases": {
                "thumbsup": "+1",
                "smile": "grinning",
            },
            "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
            "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
        },
    }


@pytest.mark.asyncio
async def test_read_slack_emojis_param() -> None:
    """Emojis should be read successfully with default token."""
    result = await srv.read_slack_emojis(input_params=SlackReadEmojisInput())
    assert result == {
        "ok": True,
        "emoji": {
            "aliases": {
                "thumbsup": "+1",
                "smile": "grinning",
            },
            "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
            "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
        },
    }


@pytest.mark.asyncio
async def test_read_slack_emojis_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Make _get_default_client raise ValueError when no token is found
    def patched_get_default_client():
        raise ValueError("Slack token not found. Please provide a token or set environment variables.")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)
    
    # Update the mock default token property to return None
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_none_token(self):
        return None
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.read_slack_emojis(input_params=SlackReadEmojisInput())


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_add_slack_reactions_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")
    
    # Update the mock default token property
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_env_token(self):
        return "xoxb-env-token"
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))
    
    # Update the _get_default_client function to use our env token
    def patched_get_default_client():
        return _DummyAsyncWebClient(token="xoxb-env-token")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)

    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="#general", timestamp=timestamp, emojis=["thumbsup"])
    )
    assert result == {
        "responses": [
            {
                "ok": True,
                "channel": "#general",
                "timestamp": timestamp,
                "name": "thumbsup",
            }
        ]
    }


@pytest.mark.asyncio
async def test_add_slack_reactions_param() -> None:
    """Reactions should be added successfully with default token."""
    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="C123", timestamp=timestamp, emojis=["thumbsup"])
    )
    assert result == {
        "responses": [
            {
                "ok": True,
                "channel": "C123",
                "timestamp": timestamp,
                "name": "thumbsup",
            }
        ]
    }


@pytest.mark.asyncio
async def test_add_slack_reactions_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Make _get_default_client raise ValueError when no token is found
    def patched_get_default_client():
        raise ValueError("Slack token not found. Please provide a token or set environment variables.")
    
    monkeypatch.setattr("slack_mcp.server._get_default_client", patched_get_default_client)
    
    # Update the mock default token property to return None
    from slack_mcp.client_manager import SlackClientManager
    
    def mock_none_token(self):
        return None
    
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    timestamp = "1620000000.000000"
    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.add_slack_reactions(
            input_params=SlackAddReactionsInput(channel="#general", timestamp=timestamp, emojis=["thumbsup"])
        )
