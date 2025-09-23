#!/usr/bin/env python3
"""
Comprehensive PyTest-based tests for the validate_slack_event_types.py CI script.

This test suite covers all functionality including:
- API specification fetching and parsing
- Event type extraction from Slack API spec
- SlackEvent enum loading and comparison
- Validation logic with strict and non-strict modes
- Output formatting functions
- CLI argument handling and integration tests

Uses PyTest conventions and modern typing (PEP 484/PEP 585).
"""

from __future__ import annotations

import json
import os
import sys
from enum import Enum
from io import StringIO
from unittest.mock import MagicMock, Mock, patch
from urllib.error import URLError

import pytest

# Add the scripts/ci directory to sys.path to import the module under test
script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ci_script_path = os.path.join(script_dir, "scripts", "ci")
sys.path.insert(0, ci_script_path)

# Import the module under test
import validate_slack_event_types as script_module


# PyTest Fixtures
@pytest.fixture
def sample_api_spec() -> dict[str, any]:
    """Sample API specification structure (simplified version of actual Slack API spec)."""
    return {
        "topics": {
            "message": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/message"
                    }
                }
            },
            "reaction.added": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/reaction_added"
                    }
                }
            },
            "message.channels": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/message.channels"
                    }
                }
            },
            "app_mention": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/app_mention"
                    }
                }
            },
            "user_change": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/user_change"
                    }
                }
            }
        }
    }


@pytest.fixture
def expected_events() -> tuple[set[str], set[str]]:
    """Expected extracted events from sample API spec."""
    standard_events = {"message", "reaction_added", "app_mention", "user_change"}
    subtype_events = {"message.channels", "message.app_home", "message.groups", "message.im", "message.mpim"}
    return standard_events, subtype_events


@pytest.fixture
def sample_enum_events() -> tuple[set[str], set[str]]:
    """Sample enum events (what's currently in the enum)."""
    standard = {"message", "reaction_added", "app_mention", "user_change", "extra_event"}
    subtype = {"message.channels"}
    return standard, subtype


@pytest.fixture(autouse=True)
def setup_and_cleanup() -> None:
    """Automatic setup and cleanup for all tests."""
    # Setup is already done by adding to sys.path at module level
    yield
    # Cleanup: Remove the CI script path from sys.path if it exists
    if ci_script_path in sys.path:
        sys.path.remove(ci_script_path)


# Tests for the fetch_api_spec function
@patch('validate_slack_event_types.urllib.request.urlopen')
def test_fetch_api_spec_success(mock_urlopen: Mock, sample_api_spec: dict[str, any]) -> None:
    """Test successful API specification fetching."""
    # Mock the URL response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(sample_api_spec).encode('utf-8')
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    mock_urlopen.return_value = mock_response

    result = script_module.fetch_api_spec("https://example.com/api.json")

    assert result == sample_api_spec
    mock_urlopen.assert_called_once_with("https://example.com/api.json")


@patch('validate_slack_event_types.urllib.request.urlopen')
@patch('validate_slack_event_types.sys.exit')
def test_fetch_api_spec_url_error(mock_exit: Mock, mock_urlopen: Mock) -> None:
    """Test handling of URL errors when fetching API spec."""
    mock_urlopen.side_effect = URLError("Connection failed")

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        script_module.fetch_api_spec("https://invalid-url.com/api.json")

    mock_exit.assert_called_once_with(1)
    error_output = mock_stderr.getvalue()
    assert "Error fetching API specification" in error_output
    assert "Connection failed" in error_output


@patch('validate_slack_event_types.urllib.request.urlopen')
@patch('validate_slack_event_types.sys.exit')
def test_fetch_api_spec_json_decode_error(mock_exit: Mock, mock_urlopen: Mock) -> None:
    """Test handling of JSON decode errors."""
    mock_response = MagicMock()
    mock_response.read.return_value = b"invalid json content"
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None
    mock_urlopen.return_value = mock_response

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        script_module.fetch_api_spec("https://example.com/api.json")

    mock_exit.assert_called_once_with(1)
    error_output = mock_stderr.getvalue()
    assert "Error fetching API specification" in error_output


