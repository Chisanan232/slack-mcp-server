"""
PyTest-based tests for the SlackEvent enum.

This module tests the SlackEvent enum functionality including:
- Value correctness for all event types
- String comparison and conversion
- from_type_subtype method behavior and edge cases
- Error handling for invalid events
"""

from __future__ import annotations

import inspect
from typing import Dict, Optional

import pytest

from slack_mcp.events import SlackEvent


def test_slack_event_values() -> None:
    """Test that SlackEvent enum values match their string representations."""
    assert SlackEvent.MESSAGE == "message"
    assert SlackEvent.REACTION_ADDED == "reaction_added"
    assert SlackEvent.APP_MENTION == "app_mention"
    assert SlackEvent.MESSAGE_CHANNELS == "message.channels"


def test_slack_event_from_type_subtype() -> None:
    """Test the from_type_subtype class method for creating SlackEvents."""
    # Test with type only
    event = SlackEvent.from_type_subtype("message")
    assert event == SlackEvent.MESSAGE

    # Test with type and subtype
    event = SlackEvent.from_type_subtype("message", "channels")
    assert event == SlackEvent.MESSAGE_CHANNELS

    # Test fallback to type-only when combined doesn't exist
    event = SlackEvent.from_type_subtype("reaction_added", "custom_subtype")
    assert event == SlackEvent.REACTION_ADDED


def test_slack_event_string_comparison() -> None:
    """Test that SlackEvent enums can be compared with strings."""
    assert SlackEvent.MESSAGE == "message"
    assert "app_mention" == SlackEvent.APP_MENTION
    assert "message.channels" == SlackEvent.MESSAGE_CHANNELS


def test_invalid_event_type() -> None:
    """Test that invalid event types raise ValueError."""
    with pytest.raises(ValueError):
        SlackEvent.from_type_subtype("not_a_real_event_type")


@pytest.mark.parametrize(
    "event_type,subtype,expected",
    [
        ("message", None, SlackEvent.MESSAGE),
        ("message", "channels", SlackEvent.MESSAGE_CHANNELS),
        ("reaction_added", None, SlackEvent.REACTION_ADDED),
        ("app_mention", None, SlackEvent.APP_MENTION),
        ("emoji_changed", None, SlackEvent.EMOJI_CHANGED),
        ("channel_created", None, SlackEvent.CHANNEL_CREATED),
    ],
)
def test_from_type_subtype_parametrized(event_type: str, subtype: Optional[str], expected: SlackEvent) -> None:
    """Test from_type_subtype with various combinations using parametrize."""
    assert SlackEvent.from_type_subtype(event_type, subtype) == expected


def test_newly_added_event_types() -> None:
    """Test that some of the newly added event types are correctly defined."""
    # Test a sample of the newly added event types
    assert SlackEvent.WORKFLOW_STEP_EXECUTE == "workflow_step_execute"
    assert SlackEvent.ASSISTANT_THREAD_STARTED == "assistant_thread_started"
    assert SlackEvent.USER_HUDDLE_CHANGED == "user_huddle_changed"
    assert SlackEvent.FILE_CREATED == "file_created"
    assert SlackEvent.SUBTEAM_MEMBERS_CHANGED == "subteam_members_changed"


def test_all_enum_members_are_strings() -> None:
    """Test that all enum members are properly defined as strings."""
    for member in SlackEvent:
        assert isinstance(member, str), f"Member {member.name} is not a string"
        assert member.value == member, f"Member {member.name} value doesn't match string representation"


def test_all_message_subtypes() -> None:
    """Test all message subtype combinations."""
    message_subtypes = {
        "app_home": SlackEvent.MESSAGE_APP_HOME,
        "channels": SlackEvent.MESSAGE_CHANNELS,
        "groups": SlackEvent.MESSAGE_GROUPS,
        "im": SlackEvent.MESSAGE_IM,
        "mpim": SlackEvent.MESSAGE_MPIM,
    }

    for subtype, enum_value in message_subtypes.items():
        # Check direct value
        assert enum_value == f"message.{subtype}"

        # Check from_type_subtype
        assert SlackEvent.from_type_subtype("message", subtype) == enum_value


