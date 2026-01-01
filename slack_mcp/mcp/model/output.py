"""Data models for Slack MCP server output."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class SlackResponse(BaseModel):
    """Base class for Slack API responses."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    error: Optional[str] = None
    needed: Optional[str] = None
    provided: Optional[str] = None


class SlackMessageResponse(SlackResponse):
    """Output for :pydata:`send_slack_message`."""

    channel: Optional[str] = None
    ts: Optional[str] = None
    text: Optional[str] = None
    message: Optional[Dict[str, Any]] = None


class SlackThreadMessagesResponse(SlackResponse):
    """Output for :pydata:`read_thread_messages`."""

    channel: Optional[str] = None
    ts: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    has_more: Optional[bool] = None
    response_metadata: Optional[Dict[str, Any]] = None


class SlackChannelMessagesResponse(SlackResponse):
    """Output for :pydata:`read_slack_channel_messages`."""

    channel: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    has_more: Optional[bool] = None
    response_metadata: Optional[Dict[str, Any]] = None


class SlackThreadReplyResponse(BaseModel):
    """Output for :pydata:`send_slack_thread_reply`."""

    model_config = ConfigDict(extra="ignore")

    responses: List[Dict[str, Any]]


class SlackEmojiListResponse(SlackResponse):
    """Output for :pydata:`read_slack_emojis`."""

    emoji: Optional[Dict[str, Any]] = None


class SlackAddReactionsResponse(BaseModel):
    """Output for :pydata:`add_slack_reactions`."""

    model_config = ConfigDict(extra="ignore")

    responses: List[Dict[str, Any]]