# Tests for the extract_event_types function
def test_extract_event_types_basic(sample_api_spec: dict[str, any]) -> None:
    """Test basic event type extraction from API spec."""
    standard_events, subtype_events = script_module.extract_event_types(sample_api_spec)

    # Should include the main events from the spec
    assert "message" in standard_events
    assert "reaction_added" in standard_events
    assert "app_mention" in standard_events
    assert "user_change" in standard_events

    # Should include the subtype event from spec plus known message subtypes
    assert "message.channels" in subtype_events
    # Should include known message subtypes even if not in spec
    for known_subtype in script_module.KNOWN_MESSAGE_SUBTYPES:
        assert known_subtype in subtype_events


def test_extract_event_types_no_external_docs() -> None:
    """Test event extraction when externalDocs URL is missing."""
    spec_without_docs = {
        "topics": {
            "custom_event": {
                "subscribe": {}
            }
        }
    }

    standard_events, subtype_events = script_module.extract_event_types(spec_without_docs)

    # Should fall back to using topic key (with dots replaced by underscores)
    assert "custom_event" in standard_events


def test_extract_event_types_empty_spec() -> None:
    """Test event extraction from empty or invalid spec."""
    empty_spec: dict[str, any] = {}
    standard_events, subtype_events = script_module.extract_event_types(empty_spec)

    # Should still include known message subtypes
    for known_subtype in script_module.KNOWN_MESSAGE_SUBTYPES:
        assert known_subtype in subtype_events
    # Should have message as standard event due to known subtypes
    assert "message" in standard_events


def test_extract_event_types_subtype_handling() -> None:
    """Test proper handling of events with subtypes."""
    spec_with_subtypes = {
        "topics": {
            "message.im": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/message.im"
                    }
                }
            },
            "file.change": {
                "subscribe": {
                    "externalDocs": {
                        "url": "https://api.slack.com/events/file.change"
                    }
                }
            }
        }
    }

    standard_events, subtype_events = script_module.extract_event_types(spec_with_subtypes)

    # Should have main event types
    assert "message" in standard_events
    assert "file" in standard_events
    # Should have subtype events
    assert "message.im" in subtype_events
    assert "file.change" in subtype_events


# Tests for the get_current_enum_events function
@patch('validate_slack_event_types.importlib.util.spec_from_file_location')
@patch('validate_slack_event_types.importlib.util.module_from_spec')
def test_get_current_enum_events_success(mock_module_from_spec: Mock, mock_spec_from_file: Mock) -> None:
    """Test successful loading of SlackEvent enum."""
    # Create mock event objects with values
    class MockEventValue:
        def __init__(self, value: str) -> None:
            self.value = value
    
    # Create individual enum instances
    message_event = MockEventValue("message")
    reaction_event = MockEventValue("reaction_added")
    channel_event = MockEventValue("message.channels")
    mention_event = MockEventValue("app_mention")
    
    mock_enum_values = [message_event, reaction_event, channel_event, mention_event]

    # Create a mock enum class that properly iterates
    class MockSlackEvent:
        def __iter__(self) -> list[MockEventValue]:
            return iter(mock_enum_values)

    # Mock the module loading
    mock_spec = Mock()
    mock_spec.loader = Mock()
    mock_spec_from_file.return_value = mock_spec

    mock_module = Mock()
    mock_module.SlackEvent = MockSlackEvent()
    mock_module_from_spec.return_value = mock_module

    # Patch isinstance within the module to make our mock objects appear as Enum instances
    with patch('validate_slack_event_types.isinstance') as mock_isinstance:
        def isinstance_side_effect(obj: any, cls: type) -> bool:
            if cls == Enum and hasattr(obj, 'value'):
                return True
            return type(obj) == cls or isinstance(type(obj), type(cls))
        
        mock_isinstance.side_effect = isinstance_side_effect
        
        standard_events, subtype_events = script_module.get_current_enum_events()

    # Verify results
    assert "message" in standard_events
    assert "reaction_added" in standard_events
    assert "app_mention" in standard_events
    assert "message.channels" in subtype_events


@patch('validate_slack_event_types.importlib.util.spec_from_file_location')
def test_get_current_enum_events_import_error(mock_spec_from_file: Mock) -> None:
    """Test handling of import errors when loading enum."""
    mock_spec_from_file.return_value = None

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        standard_events, subtype_events = script_module.get_current_enum_events()

    # Should return empty sets on error
    assert standard_events == set()
    assert subtype_events == set()
    # Should log error message
    error_output = mock_stderr.getvalue()
    assert "Error importing SlackEvent enum" in error_output


