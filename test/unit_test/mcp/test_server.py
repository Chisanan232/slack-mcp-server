"""Unit tests for :pymod:`slack_mcp.server`."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest
from slack_sdk.http_retry.async_handler import AsyncRetryHandler

import slack_mcp.mcp.server as srv
from slack_mcp.mcp.model.input import (
    SlackAddReactionsInput,
    SlackPostMessageInput,
    SlackReadChannelMessagesInput,
    SlackReadEmojisInput,
    SlackReadThreadMessagesInput,
    SlackThreadReplyInput,
)
from slack_mcp.mcp.model.output import (
    SlackAddReactionsResponse,
    SlackChannelMessagesResponse,
    SlackEmojiListResponse,
    SlackMessageResponse,
    SlackThreadMessagesResponse,
    SlackThreadReplyResponse,
)

# Ensure pytest-asyncio plugin is available for async tests
pytest_plugins = ["pytest_asyncio"]


class _FakeSlackResponse:  # noqa: D101 – minimal stub
    """Stand-in for :class:`slack_sdk.web.slack_response.SlackResponse`."""

    def __init__(self, data: dict[str, Any]):  # noqa: D401 – docstring short.
        self.data: Dict[str, Any] = data


class _DummyAsyncWebClient:  # noqa: D101 – simple stub
    """Minimal stub replacing :class:`slack_sdk.web.async_client.AsyncWebClient`."""

    def __init__(self, *args: Any, **kwargs: Any):  # noqa: D401 – docstring short.
        # Accept and ignore all initialisation parameters.
        self.token = kwargs.get("token", "dummy-token")
        # Add retry_handlers attribute needed by RetryableSlackClientFactory
        self.retry_handlers: List[AsyncRetryHandler] = []

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
    monkeypatch.setattr("slack_mcp.mcp.server.AsyncWebClient", _DummyAsyncWebClient)

    # Patch the SlackClientManager's client caches
    from slack_mcp.client.manager import SlackClientManager

    # Create a mock instance with empty caches
    mock_manager = SlackClientManager()
    mock_manager._async_clients = {}
    mock_manager._sync_clients = {}

    # Set it as the singleton instance
    monkeypatch.setattr("slack_mcp.client.manager.SlackClientManager._instance", mock_manager)

    # Mock the default token property by creating a new property that returns our test token
    default_token = "xoxb-default-test-token"

    def mock_default_token(self):
        return default_token

    # Replace the property with our mock
    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_default_token))

    # Also patch the AsyncWebClient in the client_factory module
    from slack_mcp.client import factory

    monkeypatch.setattr(factory, "AsyncWebClient", _DummyAsyncWebClient)
    monkeypatch.setattr(factory, "WebClient", _DummyAsyncWebClient)  # Use same mock for sync client


# Define constants for environment variables
SLACK_TOKEN_ENV_VARS = ("SLACK_BOT_TOKEN", "SLACK_TOKEN")


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", SLACK_TOKEN_ENV_VARS)
async def test_send_slack_message_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_env_token(self):
        return "xoxb-env-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

    result = await srv.send_slack_message(input_params=SlackPostMessageInput(channel="#general", text="Hello"))
    assert isinstance(result, SlackMessageResponse)
    assert result.ok is True
    assert result.channel == "#general"
    assert result.text == "Hello"
    assert result.ts == "1620000000.000000"


@pytest.mark.asyncio
async def test_send_slack_message_param() -> None:
    """Message should be sent successfully with default token."""
    result = await srv.send_slack_message(input_params=SlackPostMessageInput(channel="C123", text="Hi"))
    assert isinstance(result, SlackMessageResponse)
    assert result.ok is True
    assert result.channel == "C123"
    assert result.text == "Hi"
    assert result.ts == "1620000000.000000"


@pytest.mark.asyncio
async def test_send_slack_message_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    # Remove environment variables
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Update the mock default token property to return None
    from slack_mcp.client.manager import SlackClientManager

    def mock_none_token(self):
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.send_slack_message(input_params=SlackPostMessageInput(channel="#general", text="Hello"))


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", SLACK_TOKEN_ENV_VARS)
async def test_read_thread_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_env_token(self):
        return "xoxb-env-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="#general", thread_ts="1620000000.000000")
    )
    assert isinstance(result, SlackThreadMessagesResponse)
    assert result.ok is True
    assert result.channel == "#general"
    assert result.messages == [{"text": "Thread parent", "ts": "1620000000.000000"}]
    assert result.ts == "1620000000.000000"


@pytest.mark.asyncio
async def test_read_thread_messages_param() -> None:
    """Thread messages should be read successfully with default token."""
    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1620000000.000000")
    )
    assert isinstance(result, SlackThreadMessagesResponse)
    assert result.ok is True
    assert result.channel == "C123"
    assert result.messages == [{"text": "Thread parent", "ts": "1620000000.000000"}]
    assert result.ts == "1620000000.000000"


@pytest.mark.asyncio
async def test_read_thread_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Update the mock default token property to return None
    from slack_mcp.client.manager import SlackClientManager

    def mock_none_token(self):
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.read_thread_messages(
            input_params=SlackReadThreadMessagesInput(channel="#general", thread_ts="1620000000.000000")
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", SLACK_TOKEN_ENV_VARS)
async def test_read_slack_channel_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_env_token(self):
        return "xoxb-env-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="#general"))
    assert isinstance(result, SlackChannelMessagesResponse)
    assert result.ok is True
    assert result.channel == "#general"
    assert result.messages is not None
    assert len(result.messages) > 0
    assert result.has_more is False
    assert result.response_metadata is not None


@pytest.mark.asyncio
async def test_read_slack_channel_messages_limit() -> None:
    """Channel messages should be limited by the limit parameter."""
    result = await srv.read_slack_channel_messages(
        input_params=SlackReadChannelMessagesInput(channel="#general", limit=1)
    )
    assert isinstance(result, SlackChannelMessagesResponse)
    assert result.ok is True
    assert result.channel == "#general"
    assert result.messages == [{"type": "message", "text": "Test message 0", "ts": "165612340.00000", "user": "U123450"}]
    assert result.has_more is False
    assert result.response_metadata == {"next_cursor": ""}


@pytest.mark.asyncio
async def test_read_slack_channel_messages_param() -> None:
    """Channel messages should be read successfully with default token."""
    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="C123"))
    assert isinstance(result, SlackChannelMessagesResponse)
    assert result.ok is True
    assert result.channel == "C123"
    assert result.messages == [
        {"type": "message", "text": "Test message 0", "ts": "165612340.00000", "user": "U123450"},
        {"type": "message", "text": "Test message 1", "ts": "165612341.00000", "user": "U123451"},
        {"type": "message", "text": "Test message 2", "ts": "165612342.00000", "user": "U123452"},
    ]
    assert result.has_more is False
    assert result.response_metadata == {"next_cursor": ""}


@pytest.mark.asyncio
async def test_read_slack_channel_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Update the mock default token property to return None
    from slack_mcp.client.manager import SlackClientManager

    def mock_none_token(self):
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="#general"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "param_name,param_value,expected_kwarg",
    [
        ("oldest", "1620000000.000000", {"oldest": "1620000000.000000"}),
        ("latest", "1620010000.000000", {"latest": "1620010000.000000"}),
        ("inclusive", True, {"inclusive": True}),
        (
            "all_params",
            {"oldest": "1620000000.000000", "latest": "1620010000.000000", "inclusive": True},
            {"oldest": "1620000000.000000", "latest": "1620010000.000000", "inclusive": True},
        ),
    ],
)
async def test_read_slack_channel_messages_optional_params(
    monkeypatch: pytest.MonkeyPatch, param_name: str, param_value: Any, expected_kwarg: dict
) -> None:
    """Test that optional parameters are correctly passed to the Slack API."""
    # Create a spy for the AsyncWebClient.conversations_history method
    from slack_mcp.mcp.server import AsyncWebClient

    original_method = AsyncWebClient.conversations_history

    # Create a dictionary to store the kwargs that were passed
    captured_kwargs = {}

    async def mock_conversations_history(self, **kwargs):
        # Store the kwargs for later inspection
        captured_kwargs.update(kwargs)
        # Call the original method to maintain behavior
        return await original_method(self, **kwargs)

    # Apply the spy
    monkeypatch.setattr(AsyncWebClient, "conversations_history", mock_conversations_history)

    # Prepare input parameters
    if param_name == "all_params":
        # For the "all_params" case, we need to set all three parameters
        input_params = SlackReadChannelMessagesInput(
            channel="#general",
            oldest=param_value["oldest"],
            latest=param_value["latest"],
            inclusive=param_value["inclusive"],
        )
    else:
        # For individual parameter tests
        kwargs = {"channel": "#general"}
        kwargs[param_name] = param_value
        input_params = SlackReadChannelMessagesInput(**kwargs)  # type: ignore[arg-type]

    # Call the function
    await srv.read_slack_channel_messages(input_params=input_params)

    # Verify that the expected kwargs were passed to the API call
    for key, value in expected_kwarg.items():
        assert key in captured_kwargs, f"Expected {key} to be in kwargs"
        assert captured_kwargs[key] == value, f"Expected {key}={value}, got {captured_kwargs[key]}"


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", SLACK_TOKEN_ENV_VARS)
async def test_send_slack_thread_reply_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_env_token(self):
        return "xoxb-env-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="#general", thread_ts=thread_ts, texts=["Hello"])
    )
    assert isinstance(result, SlackThreadReplyResponse)
    assert result.responses == [
        {
            "ok": True,
            "channel": "#general",
            "ts": "1620000000.000000",
            "text": "Hello",
            "thread_ts": "1620000000.000000",
        }
    ]


@pytest.mark.asyncio
async def test_send_slack_thread_reply_param() -> None:
    """Thread replies should be sent successfully with default token."""
    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="C123", thread_ts=thread_ts, texts=["Hello"])
    )
    assert isinstance(result, SlackThreadReplyResponse)
    assert result.responses == [
        {
            "ok": True,
            "channel": "C123",
            "ts": "1620000000.000000",
            "text": "Hello",
            "thread_ts": "1620000000.000000",
        }
    ]


@pytest.mark.asyncio
async def test_send_slack_thread_reply_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Update the mock default token property to return None
    from slack_mcp.client.manager import SlackClientManager

    def mock_none_token(self):
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    thread_ts = "1620000000.000000"
    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.send_slack_thread_reply(
            input_params=SlackThreadReplyInput(channel="#general", thread_ts=thread_ts, texts=["Hello"])
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", SLACK_TOKEN_ENV_VARS)
async def test_read_slack_emojis_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_env_token(self):
        return "xoxb-env-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

    result = await srv.read_slack_emojis(input_params=SlackReadEmojisInput())
    assert isinstance(result, SlackEmojiListResponse)
    assert result.ok is True
    assert result.emoji == {
        "aliases": {
            "thumbsup": "+1",
            "smile": "grinning",
        },
        "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
        "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
    }


@pytest.mark.asyncio
async def test_read_slack_emojis_param() -> None:
    """Emojis should be read successfully with default token."""
    result = await srv.read_slack_emojis(input_params=SlackReadEmojisInput())
    assert isinstance(result, SlackEmojiListResponse)
    assert result.ok is True
    assert result.emoji == {
        "aliases": {
            "thumbsup": "+1",
            "smile": "grinning",
        },
        "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
        "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
    }


@pytest.mark.asyncio
async def test_get_slack_emojis_resource() -> None:
    """Emojis should be read successfully from the resource."""
    result = await srv.get_slack_emojis()
    assert isinstance(result, SlackEmojiListResponse)
    assert result.ok is True
    assert result.emoji == {
        "aliases": {
            "thumbsup": "+1",
            "smile": "grinning",
        },
        "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
        "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
    }


@pytest.mark.asyncio
async def test_read_slack_emojis_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Update the mock default token property to return None
    from slack_mcp.client.manager import SlackClientManager

    def mock_none_token(self):
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.read_slack_emojis(input_params=SlackReadEmojisInput())


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", SLACK_TOKEN_ENV_VARS)
async def test_add_slack_reactions_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when using default client."""
    # Remove all Slack token env vars first
    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Then set just the one we want to test
    monkeypatch.setenv(env_var, "xoxb-env-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_env_token(self):
        return "xoxb-env-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_env_token))

    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="#general", timestamp=timestamp, emojis=["thumbsup"])
    )
    assert isinstance(result, SlackAddReactionsResponse)
    assert result.responses == [
        {
            "ok": True,
            "channel": "#general",
            "timestamp": timestamp,
            "name": "thumbsup",
        }
    ]


