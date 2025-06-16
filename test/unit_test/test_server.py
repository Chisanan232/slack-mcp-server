"""Unit tests for :pymod:`slack_mcp.server`."""
from __future__ import annotations

import os
from typing import Any, Final

import pytest

import slack_mcp.server as srv

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


@pytest.fixture(autouse=True)
def _patch_slack_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch :pyclass:`AsyncWebClient` with the dummy implementation for tests."""

    monkeypatch.setattr(srv, "AsyncWebClient", _DummyAsyncWebClient)


aSYNC_TOKEN_ENV_VARS = ("SLACK_BOT_TOKEN", "SLACK_TOKEN")


@pytest.mark.parametrize("env_var", aSYNC_TOKEN_ENV_VARS)
async def test_send_slack_message_env(monkeypatch: pytest.MonkeyPatch, env_var: str) -> None:
    """Token should be picked from environment when *token* argument is *None*."""

    monkeypatch.setenv(env_var, "xoxb-env-token")

    result = await srv.send_slack_message(channel="#general", text="Hello")
    assert result == {"ok": True, "channel": "#general", "text": "Hello"}


async def test_send_slack_message_param(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit *token* parameter takes precedence over environment variables."""

    # Ensure env vars are absent.
    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    result = await srv.send_slack_message(channel="C123", text="Hi", token="xoxb-param")
    assert result == {"ok": True, "channel": "C123", "text": "Hi"}


async def test_send_slack_message_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Function should raise :class:`ValueError` if no token is provided at all."""

    for var in aSYNC_TOKEN_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError):
        await srv.send_slack_message(channel="C123", text="Hi")