@patch('validate_slack_event_types.importlib.util.spec_from_file_location')
@patch('validate_slack_event_types.importlib.util.module_from_spec')
def test_get_current_enum_events_attribute_error(mock_module_from_spec: Mock, mock_spec_from_file: Mock) -> None:
    """Test handling when SlackEvent attribute is missing."""
    mock_spec = Mock()
    mock_spec.loader = Mock()
    mock_spec_from_file.return_value = mock_spec

    mock_module = Mock()
    # Simulate missing SlackEvent attribute
    mock_module.SlackEvent = None
    del mock_module.SlackEvent
    mock_module_from_spec.return_value = mock_module

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        standard_events, subtype_events = script_module.get_current_enum_events()

    # Should return empty sets on error
    assert standard_events == set()
    assert subtype_events == set()
    # Should log error message
    error_output = mock_stderr.getvalue()
    assert "Error importing SlackEvent enum" in error_output


# Tests for the compare_events function
def test_compare_events_no_differences() -> None:
    """Test comparison when API and enum events match perfectly."""
    api_standard = {"message", "reaction_added"}
    api_subtype = {"message.channels"}
    enum_standard = {"message", "reaction_added"}
    enum_subtype = {"message.channels"}

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        script_module.compare_events(api_standard, api_subtype, enum_standard, enum_subtype)

    output = mock_stdout.getvalue()
    assert "No discrepancies found" in output
    assert "SlackEvent enum is in sync" in output


def test_compare_events_missing_in_enum() -> None:
    """Test comparison when enum is missing events from API."""
    api_standard = {"message", "reaction_added", "app_mention"}
    api_subtype = {"message.channels", "message.im"}
    enum_standard = {"message", "reaction_added"}
    enum_subtype = {"message.channels"}

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        script_module.compare_events(api_standard, api_subtype, enum_standard, enum_subtype)

    output = mock_stdout.getvalue()
    assert "missing in enum" in output
    assert "app_mention" in output
    assert "message.im" in output


def test_compare_events_extra_in_enum() -> None:
    """Test comparison when enum has extra events not in API."""
    api_standard = {"message", "reaction_added"}
    api_subtype = {"message.channels"}
    enum_standard = {"message", "reaction_added", "custom_event"}
    enum_subtype = {"message.channels", "message.custom"}

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        script_module.compare_events(api_standard, api_subtype, enum_standard, enum_subtype)

    output = mock_stdout.getvalue()
    assert "Extra" in output
    assert "custom_event" in output
    assert "message.custom" in output


# Tests for the validate_enum_completeness function
def test_validate_enum_completeness_success() -> None:
    """Test successful validation when enum contains all API events."""
    api_standard = {"message", "reaction_added"}
    api_subtype = {"message.channels"}
    enum_standard = {"message", "reaction_added", "extra_event"}  # Extra is OK in non-strict
    enum_subtype = {"message.channels"}

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        result = script_module.validate_enum_completeness(
            api_standard, api_subtype, enum_standard, enum_subtype, strict=False
        )

    assert result is True
    output = mock_stdout.getvalue()
    assert "Validation:" in output
    assert "contains all events" in output


def test_validate_enum_completeness_missing_events() -> None:
    """Test validation failure when enum is missing API events."""
    api_standard = {"message", "reaction_added", "app_mention"}
    api_subtype = {"message.channels", "message.im"}
    enum_standard = {"message", "reaction_added"}
    enum_subtype = {"message.channels"}

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        result = script_module.validate_enum_completeness(
            api_standard, api_subtype, enum_standard, enum_subtype, strict=False
        )

    assert result is False
    error_output = mock_stderr.getvalue()
    assert "VALIDATION FAILED" in error_output
    assert "Missing standard events" in error_output
    assert "app_mention" in error_output
    assert "Missing subtype events" in error_output
    assert "message.im" in error_output


def test_validate_enum_completeness_strict_mode_success() -> None:
    """Test strict validation success when enum exactly matches API."""
    api_standard = {"message", "reaction_added"}
    api_subtype = {"message.channels"}
    enum_standard = {"message", "reaction_added"}
    enum_subtype = {"message.channels"}

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        result = script_module.validate_enum_completeness(
            api_standard, api_subtype, enum_standard, enum_subtype, strict=True
        )

    assert result is True
    output = mock_stdout.getvalue()
    assert "exactly matches" in output


