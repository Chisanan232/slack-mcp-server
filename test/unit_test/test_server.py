"""Unit tests for :pymod:`slack_mcp.server`."""

from __future__ import annotations

from typing import Any, Final

import pytest

import slack_mcp.server as srv
from slack_mcp.model import SlackPostMessageInput, SlackReadChannelMessagesInput, SlackReadThreadMessagesInput

# Ensure pytest-asyncio plugin is available for async tests
pytest_plugins = ["pytest_asyncio"]

pytestmark = pytest.mark.asyncio


class _FakeSlackResponse:  # noqa: D101 – minimal stub
    """Stand-in for :class:`slack_sdk.web.slack_response.SlackResponse`."""

    def __init__(self, data: dict[str, Any]):  # noqa: D401 – docstring short.
        self.data: Final[dict[str, Any]] = data


class _DummyAsyncWebClient:  # noqa: D101 – simple stub
    """Minimal stub replacing :class:`slack_sdk.web.async_client.AsyncWebClient`."""

    def __init__(self, *args: Any, **kwargs: Any):  # noqa: D401 – docstring short.
        # Accept and ignore all initialisation parameters.
        pass

    async def chat_postMessage(self, *, channel: str, text: str, **_: Any):
        """Echo back inputs in a Slack-like response structure."""
        return _FakeSlackResponse({"ok": True, "channel": channel, "text": text})

    async def conversations_replies(self, *, channel: str, ts: str, limit: int = 100, **_: Any):
        """Echo back inputs in a Slack-like thread response structure."""
        messages = [
            {"ts": ts, "thread_ts": ts, "text": "Parent message"},
            {"ts": f"{ts}.1", "thread_ts": ts, "text": "Reply 1"},
            {"ts": f"{ts}.2", "thread_ts": ts, "text": "Reply 2"}
        ]
        # Limit the number of messages based on the limit parameter
        return _FakeSlackResponse({
            "ok": True,
            "channel": channel,
            "messages": messages[:min(limit, len(messages))],
            "has_more": False,
            "response_metadata": {"next_cursor": ""}
        })

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


@pytest.fixture(autouse=True)
def _patch_slack_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch :pyclass:`AsyncWebClient` with the dummy implementation for tests."""

    monkeypatch.setattr(srv, "AsyncWebClient", _DummyAsyncWebClient)


aSYNC_TOKEN_ENV_VARS = ("SLACK_BOT_TOKEN", "SLACK_TOKEN")


@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_send_slack_message_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None*."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.send_slack_message(input_params=SlackPostMessageInput(channel="#general", text="Hello"))
    assert result == {"ok": True, "channel": "#general", "text": "Hello"}


async def test_send_slack_message_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.send_slack_message(
        input_params=SlackPostMessageInput(channel="C123", text="Hi", token="xoxb-param")
    )
    assert result == {"ok": True, "channel": "C123", "text": "Hi"}


async def test_send_slack_message_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.send_slack_message(input_params=SlackPostMessageInput(channel="C123", text="Hi"))


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


async def test_read_thread_messages_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables for thread reading."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(
            channel="C123",
            thread_ts="1234567890.123456",
            token="xoxb-param"
        )
    )
    assert result["ok"] is True
    assert result["channel"] == "C123"
    assert len(result["messages"]) == 3


async def test_read_thread_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all for thread reading."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.read_thread_messages(
            input_params=SlackReadThreadMessagesInput(channel="C123", thread_ts="1234567890.123456")
        )


async def test_read_thread_messages_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should honor the limit parameter for thread reading."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-env-token")

    # Test with limit=1
    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(
            channel="C123",
            thread_ts="1234567890.123456",
            limit=1
        )
    )
    assert result["ok"] is True
    assert len(result["messages"]) == 1
    assert result["messages"][0]["text"] == "Parent message"

    # Test with limit=2
    result = await srv.read_thread_messages(
        input_params=SlackReadThreadMessagesInput(
            channel="C123",
            thread_ts="1234567890.123456",
            limit=2
        )
    )
    assert result["ok"] is True
    assert len(result["messages"]) == 2
    assert result["messages"][1]["text"] == "Reply 1"


@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_read_slack_channel_messages_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None*."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="#general"))
    assert result["ok"] is True
    assert result["channel"] == "#general"
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 3


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


async def test_read_slack_channel_messages_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Channel history limit parameter should be passed correctly."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")

    # With the test implementation, we should get max 2 messages when limit is 2
    result = await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="C123", limit=2))
    assert result["ok"] is True
    assert len(result["messages"]) == 2


async def test_read_slack_channel_messages_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.read_slack_channel_messages(input_params=SlackReadChannelMessagesInput(channel="C123"))
