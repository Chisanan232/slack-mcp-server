"""Pydantic models for Slack events API payloads.

This module defines Pydantic models for Slack events API payloads,
following PEP 484/585 typing conventions.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SlackEventItem(BaseModel):
    """Model for Slack event item data structure."""

    type: Optional[str] = None
    channel: Optional[str] = None
    ts: Optional[str] = None


class EventCallbackModel(BaseModel):
    """Pydantic model for Slack event callback data structure."""

    type: str
    user: Optional[str] = None
    text: Optional[str] = None
    ts: Optional[str] = None
    channel: Optional[str] = None
    item: Optional[Dict[str, Any]] = None
    reaction: Optional[str] = None
    event_ts: Optional[str] = None
    thread_ts: Optional[str] = None

    # Use model_config instead of inner Config class for Pydantic v2 compatibility
    model_config = {
        "extra": "allow",
    }


class SlackEventModel(BaseModel):
    """Pydantic model for Slack event data structure."""

    token: str
    team_id: str
    api_app_id: str
    event: EventCallbackModel
    type: str
    event_id: str
    event_time: int
    authorizations: List[Dict[str, Any]]
    is_ext_shared_channel: Optional[bool] = False

    # Use model_config instead of inner Config class for Pydantic v2 compatibility
    model_config = {
        "extra": "allow",
    }


class UrlVerificationModel(BaseModel):
    """Pydantic model for Slack URL verification challenge."""

    type: str = Field(..., pattern="url_verification")
    challenge: str
    token: str


def deserialize(event_data: Dict[str, Any]) -> SlackEventModel | UrlVerificationModel:
    """Deserialize Slack event data into the appropriate Pydantic model.

    Parameters
    ----------
    event_data : Dict[str, Any]
        The event data from Slack as a dictionary

    Returns
    -------
    SlackEventModel | UrlVerificationModel
        The deserialized Slack event model

    Examples
    --------
    >>> event_data = {"type": "event_callback", "event": {"type": "app_mention"}, ...}
    >>> slack_event = deserialize(event_data)
    >>> isinstance(slack_event, SlackEventModel)
    True
    """
    event_type = event_data.get("type")

    if event_type == "url_verification":
        return UrlVerificationModel(**event_data)
    else:
        return SlackEventModel(**event_data)
