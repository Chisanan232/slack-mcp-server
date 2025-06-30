"""Unit tests for :pymod:`slack_mcp.server`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Optional

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
        pass

    async def chat_postMessage(self, *, channel: str, text: str, thread_ts: Optional[str] = None, **_: Any):
        """Echo back inputs in a Slack-like response structure."""
        response = {"ok": True, "channel": channel, "text": text}
        if thread_ts:
            response["thread_ts"] = thread_ts
            response["ts"] = f"{float(thread_ts) + 0.001:.6f}"  # Simulate a reply timestamp
        else:
            response["ts"] = "1620000000.000000"  # Dummy timestamp for non-thread messages
        return _FakeSlackResponse(response)

    async def conversations_replies(self, *, channel: str, ts: str, limit: int = 100, **_: Any):
        """Echo back inputs in a Slack-like thread response structure."""
        messages = [
            {"ts": ts, "thread_ts": ts, "text": "Parent message"},
            {"ts": f"{ts}.1", "thread_ts": ts, "text": "Reply 1"},
            {"ts": f"{ts}.2", "thread_ts": ts, "text": "Reply 2"},
        ]
        # Limit the number of messages based on the limit parameter
        return _FakeSlackResponse(
            {
                "ok": True,
                "channel": channel,
                "messages": messages[: min(limit, len(messages))],
                "has_more": False,
                "response_metadata": {"next_cursor": ""},
            }
        )

    async def conversations_history(
        self,
        *,
        channel: str,
        limit: int = 100,
        oldest: str | None = None,
        latest: str | None = None,
        inclusive: bool = False,
        **_: Any,
    ):
        """Echo back inputs in a Slack-like response structure for channel history."""
        messages = [
            {"type": "message", "text": f"Test message {i}", "ts": f"16561234{i}.00000", "user": f"U12345{i}"}
            for i in range(min(3, limit))
        ]
        return _FakeSlackResponse(
            {
                "ok": True,
                "channel": channel,
                "messages": messages,
                "has_more": False,
                "response_metadata": {"next_cursor": ""},
            }
        )

    async def emoji_list(self, **_: Any):
        """Return a mock emoji list with built-in and custom emojis."""
        emojis = {
            # Built-in emojis (aliases to other emojis)
            "thumbsup": "alias:+1",
            "smile": "alias:grinning",
            # Custom emojis (URLs to images)
            "custom_emoji1": "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png",
            "custom_emoji2": "https://emoji.slack-edge.com/T12345/custom_emoji2/def456.png",
        }
        return _FakeSlackResponse({"ok": True, "emoji": emojis})

    async def reactions_add(self, *, channel: str, timestamp: str, name: str, **_: Any):
        """Echo back inputs in a Slack-like response structure for reactions.add API."""
        response = {
            "ok": True,
            "channel": channel,
            "timestamp": timestamp,
            "name": name,
        }
        return _FakeSlackResponse(response)


@pytest.fixture(autouse=True)
def _patch_slack_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch :pyclass:`AsyncWebClient` with the dummy implementation for tests."""

    monkeypatch.setattr(srv, "AsyncWebClient", _DummyAsyncWebClient)
    # Also patch the AsyncWebClient in the client_factory module
    from slack_mcp import client_factory
    monkeypatch.setattr(client_factory, "AsyncWebClient", _DummyAsyncWebClient)
    monkeypatch.setattr(client_factory, "WebClient", _DummyAsyncWebClient)  # Use same mock for sync client


aSYNC_TOKEN_ENV_VARS = ("SLACK_BOT_TOKEN", "SLACK_TOKEN")


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_send_slack_message_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None*."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.send_slack_message(input_params=SlackPostMessageInput(channel="#general", text="Hello"))
    assert result == {"ok": True, "channel": "#general", "text": "Hello", "ts": "1620000000.000000"}


@pytest.mark.asyncio
async def test_send_slack_message_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.send_slack_message(
        input_params=SlackPostMessageInput(channel="C123", text="Hi", token="xoxb-param")
    )
    assert result == {"ok": True, "channel": "C123", "text": "Hi", "ts": "1620000000.000000"}


@pytest.mark.asyncio
async def test_send_slack_message_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.send_slack_message(input_params=SlackPostMessageInput(channel="C123", text="Hi"))


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_thread_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None* for thread reading."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="#general", thread_ts="1234567890.123456")
    )
    assert result["ok"] is True
    assert result["channel"] == "#general"
    assert len(result["messages"]) == 3
    assert result["messages"][0]["ts"] == "1234567890.123456"
    assert result["messages"][1]["text"] == "Reply 1"


