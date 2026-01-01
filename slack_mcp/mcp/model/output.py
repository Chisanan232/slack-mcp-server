"""Data models for Slack MCP server output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(kw_only=True)
class SlackResponse:
    """Base class for Slack API responses."""

    ok: bool
    error: Optional[str] = None
    needed: Optional[str] = None
    provided: Optional[str] = None


@dataclass(kw_only=True)
class SlackMessageResponse(SlackResponse):
    """Output for :pydata:`send_slack_message`."""

    channel: Optional[str] = None
    ts: Optional[str] = None
    text: Optional[str] = None
    message: Optional[Dict[str, Any]] = None


@dataclass(kw_only=True)
class SlackThreadMessagesResponse(SlackResponse):
    """Output for :pydata:`read_thread_messages`."""

    channel: Optional[str] = None
    ts: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    has_more: Optional[bool] = None


@dataclass(kw_only=True)
class SlackChannelMessagesResponse(SlackResponse):
    """Output for :pydata:`read_slack_channel_messages`."""

    channel: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    has_more: Optional[bool] = None
    response_metadata: Optional[Dict[str, Any]] = None


@dataclass(kw_only=True)
class SlackThreadReplyResponse:
    """Output for :pydata:`send_slack_thread_reply`."""

    responses: List[Dict[str, Any]]


@dataclass(kw_only=True)
class SlackEmojiListResponse(SlackResponse):
    """Output for :pydata:`read_slack_emojis`."""

    emoji: Optional[Dict[str, str]] = None


@dataclass(kw_only=True)
class SlackAddReactionsResponse:
    """Output for :pydata:`add_slack_reactions`."""

    responses: List[Dict[str, Any]]