def test_enum_comprehensive_coverage() -> None:
    """
    Verify that all Slack event types defined in the BaseSlackEventHandler
    have corresponding SlackEvent enum values.
    """
    # Get all SlackEvent enum values
    enum_values = set(item.value for item in SlackEvent)

    # Define expected Slack events based on common naming patterns
    standard_events = [
        "app_deleted",
        "app_home_opened",
        "app_installed",
        "app_mention",
        "app_rate_limited",
        "app_requested",
        "app_uninstalled",
        "app_uninstalled_team",
        "assistant_thread_context_changed",
        "assistant_thread_started",
        "call_rejected",
        "channel_archive",
        "channel_created",
        "channel_deleted",
        "channel_history_changed",
        "channel_id_changed",
        "channel_left",
        "channel_rename",
        "channel_shared",
        "channel_unarchive",
        "channel_unshared",
        "dnd_updated",
        "dnd_updated_user",
        "email_domain_changed",
        "emoji_changed",
        "file_change",
        "file_comment_added",
        "file_comment_deleted",
        "file_comment_edited",
        "file_created",
        "file_deleted",
        "file_public",
        "file_shared",
        "file_unshared",
        "function_executed",
        "grid_migration_finished",
        "grid_migration_started",
        "group_archive",
        "group_close",
        "group_deleted",
        "group_history_changed",
        "group_left",
        "group_open",
        "group_rename",
        "group_unarchive",
        "im_close",
        "im_created",
        "im_history_changed",
        "im_open",
        "invite_requested",
        "link_shared",
        "member_joined_channel",
        "member_left_channel",
        "message",
        "message_metadata_deleted",
        "message_metadata_posted",
        "message_metadata_updated",
        "pin_added",
        "pin_removed",
        "reaction_added",
        "reaction_removed",
        "resources_added",
        "resources_removed",
        "scope_denied",
        "scope_granted",
        "shared_channel_invite_accepted",
        "shared_channel_invite_approved",
        "shared_channel_invite_declined",
        "shared_channel_invite_received",
        "shared_channel_invite_requested",
        "star_added",
        "star_removed",
        "subteam_created",
        "subteam_members_changed",
        "subteam_self_added",
        "subteam_self_removed",
        "subteam_updated",
        "team_access_granted",
        "team_access_revoked",
        "team_domain_change",
        "team_join",
        "team_rename",
        "tokens_revoked",
        "url_verification",
        "user_change",
        "user_huddle_changed",
        "user_resource_denied",
        "user_resource_granted",
        "user_resource_removed",
        "workflow_deleted",
        "workflow_published",
        "workflow_step_deleted",
        "workflow_step_execute",
        "workflow_unpublished",
    ]

    # Message subtypes
    message_subtypes = ["message.app_home", "message.channels", "message.groups", "message.im", "message.mpim"]

    expected_events = set(standard_events + message_subtypes)

    # Check for missing events in the enum
    missing_events = expected_events - enum_values
    assert not missing_events, f"Missing events in SlackEvent enum: {missing_events}"

    # Check for extra events in the enum that weren't expected
    extra_events = enum_values - expected_events
    assert not extra_events, f"Unexpected events in SlackEvent enum: {extra_events}"


def test_from_type_subtype_edge_cases() -> None:
    """Test edge cases for the from_type_subtype method."""
    # Test case sensitivity
    with pytest.raises(ValueError):
        SlackEvent.from_type_subtype("MESSAGE")  # Should be lowercase

    # Test with empty string
    with pytest.raises(ValueError):
        SlackEvent.from_type_subtype("")

    # Test with whitespace
    with pytest.raises(ValueError):
        SlackEvent.from_type_subtype(" message ")

    # Test with invalid subtype format
    with pytest.raises(ValueError):
        # This should fail because "message." is not a valid event
        SlackEvent.from_type_subtype("message.")

    # Test with None type - Python raises ValueError at the enum level
    with pytest.raises(ValueError):
        SlackEvent.from_type_subtype(None)  # type: ignore


def test_type_safety() -> None:
    """Test type safety of SlackEvent enum operations."""
    # Verify type annotations on from_type_subtype method
    sig = inspect.signature(SlackEvent.from_type_subtype)
    params = sig.parameters

    # Check parameter types - need to handle string representation of annotations
    assert str(params["event_type"].annotation) == "str", "event_type param should be annotated as str"
    assert str(params["subtype"].annotation) == "str | None", "subtype param should be annotated as str | None"

    # Check return type - need to handle string representation of annotations
    assert str(sig.return_annotation) == "SlackEvent", "Return type should be SlackEvent"

    # Test type safety of string comparisons
    event = SlackEvent.MESSAGE
    assert isinstance(event, SlackEvent)
    assert isinstance(event, str)

    # Type hinting - these should not raise type errors
    def accepts_str(s: str) -> None:
        pass

    accepts_str(SlackEvent.MESSAGE)  # SlackEvent should be assignable to str


def test_enum_iteration() -> None:
    """Test that we can iterate through all enum values."""
    # Count the number of enum members
    count = 0
    for _ in SlackEvent:
        count += 1

    # Check we have a reasonable number of events (at least 90)
    assert count >= 90, f"Expected at least 90 SlackEvent members, got {count}"

    # Create a list of all enum names
    enum_names = [member.name for member in SlackEvent]

    # Verify some key events are in the list
    assert "MESSAGE" in enum_names
    assert "REACTION_ADDED" in enum_names
    assert "APP_MENTION" in enum_names
    assert "MESSAGE_CHANNELS" in enum_names

    # Verify all enum names follow the naming convention (uppercase with underscores)
    for name in enum_names:
        assert name.isupper() or "_" in name, f"Enum name {name} doesn't follow naming convention"


def test_slack_event_dict_usage() -> None:
    """Test using SlackEvent in dictionaries."""
    # Create a dictionary with SlackEvent keys
    handlers: Dict[SlackEvent, str] = {
        SlackEvent.MESSAGE: "handle_message",
        SlackEvent.REACTION_ADDED: "handle_reaction",
    }

    # Test lookup by enum
    assert handlers[SlackEvent.MESSAGE] == "handle_message"

    # Test lookup by string equivalent (this should work because SlackEvent inherits from str)
    assert handlers["message"] == "handle_message"

    # Test using from_type_subtype result for lookup
    event_type = SlackEvent.from_type_subtype("reaction_added")
    assert handlers[event_type] == "handle_reaction"