@pytest.mark.asyncio
async def test_read_thread_messages_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables for thread reading."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1234567890.123456", token="xoxb-param")
    )
    assert result["ok"] is True
    assert result["channel"] == "C123"
    assert len(result["messages"]) == 3


@pytest.mark.asyncio
async def test_read_thread_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all for thread reading."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.read_thread_messages(
            input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1234567890.123456")
        )


@pytest.mark.asyncio
async def test_read_thread_messages_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should honor the limit parameter for thread reading."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-env-token")

    # Test with limit=1
    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1234567890.123456", limit=1)
    )
    assert result["ok"] is True
    assert len(result["messages"]) == 1
    assert result["messages"][0]["text"] == "Parent message"

    # Test with limit=2
    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1234567890.123456", limit=2)
    )
    assert result["ok"] is True
    assert len(result["messages"]) == 2
    assert result["messages"][1]["text"] == "Reply 1"


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_slack_channel_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None*."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="#general"))
    assert result["ok"] is True
    assert result["channel"] == "#general"
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 3


@pytest.mark.asyncio
async def test_read_slack_channel_messages_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.read_slack_channel_messages(
        input_params=SlackReadChannelMessagesInput(channel="C123", token="xoxb-param")
    )
    assert result["ok"] is True
    assert result["channel"] == "C123"
    assert isinstance(result["messages"], list)


@pytest.mark.asyncio
async def test_read_slack_channel_messages_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Channel history limit parameter should be passed correctly."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

    # With the test implementation, we should get max 2 messages when limit is 2
    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="C123", limit=2))
    assert result["ok"] is True
    assert len(result["messages"]) == 2