def test_validate_enum_completeness_strict_mode_extra_events() -> None:
    """Test strict validation failure when enum has extra events."""
    api_standard = {"message", "reaction_added"}
    api_subtype = {"message.channels"}
    enum_standard = {"message", "reaction_added", "extra_event"}
    enum_subtype = {"message.channels", "message.custom"}

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        result = script_module.validate_enum_completeness(
            api_standard, api_subtype, enum_standard, enum_subtype, strict=True
        )

    assert result is False
    error_output = mock_stderr.getvalue()
    assert "VALIDATION FAILED" in error_output
    assert "Extra standard events" in error_output
    assert "extra_event" in error_output
    assert "Extra subtype events" in error_output
    assert "message.custom" in error_output


# Tests for utility functions
@pytest.mark.parametrize("event_name,expected", [
    ("message", "MESSAGE"),
    ("reaction_added", "REACTION_ADDED"),
    ("app_mention", "APP_MENTION"),
])
def test_convert_to_enum_name_standard_event(event_name: str, expected: str) -> None:
    """Test conversion of standard event names to enum names."""
    assert script_module.convert_to_enum_name(event_name) == expected


@pytest.mark.parametrize("event_name,expected", [
    ("message.channels", "MESSAGE_CHANNELS"),
    ("file.change", "FILE_CHANGE"),
    ("message.im", "MESSAGE_IM"),
])
def test_convert_to_enum_name_subtype_event(event_name: str, expected: str) -> None:
    """Test conversion of subtype event names to enum names."""
    assert script_module.convert_to_enum_name(event_name) == expected


def test_format_as_enum() -> None:
    """Test formatting events as enum definitions."""
    standard_events = {"message", "reaction_added"}
    subtype_events = {"message.channels"}

    result = script_module.format_as_enum(standard_events, subtype_events)

    # Should contain properly formatted enum definitions (result is a list)
    result_str = "\n".join(result)
    assert 'MESSAGE = "message"' in result_str
    assert 'REACTION_ADDED = "reaction_added"' in result_str
    assert 'MESSAGE_CHANNELS = "message.channels"' in result_str


def test_format_as_list() -> None:
    """Test formatting events as a Python list."""
    standard_events = {"message", "reaction_added"}
    subtype_events = {"message.channels"}

    result = script_module.format_as_list(standard_events, subtype_events)

    # Should contain properly formatted list items (result is a list)
    result_str = "\n".join(result)
    assert '"message",' in result_str
    assert '"reaction_added",' in result_str
    assert '"message.channels",' in result_str


def test_format_output_json() -> None:
    """Test JSON output formatting."""
    standard_events = {"message", "reaction_added"}
    subtype_events = {"message.channels"}

    result = script_module.format_output(standard_events, subtype_events, "json")

    # Should be valid JSON
    parsed = json.loads(result)
    assert "message" in parsed
    assert "reaction_added" in parsed
    assert "message.channels" in parsed


def test_format_output_list() -> None:
    """Test list output formatting."""
    standard_events = {"message", "reaction_added"}
    subtype_events = {"message.channels"}

    result = script_module.format_output(standard_events, subtype_events, "list")

    # Should be properly formatted list
    assert result.startswith("[")
    assert result.endswith("]")
    assert '"message",' in result
    assert '"reaction_added",' in result
    assert '"message.channels",' in result


def test_format_output_enum() -> None:
    """Test enum output formatting."""
    standard_events = {"message", "reaction_added"}
    subtype_events = {"message.channels"}

    result = script_module.format_output(standard_events, subtype_events, "enum")

    # Should contain enum formatting with comments
    assert "# Standard events" in result
    assert "# Message subtypes" in result
    assert 'MESSAGE = "message"' in result
    assert 'MESSAGE_CHANNELS = "message.channels"' in result


# Tests for the generate_update_code function
def test_generate_update_code_no_missing_events() -> None:
    """Test code generation when no events are missing."""
    api_standard = {"message", "reaction_added"}
    api_subtype = {"message.channels"}
    enum_standard = {"message", "reaction_added"}
    enum_subtype = {"message.channels"}

    result = script_module.generate_update_code(api_standard, api_subtype, enum_standard, enum_subtype)

    assert "No updates needed" in result


def test_generate_update_code_missing_events() -> None:
    """Test code generation when events are missing from enum."""
    api_standard = {"message", "reaction_added", "app_mention"}
    api_subtype = {"message.channels", "message.im"}
    enum_standard = {"message", "reaction_added"}
    enum_subtype = {"message.channels"}

    result = script_module.generate_update_code(api_standard, api_subtype, enum_standard, enum_subtype)

    assert "New standard events to add" in result
    assert 'APP_MENTION = "app_mention"' in result
    assert "New subtype events to add" in result
    assert 'MESSAGE_IM = "message.im"' in result