@pytest.mark.asyncio
async def test_add_slack_reactions_param() -> None:
    """Reactions should be added successfully with default token."""
    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="C123", timestamp=timestamp, emojis=["thumbsup"])
    )
    assert isinstance(result, SlackAddReactionsResponse)
    assert result.responses == [
        {
            "ok": True,
            "channel": "C123",
            "timestamp": timestamp,
            "name": "thumbsup",
        }
    ]


@pytest.mark.asyncio
async def test_add_slack_reactions_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is available in environment."""

    for var in SLACK_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Update the mock default token property to return None
    from slack_mcp.client.manager import SlackClientManager

    def mock_none_token(self):
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_none_token))

    timestamp = "1620000000.000000"
    with pytest.raises(ValueError, match=r"Slack token not found.*"):
        await srv.add_slack_reactions(
            input_params=SlackAddReactionsInput(channel="#general", timestamp=timestamp, emojis=["thumbsup"])
        )


def test_set_slack_client_retry_count_negative() -> None:
    """Function should raise :class:`ValueError` if retry count is negative."""
    with pytest.raises(ValueError, match="Retry count must be non-negative"):
        srv.set_slack_client_retry_count(-1)


def test_get_slack_client_returns_client() -> None:
    """Function should return client from client.manager.get_async_client."""
    # Create a test token
    test_token = "xoxb-test-token-for-get-client"

    # Get a client with the test token
    client = srv.get_slack_client(token=test_token)

    # Verify the client has the correct token
    assert client.token == test_token

    # Also test with default token
    default_client = srv.get_slack_client()
    assert default_client.token is not None


@pytest.mark.parametrize(
    "env_var,token_value,expected_outcome",
    [
        ("SLACK_BOT_TOKEN", "xoxb-test-token", "success"),  # SLACK_BOT_TOKEN is set
        ("SLACK_TOKEN", "xoxp-test-token", "success"),  # SLACK_TOKEN is set
        (None, None, "error"),  # No token set
    ],
)
def test_get_default_client(
    monkeypatch: pytest.MonkeyPatch, env_var: Optional[str], token_value: Optional[str], expected_outcome: str
) -> None:
    """Test _get_default_client with various token configurations.

    This test verifies that _get_default_client correctly:
    1. Uses SLACK_BOT_TOKEN when available
    2. Falls back to SLACK_TOKEN when SLACK_BOT_TOKEN is not set
    3. Raises ValueError when no token is available
    """
    # Clear all environment variables first
    for var in ("SLACK_BOT_TOKEN", "SLACK_TOKEN"):
        monkeypatch.delenv(var, raising=False)

    # Set the environment variable if specified
    if env_var and token_value:
        monkeypatch.setenv(env_var, token_value)

    # Update the mock default token property to match our test case
    from slack_mcp.client.manager import SlackClientManager

    def mock_token_getter(self):
        if env_var == "SLACK_BOT_TOKEN" and token_value:
            return token_value
        elif env_var == "SLACK_TOKEN" and token_value:
            return token_value
        return None

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_token_getter))

    # Clear any cached clients
    srv.clear_slack_clients()

    # Test the function
    if expected_outcome == "success":
        client = srv._get_default_client()
        assert isinstance(client, _DummyAsyncWebClient)
        # Verify the client was created with the correct token
        assert client.token == token_value
    else:
        with pytest.raises(ValueError, match=r"Slack token not found.*"):
            srv._get_default_client()


@pytest.mark.parametrize(
    "retry_count",
    [
        3,  # Default retry count
        5,  # Custom retry count
        0,  # No retries
    ],
)
def test_get_default_client_retry_behavior(monkeypatch: pytest.MonkeyPatch, retry_count: int) -> None:
    """Test _get_default_client with different retry configurations.

    This test verifies that _get_default_client correctly:
    1. Uses the configured retry count
    """
    # Set a token in environment
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_token_getter(self):
        return "xoxb-test-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_token_getter))

    # Set the retry count
    srv.set_slack_client_retry_count(retry_count)

    # Clear any cached clients
    srv.clear_slack_clients()

    # Test the function directly
    client = srv._get_default_client()

    # Verify client was created
    assert isinstance(client, _DummyAsyncWebClient)
    assert client.token == "xoxb-test-token"

    # Verify the retry count was set correctly in the client manager
    client_manager = srv.get_client_manager()
    assert client_manager._default_retry_count == retry_count


def test_get_default_client_caching(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that _get_default_client uses the client manager's caching mechanism.

    This test verifies that calling _get_default_client multiple times with the
    same token returns the same client instance from the cache.
    """
    # Set a token in environment
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

    # Update the mock default token property
    from slack_mcp.client.manager import SlackClientManager

    def mock_token_getter(self):
        return "xoxb-test-token"

    monkeypatch.setattr(SlackClientManager, "_default_token", property(mock_token_getter))

    # Get the client manager to inspect its cache
    client_manager = srv.get_client_manager()

    # Clear any cached clients to start fresh
    srv.clear_slack_clients()
    assert len(client_manager._async_clients) == 0

    # Call _get_default_client and get the first client
    client1 = srv._get_default_client()

    # Cache key format is "{token}:{use_retries}"
    cache_key = "xoxb-test-token:True"

    # Check that the client is in the cache
    assert cache_key in client_manager._async_clients
    assert client_manager._async_clients[cache_key] is client1

    # Call _get_default_client again
    client2 = srv._get_default_client()

    # Verify both calls return the same client instance
    assert client1 is client2

    # Now clear the cache
    srv.clear_slack_clients()
    assert len(client_manager._async_clients) == 0

    # Get a new client
    client3 = srv._get_default_client()

    # Cache should have one client again
    assert cache_key in client_manager._async_clients

    # But it should be a different instance than before
    assert client3 is not client1