@pytest.mark.asyncio
async def test_read_slack_channel_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all."""

    # Clear environment variables first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.read_slack_channel_messages(SlackReadChannelMessagesInput(channel="C123"))


@dataclass(slots=True, kw_only=True)
class TestBaseInput(_BaseInput):
    """Test implementation of _BaseInput for testing purposes."""


@pytest.mark.parametrize(
    "token_param, env_vars, expected_result, should_raise",
    [
        # Case 1: explicit token parameter is provided
        ("xoxb-explicit", {}, "xoxb-explicit", False),
        # Case 2: SLACK_BOT_TOKEN env var is set, no token parameter
        (None, {"SLACK_BOT_TOKEN": "xoxb-bot-token"}, "xoxb-bot-token", False),
        # Case 3: SLACK_TOKEN env var is set, no token parameter or SLACK_BOT_TOKEN
        (None, {"SLACK_TOKEN": "xoxb-slack-token"}, "xoxb-slack-token", False),
        # Case 4: Both env vars are set, SLACK_BOT_TOKEN should take precedence
        (None, {"SLACK_BOT_TOKEN": "xoxb-bot-token", "SLACK_TOKEN": "xoxb-slack-token"}, "xoxb-bot-token", False),
        # Case 5: Token param overrides env vars
        (
            "xoxb-explicit",
            {"SLACK_BOT_TOKEN": "xoxb-bot-token", "SLACK_TOKEN": "xoxb-slack-token"},
            "xoxb-explicit",
            False,
        ),
        # Case 6: Empty string token should raise (treated as None)
        ("", {}, None, True),
        # Case 7: No token anywhere should raise
        (None, {}, None, True),
    ],
)
def test_verify_slack_token_exist(
    monkeypatch: pytest.MonkeyPatch,
    token_param: str | None,
    env_vars: dict[str, str],
    expected_result: str | None,
    should_raise: bool,
) -> None:
    """Test token resolution with different token sources."""
    # Clear environment variables first
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    # Set env vars according to the test case
    for var_name, var_value in env_vars.items():
        monkeypatch.setenv(var_name, var_value)

    # Import the factory here to ensure it picks up the monkeypatched environment
    from slack_mcp.client_factory import DefaultSlackClientFactory
    factory = DefaultSlackClientFactory()

    if should_raise:
        with pytest.raises(ValueError) as excinfo:
            factory._resolve_token(token_param)
        assert "Slack token not found" in str(excinfo.value)
    else:
        result = factory._resolve_token(token_param)
        assert result == expected_result


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_send_slack_thread_reply_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None* for thread replies."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="#general", thread_ts=thread_ts, texts=["Reply 1", "Reply 2"])
    )

    assert isinstance(result, dict)
    assert "responses" in result

    responses = result["responses"]
    assert isinstance(responses, list)
    assert len(responses) == 2

    # Check first reply
    assert responses[0]["ok"] is True
    assert responses[0]["channel"] == "#general"
    assert responses[0]["text"] == "Reply 1"
    assert responses[0]["thread_ts"] == thread_ts
    assert "ts" in responses[0]

    # Check second reply
    assert responses[1]["ok"] is True
    assert responses[1]["channel"] == "#general"
    assert responses[1]["text"] == "Reply 2"
    assert responses[1]["thread_ts"] == thread_ts
    assert "ts" in responses[1]


@pytest.mark.asyncio
async def test_send_slack_thread_reply_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables for thread replies."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(
            channel="C123", thread_ts=thread_ts, texts=["Reply text"], token="xoxb-param"
        )
    )

    assert isinstance(result, dict)
    assert "responses" in result

    responses = result["responses"]
    assert isinstance(responses, list)
    assert len(responses) == 1
    assert responses[0]["ok"] is True
    assert responses[0]["channel"] == "C123"
    assert responses[0]["text"] == "Reply text"
    assert responses[0]["thread_ts"] == thread_ts
    assert "ts" in responses[0]


@pytest.mark.asyncio
async def test_send_slack_thread_reply_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all for thread replies."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    thread_ts = "1620000000.000000"
    with pytest.raises(ValueError):
        await srv.send_slack_thread_reply(
            input_params=SlackThreadReplyInput(channel="C123", thread_ts=thread_ts, texts=["Reply text"])
        )


@pytest.mark.asyncio
async def test_send_slack_thread_reply_empty_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should return a dict with an empty list if texts list is empty."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="#general", thread_ts=thread_ts, texts=[])
    )

    assert isinstance(result, dict)
    assert "responses" in result
    assert isinstance(result["responses"], list)
    assert len(result["responses"]) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_slack_emojis_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None* for emoji reading."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.read_slack_emojis(input_params=SlackReadEmojisInput())
    assert result["ok"] is True
    assert "emoji" in result
    assert isinstance(result["emoji"], dict)
    assert result["emoji"]["thumbsup"] == "alias:+1"
    assert result["emoji"]["custom_emoji1"] == "https://emoji.slack-edge.com/T12345/custom_emoji1/abc123.png"


@pytest.mark.asyncio
async def test_read_slack_emojis_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables for emoji reading."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.read_slack_emojis(input_params=SlackReadEmojisInput(token="xoxb-param"))
    assert result["ok"] is True
    assert "emoji" in result
    assert isinstance(result["emoji"], dict)


@pytest.mark.asyncio
async def test_read_slack_emojis_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all for emoji reading."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.read_slack_emojis(input_params=SlackReadEmojisInput())


@pytest.mark.asyncio
@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_add_slack_reactions_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None* for adding reactions."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="#general", timestamp=timestamp, emojis=["thumbsup", "heart"])
    )

    assert isinstance(result, dict)
    assert "responses" in result

    responses = result["responses"]
    assert isinstance(responses, list)
    assert len(responses) == 2

    # Check first reaction
    assert responses[0]["ok"] is True
    assert responses[0]["channel"] == "#general"
    assert responses[0]["timestamp"] == timestamp
    assert responses[0]["name"] == "thumbsup"

    # Check second reaction
    assert responses[1]["ok"] is True
    assert responses[1]["channel"] == "#general"
    assert responses[1]["timestamp"] == timestamp
    assert responses[1]["name"] == "heart"


@pytest.mark.asyncio
async def test_add_slack_reactions_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables for adding reactions."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="C123", timestamp=timestamp, emojis=["smile"], token="xoxb-param")
    )

    assert isinstance(result, dict)
    assert "responses" in result

    responses = result["responses"]
    assert isinstance(responses, list)
    assert len(responses) == 1
    assert responses[0]["ok"] is True
    assert responses[0]["channel"] == "C123"
    assert responses[0]["timestamp"] == timestamp
    assert responses[0]["name"] == "smile"


@pytest.mark.asyncio
async def test_add_slack_reactions_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all for adding reactions."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    timestamp = "1620000000.000000"
    with pytest.raises(ValueError):
        await srv.add_slack_reactions(
            input_params=SlackAddReactionsInput(channel="C123", timestamp=timestamp, emojis=["smile"])
        )


@pytest.mark.asyncio
async def test_add_slack_reactions_empty_emojis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should return a dict with an empty list if emojis list is empty."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

    timestamp = "1620000000.000000"
    result = await srv.add_slack_reactions(
        input_params=SlackAddReactionsInput(channel="#general", timestamp=timestamp, emojis=[])
    )

    assert isinstance(result, dict)
    assert "responses" in result
    assert isinstance(result["responses"], list)
    assert len(result["responses"]) == 0