# Integration tests for the main function
@patch('validate_slack_event_types.fetch_api_spec')
@patch('validate_slack_event_types.extract_event_types')
@patch('validate_slack_event_types.sys.argv')
def test_main_basic_output(
    mock_argv: Mock, 
    mock_extract: Mock, 
    mock_fetch: Mock, 
    sample_api_spec: dict[str, any]
) -> None:
    """Test main function with basic output formatting."""
    mock_argv.__getitem__.side_effect = lambda x: ["script_name"][x]
    mock_argv.__len__.return_value = 1
    mock_fetch.return_value = sample_api_spec
    mock_extract.return_value = ({"message", "reaction_added"}, {"message.channels"})

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        script_module.main()

    output = mock_stdout.getvalue()
    assert "Fetching Slack Events API specification" in output
    assert "Extracting event types" in output
    assert "Found" in output
    assert "Output:" in output


@patch('validate_slack_event_types.fetch_api_spec')
@patch('validate_slack_event_types.extract_event_types')
@patch('validate_slack_event_types.get_current_enum_events')
@patch('validate_slack_event_types.sys.argv')
def test_main_with_compare_flag(
    mock_argv: Mock, 
    mock_get_current: Mock, 
    mock_extract: Mock, 
    mock_fetch: Mock,
    sample_api_spec: dict[str, any]
) -> None:
    """Test main function with --compare flag."""
    mock_argv.__getitem__.side_effect = lambda x: ["script_name", "--compare"][x]
    mock_argv.__len__.return_value = 2
    mock_fetch.return_value = sample_api_spec
    mock_extract.return_value = ({"message", "reaction_added"}, {"message.channels"})
    mock_get_current.return_value = ({"message", "reaction_added"}, {"message.channels"})

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        script_module.main()

    output = mock_stdout.getvalue()
    assert "Comparison with current SlackEvent enum" in output


@patch('validate_slack_event_types.fetch_api_spec')
@patch('validate_slack_event_types.extract_event_types')
@patch('validate_slack_event_types.get_current_enum_events')
@patch('validate_slack_event_types.validate_enum_completeness')
@patch('validate_slack_event_types.sys.argv')
@patch('validate_slack_event_types.sys.exit')
def test_main_with_validate_flag_failure(
    mock_exit: Mock, 
    mock_argv: Mock, 
    mock_validate: Mock, 
    mock_get_current: Mock, 
    mock_extract: Mock, 
    mock_fetch: Mock,
    sample_api_spec: dict[str, any]
) -> None:
    """Test main function with --validate flag when validation fails."""
    mock_argv.__getitem__.side_effect = lambda x: ["script_name", "--validate"][x]
    mock_argv.__len__.return_value = 2
    mock_fetch.return_value = sample_api_spec
    mock_extract.return_value = ({"message", "reaction_added"}, {"message.channels"})
    mock_get_current.return_value = ({"message"}, set())
    mock_validate.return_value = False  # Validation fails

    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        script_module.main()

    mock_exit.assert_called_once_with(1)
    error_output = mock_stderr.getvalue()
    assert "Validation failed" in error_output


@patch('validate_slack_event_types.fetch_api_spec')
@patch('validate_slack_event_types.extract_event_types')
@patch('validate_slack_event_types.get_current_enum_events')
@patch('validate_slack_event_types.generate_update_code')
@patch('validate_slack_event_types.sys.argv')
def test_main_with_generate_update_flag(
    mock_argv: Mock, 
    mock_generate: Mock, 
    mock_get_current: Mock, 
    mock_extract: Mock, 
    mock_fetch: Mock,
    sample_api_spec: dict[str, any]
) -> None:
    """Test main function with --generate-update flag."""
    mock_argv.__getitem__.side_effect = lambda x: ["script_name", "--generate-update"][x]
    mock_argv.__len__.return_value = 2
    mock_fetch.return_value = sample_api_spec
    mock_extract.return_value = ({"message", "reaction_added"}, {"message.channels"})
    mock_get_current.return_value = ({"message"}, set())
    mock_generate.return_value = 'APP_MENTION = "app_mention"'

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        script_module.main()

    output = mock_stdout.getvalue()
    assert "Generated code to update" in output
    assert 'APP_MENTION = "app_mention"' in output
