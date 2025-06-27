"""Unit tests for slack_models module.

This module tests the Pydantic models and deserialization functionality
for Slack events API payloads.
"""

import json
import pytest

from slack_mcp.slack_models import (
    SlackEventModel,
    EventCallbackModel,
    SlackEventItem,
    UrlVerificationModel,
    deserialize,
)


def test_url_verification_model():
    """Test UrlVerificationModel deserialization."""
    data = {
        "type": "url_verification",
        "challenge": "test_challenge_token",
        "token": "test_token"
    }
    
    # Test deserialization function
    model = deserialize(data)
    assert isinstance(model, UrlVerificationModel)
    assert model.challenge == "test_challenge_token"
    assert model.token == "test_token"
    assert model.type == "url_verification"
    
    # Test direct model instantiation
    model = UrlVerificationModel(**data)
    assert model.challenge == "test_challenge_token"
    assert model.token == "test_token"


def test_slack_event_model():
    """Test SlackEventModel deserialization."""
    data = {
        "token": "test_token",
        "team_id": "T12345",
        "api_app_id": "A12345",
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "Hello <@U12345>",
            "ts": "1234567890.123456",
            "channel": "C12345",
            "event_ts": "1234567890.123456"
        },
        "type": "event_callback",
        "event_id": "Ev12345",
        "event_time": 1234567890,
        "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
        "is_ext_shared_channel": False
    }
    
    # Test deserialization function
    model = deserialize(data)
    assert isinstance(model, SlackEventModel)
    assert model.token == "test_token"
    assert model.team_id == "T12345"
    assert model.event.type == "app_mention"
    assert model.event.user == "U12345"
    assert model.event.text == "Hello <@U12345>"
    
    # Test direct model instantiation
    model = SlackEventModel(**data)
    assert model.token == "test_token"
    assert model.team_id == "T12345"
    assert model.event.type == "app_mention"
    assert model.event.user == "U12345"


def test_event_callback_model():
    """Test EventCallbackModel with various event types."""
    # Test app_mention event
    data = {
        "type": "app_mention",
        "user": "U12345",
        "text": "Hello <@U12345>",
        "ts": "1234567890.123456",
        "channel": "C12345",
        "event_ts": "1234567890.123456"
    }
    
    model = EventCallbackModel(**data)
    assert model.type == "app_mention"
    assert model.user == "U12345"
    assert model.text == "Hello <@U12345>"
    
    # Test reaction_added event
    data = {
        "type": "reaction_added",
        "user": "U12345",
        "reaction": "thumbsup",
        "item": {
            "type": "message",
            "channel": "C12345",
            "ts": "1234567890.123456"
        },
        "event_ts": "1234567890.123457"
    }
    
    model = EventCallbackModel(**data)
    assert model.type == "reaction_added"
    assert model.user == "U12345"
    assert model.reaction == "thumbsup"
    assert model.item["type"] == "message"


def test_extra_fields():
    """Test that extra fields are allowed and preserved."""
    data = {
        "token": "test_token",
        "team_id": "T12345",
        "api_app_id": "A12345",
        "event": {
            "type": "app_mention",
            "user": "U12345",
            "text": "Hello <@U12345>",
            "ts": "1234567890.123456",
            "channel": "C12345",
            "event_ts": "1234567890.123456",
            "extra_field": "extra_value"
        },
        "type": "event_callback",
        "event_id": "Ev12345",
        "event_time": 1234567890,
        "authorizations": [{"enterprise_id": None, "team_id": "T12345", "user_id": "U12345"}],
        "is_ext_shared_channel": False,
        "another_extra_field": "another_extra_value"
    }
    
    model = deserialize(data)
    assert isinstance(model, SlackEventModel)
    assert model.model_dump().get("another_extra_field") == "another_extra_value"
    assert model.event.model_dump().get("extra_field") == "extra_value"


def test_optional_fields():
    """Test that optional fields can be omitted."""
    minimal_data = {
        "token": "test_token",
        "team_id": "T12345",
        "api_app_id": "A12345",
        "event": {
            "type": "app_mention",
        },
        "type": "event_callback",
        "event_id": "Ev12345",
        "event_time": 1234567890,
        "authorizations": []
    }
    
    model = deserialize(minimal_data)
    assert isinstance(model, SlackEventModel)
    assert model.token == "test_token"
    assert model.event.type == "app_mention"
    assert model.event.user is None
    assert model.event.text is None
    assert model.is_ext_shared_channel is False
