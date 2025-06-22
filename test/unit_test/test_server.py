"""Unit tests for :pymod:`slack_mcp.server`."""

from __future__ import annotations

from typing import Any, Final

import pytest

import slack_mcp.server as srv
from slack_mcp.model import SlackPostMessageInput, SlackThreadReplyInput

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

    async def chat_postMessage(self, *, channel: str, text: str, thread_ts: str = None, **_: Any):
        """Echo back inputs in a Slack-like response structure."""
        response = {"ok": True, "channel": channel, "text": text}
        if thread_ts:
            response["thread_ts"] = thread_ts
            response["ts"] = f"{float(thread_ts) + 0.001:.6f}"  # Simulate a reply timestamp
        else:
            response["ts"] = "1620000000.000000"  # Dummy timestamp for non-thread messages
        return _FakeSlackResponse(response)


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
    assert result == {"ok": True, "channel": "#general", "text": "Hello", "ts": "1620000000.000000"}


async def test_send_slack_message_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.send_slack_message(
        input_params=SlackPostMessageInput(channel="C123", text="Hi", token="xoxb-param")
    )
    assert result == {"ok": True, "channel": "C123", "text": "Hi", "ts": "1620000000.000000"}


async def test_send_slack_message_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.send_slack_message(input_params=SlackPostMessageInput(channel="C123", text="Hi"))


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


async def test_send_slack_thread_reply_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all for thread replies."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    thread_ts = "1620000000.000000"
    with pytest.raises(ValueError):
        await srv.send_slack_thread_reply(
            input_params=SlackThreadReplyInput(channel="C123", thread_ts=thread_ts, texts=["Reply text"])
        )


async def test_send_slack_thread_reply_empty_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should return a dict with an empty list if texts list is empty."""

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-env-token")

    thread_ts = "1620000000.000000"
    result = await srv.send_slack_thread_reply(
        input_params=SlackThreadReplyInput(channel="C123", thread_ts=thread_ts, texts=[])
    )

    assert isinstance(result, dict)
    assert "responses" in result
    assert isinstance(result["responses"], list)
    assert len(result["responses"]) == 0
