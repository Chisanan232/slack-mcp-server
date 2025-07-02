#!/usr/bin/env python3
"""
Script to fetch and extract Slack event types from the official Slack API specification.

This script downloads the Slack Events API specification from GitHub and extracts
all event types defined in the specification. It can output the event types in 
different formats for use in the SlackEvent enum or for validation purposes.

Usage:
    python validate_slack_event_types.py [--output <format>] [--compare] [--validate [--strict]]

Options:
    --output   Output format: 'enum' (default), 'json', or 'list'
    --compare  Compare extracted events with current SlackEvent enum implementation
    --validate Validate that SlackEvent enum contains all events from API spec
               The script will exit with code 1 if validation fails
    --strict   When used with --validate, ensures the SlackEvent enum contains ONLY the events in the API spec
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.request


# URL of the Slack Events API specification
SLACK_EVENTS_API_URL = "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/events-api/slack_events_api_async_v1.json"

# Known message subtypes that might not be explicitly in the API spec
KNOWN_MESSAGE_SUBTYPES = [
    "message.app_home",
    "message.channels",
    "message.groups",
    "message.im",
    "message.mpim"
]

# Path to the SlackEvent enum implementation, relative to the script directory
SLACK_EVENT_ENUM_PATH = "../../slack_mcp/events.py"


def fetch_api_spec(url: str) -> Dict[str, Any]:
    """
    Fetch the Slack API specification JSON from the given URL.
    
    Args:
        url: URL of the Slack API specification
        
    Returns:
        Parsed JSON data as a dictionary
    
    Raises:
        urllib.error.URLError: If there's an error fetching the URL
        json.JSONDecodeError: If the response is not valid JSON
    """
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"Error fetching API specification: {e}", file=sys.stderr)
        sys.exit(1)


def extract_event_types(spec: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    """
    Extract all event types and subtypes from the Slack API specification.
    
    Args:
        spec: Slack API specification as a dictionary
        
    Returns:
        A tuple of two sets:
        - Set of standalone event types (e.g., 'message', 'reaction_added')
        - Set of combined type.subtype events (e.g., 'message.channels')
    """
    standard_events: Set[str] = set()
    subtype_events: Set[str] = set()
    
    # In the Slack Events API spec, events are defined as topics
    topics = spec.get("topics", {})
    
    for topic_key, topic_data in topics.items():
        if "subscribe" not in topic_data:
            continue
            
        subscribe_data = topic_data["subscribe"]
        
        # Get the event name from the external documentation URL
        event_name = None
        if "externalDocs" in subscribe_data:
            docs_url = subscribe_data["externalDocs"].get("url", "")
            if docs_url:
                # Extract event name from URL, which is more reliable
                url_parts = docs_url.split("/")
                if url_parts[-2] == "events" and url_parts[-1]:
                    event_name = url_parts[-1]
        
        # If we couldn't get from URL, try to derive from topic key
        if not event_name:
            # Topic keys in AsyncAPI use dots instead of underscores
            event_name = topic_key.replace(".", "_")
        
        # Check if this is an event with a subtype
        if "." in event_name:
            main_type, subtype = event_name.split(".", 1)
            # Add the main type as a standard event
            standard_events.add(main_type)
            # Add the full type.subtype format for subtype events
            subtype_events.add(event_name)
        else:
            standard_events.add(event_name)
    
    # Add additional known message subtypes if not already present
    for message_subtype in KNOWN_MESSAGE_SUBTYPES:
        if message_subtype not in subtype_events:
            # Make sure the base 'message' type exists
            standard_events.add("message")
            subtype_events.add(message_subtype)
    
    return standard_events, subtype_events


def get_current_enum_events() -> Tuple[Set[str], Set[str]]:
    """
    Extract events from the current SlackEvent enum implementation.
    
    Returns:
        A tuple of two sets:
        - Set of standard events (non-subtype events)
        - Set of subtype events (events with subtypes)
    """
    try:
        # Get the absolute path to the SlackEvent enum
        script_dir = os.path.dirname(os.path.abspath(__file__))
        enum_path = os.path.join(script_dir, SLACK_EVENT_ENUM_PATH)
        
        # Import the SlackEvent enum dynamically
        spec = importlib.util.spec_from_file_location("events", enum_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load module from {enum_path}")
        
        events_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(events_module)
        
        # Access the SlackEvent enum class
        slack_event_enum = getattr(events_module, "SlackEvent")
        
        standard_events: Set[str] = set()
        subtype_events: Set[str] = set()
        
        # Iterate through all enum values and separate into standard and subtype events
        for event in slack_event_enum:
            if isinstance(event, Enum):
                value = event.value
                if "." in value:
                    subtype_events.add(value)
                else:
                    standard_events.add(value)
        
        return standard_events, subtype_events
        
    except (ImportError, AttributeError) as e:
        print(f"Error importing SlackEvent enum: {e}", file=sys.stderr)
        return set(), set()


def compare_events(
    api_standard_events: Set[str],
    api_subtype_events: Set[str],
    enum_standard_events: Set[str],
    enum_subtype_events: Set[str]
) -> None:
    """
    Compare events from API and current enum implementation.
    
    Args:
        api_standard_events: Standard events from API
        api_subtype_events: Subtype events from API
        enum_standard_events: Standard events from current enum
        enum_subtype_events: Subtype events from current enum
    """
    # Find missing standard events in enum (in API but not in enum)
    missing_in_enum_standard = api_standard_events - enum_standard_events
    # Find extra standard events in enum (in enum but not in API)
    extra_in_enum_standard = enum_standard_events - api_standard_events
    
    # Same for subtype events
    missing_in_enum_subtype = api_subtype_events - enum_subtype_events
    extra_in_enum_subtype = enum_subtype_events - api_subtype_events
    
    # Report findings
    print("\nComparison with current SlackEvent enum implementation:")
    print("=" * 50)
    
    if missing_in_enum_standard:
        print("\nStandard events in API but missing in enum:")
        for event in sorted(missing_in_enum_standard):
            print(f"    {event}")
    
    if missing_in_enum_subtype:
        print("\nSubtype events in API but missing in enum:")
        for event in sorted(missing_in_enum_subtype):
            print(f"    {event}")
    
    if extra_in_enum_standard:
        print("\nExtra standard events in enum not found in API:")
        for event in sorted(extra_in_enum_standard):
            print(f"    {event}")
    
    if extra_in_enum_subtype:
        print("\nExtra subtype events in enum not found in API:")
        for event in sorted(extra_in_enum_subtype):
            print(f"    {event}")
    
    if not (missing_in_enum_standard or missing_in_enum_subtype or 
            extra_in_enum_standard or extra_in_enum_subtype):
        print("\nNo discrepancies found. SlackEvent enum is in sync with the API specification.")


def validate_enum_completeness(
    api_standard_events: Set[str],
    api_subtype_events: Set[str],
    enum_standard_events: Set[str],
    enum_subtype_events: Set[str],
    strict: bool = False
) -> bool:
    """
    Validate that the SlackEvent enum contains all events from the API spec.
    
    Args:
        api_standard_events: Standard events from API
        api_subtype_events: Subtype events from API
        enum_standard_events: Standard events from current enum
        enum_subtype_events: Subtype events from current enum
        strict: If True, ensures exact match (no extra events allowed in enum)
    
    Returns:
        True if validation succeeds, False if validation fails
    """
    # Check for missing events (API events not in enum)
    missing_standard = api_standard_events - enum_standard_events
    missing_subtype = api_subtype_events - enum_subtype_events
    
    # Check for extra events (enum events not in API)
    extra_standard = enum_standard_events - api_standard_events
    extra_subtype = enum_subtype_events - api_subtype_events
    
    # Build error message if needed
    error_msg_parts = []
    
    if missing_standard or missing_subtype:
        error_msg_parts.append(
            "SlackEvent enum is missing events from the API specification:"
        )
        if missing_standard:
            error_msg_parts.append("\nMissing standard events:")
            for event in sorted(missing_standard):
                error_msg_parts.append(f"  - {event}")
        
        if missing_subtype:
            error_msg_parts.append("\nMissing subtype events:")
            for event in sorted(missing_subtype):
                error_msg_parts.append(f"  - {event}")
    
    if strict and (extra_standard or extra_subtype):
        if not error_msg_parts:  # If this is the first error, add header
            error_msg_parts.append(
                "SlackEvent enum contains events not present in the API specification:"
            )
        else:
            error_msg_parts.append("\nAdditionally, the enum contains extra events not in API:")
        
        if extra_standard:
            error_msg_parts.append("\nExtra standard events:")
            for event in sorted(extra_standard):
                error_msg_parts.append(f"  - {event}")
        
        if extra_subtype:
            error_msg_parts.append("\nExtra subtype events:")
            for event in sorted(extra_subtype):
                error_msg_parts.append(f"  - {event}")
    
    if error_msg_parts:
        # Add suggestion for fixing the issue
        error_msg_parts.append("\nSuggested action:")
        if missing_standard or missing_subtype:
            enum_additions = [f"    {convert_to_enum_name(e)} = \"{e}\"" for e in sorted(missing_standard)] + \
                            [f"    {convert_to_enum_name(e)} = \"{e}\"" for e in sorted(missing_subtype)]
            error_msg_parts.append("Add the following lines to the SlackEvent enum:")
            error_msg_parts.append("\n".join(enum_additions))
        
        if strict and (extra_standard or extra_subtype):
            error_msg_parts.append("\nConsider removing events not in the API specification or disable strict mode.")
        
        # Print the error message instead of raising an exception
        print("\nVALIDATION FAILED:", file=sys.stderr)
        print("\n".join(error_msg_parts), file=sys.stderr)
        return False
    else:
        if strict:
            print("\nValidation: SlackEvent enum exactly matches all events from API specification.")
        else:
            print("\nValidation: SlackEvent enum contains all events from API specification.")
        return True


def generate_update_code(
    api_standard_events: Set[str],
    api_subtype_events: Set[str],
    enum_standard_events: Set[str],
    enum_subtype_events: Set[str]
) -> str:
    """
    Generate Python code that can be used to update the SlackEvent enum.
    
    Args:
        api_standard_events: Standard events from API
        api_subtype_events: Subtype events from API
        enum_standard_events: Standard events from current enum
        enum_subtype_events: Subtype events from current enum
        
    Returns:
        String containing Python code to update the enum
    """
    missing_standard = api_standard_events - enum_standard_events
    missing_subtype = api_subtype_events - enum_subtype_events
    
    if not missing_standard and not missing_subtype:
        return "# No updates needed - SlackEvent enum already contains all API events"
    
    code_parts = []
    
    if missing_standard:
        code_parts.append("# New standard events to add")
        for event in sorted(missing_standard):
            code_parts.append(f"    {convert_to_enum_name(event)} = \"{event}\"")
    
    if missing_subtype:
        if code_parts:  # Add a blank line if there were standard events
            code_parts.append("")
        code_parts.append("# New subtype events to add")
        for event in sorted(missing_subtype):
            code_parts.append(f"    {convert_to_enum_name(event)} = \"{event}\"")
    
    return "\n".join(code_parts)


def convert_to_enum_name(event_name: str) -> str:
    """
    Convert an event name to a valid Python enum name.
    
    Args:
        event_name: The event name to convert
        
    Returns:
        A valid Python enum name in UPPER_SNAKE_CASE
    """
    if "." in event_name:
        event_type, subtype = event_name.split(".", 1)
        return f"{event_type.upper()}_{subtype.upper()}"
    else:
        return event_name.upper()


def format_as_enum(event_types: Set[str], subtype_events: Set[str]) -> List[str]:
    """
    Format the event types as Python enum definitions.
    
    Args:
        event_types: Set of standard event types
        subtype_events: Set of type.subtype event combinations
        
    Returns:
        List of formatted enum definitions
    """
    enum_lines: List[str] = []
    
    # Add standard events
    for event in sorted(event_types):
        enum_name = convert_to_enum_name(event)
        enum_lines.append(f'    {enum_name} = "{event}"')
    
    # Add message subtypes
    for event in sorted(subtype_events):
        enum_name = convert_to_enum_name(event)
        enum_lines.append(f'    {enum_name} = "{event}"')
    
    return enum_lines


def format_as_list(event_types: Set[str], subtype_events: Set[str]) -> List[str]:
    """
    Format the event types as a simple Python list.
    
    Args:
        event_types: Set of standard event types
        subtype_events: Set of type.subtype event combinations
        
    Returns:
        List of formatted strings for list items
    """
    list_lines: List[str] = []
    
    # Add standard events
    for event in sorted(event_types):
        list_lines.append(f'    "{event}",')
    
    # Add subtype events
    for event in sorted(subtype_events):
        list_lines.append(f'    "{event}",')
    
    return list_lines


def format_output(
    event_types: Set[str],
    subtype_events: Set[str],
    output_format: str
) -> str:
    """
    Format the event types according to the specified output format.
    
    Args:
        event_types: Set of standard event types
        subtype_events: Set of type.subtype event combinations
        output_format: Format to output ('enum', 'json', or 'list')
        
    Returns:
        Formatted output string
    """
    if output_format == "json":
        all_events = sorted(list(event_types) + list(subtype_events))
        return json.dumps(all_events, indent=2)
    
    elif output_format == "list":
        lines = format_as_list(event_types, subtype_events)
        return "[\n" + "\n".join(lines) + "\n]"
    
    else:  # Default: enum
        # First standard events, then a comment, then subtype events
        standard_lines = format_as_enum(event_types, set())
        subtype_lines = format_as_enum(set(), subtype_events)
        
        result = "# Standard events\n"
        result += "\n".join(standard_lines)
        result += "\n\n# Message subtypes\n"
        result += "\n".join(subtype_lines)
        
        return result


def main() -> None:
    """
    Main entry point for the script.
    """
    parser = argparse.ArgumentParser(description="Extract Slack event types from API specification")
    parser.add_argument(
        "--output",
        choices=["enum", "json", "list"],
        default="enum",
        help="Output format (default: enum)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare extracted events with current SlackEvent enum implementation"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that all API events are in SlackEvent enum (exits with code 1 if validation fails)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="When used with --validate, ensures SlackEvent enum contains ONLY the events in API spec"
    )
    parser.add_argument(
        "--generate-update",
        action="store_true",
        help="Generate code to update SlackEvent enum with any missing events"
    )
    args = parser.parse_args()

    print(f"Fetching Slack Events API specification from: {SLACK_EVENTS_API_URL}")
    spec = fetch_api_spec(SLACK_EVENTS_API_URL)
    
    print("Extracting event types...")
    api_standard_events, api_subtype_events = extract_event_types(spec)
    
    total_events = len(api_standard_events) + len(api_subtype_events)
    print(f"Found {len(api_standard_events)} standard event types and {len(api_subtype_events)} subtype events "
          f"(total: {total_events})")
    
    formatted_output = format_output(api_standard_events, api_subtype_events, args.output)
    print("\nOutput:")
    print(formatted_output)
    
    # Track validation status
    validation_success = True
    
    if args.compare or args.validate or args.generate_update:
        enum_standard_events, enum_subtype_events = get_current_enum_events()
        if enum_standard_events or enum_subtype_events:
            if args.compare:
                compare_events(
                    api_standard_events, 
                    api_subtype_events,
                    enum_standard_events,
                    enum_subtype_events
                )
            
            if args.validate:
                validation_success = validate_enum_completeness(
                    api_standard_events,
                    api_subtype_events,
                    enum_standard_events,
                    enum_subtype_events,
                    args.strict
                )
                
            if args.generate_update:
                update_code = generate_update_code(
                    api_standard_events,
                    api_subtype_events,
                    enum_standard_events,
                    enum_subtype_events
                )
                print("\nGenerated code to update SlackEvent enum:")
                print("=" * 50)
                print(update_code)
                print("=" * 50)
        else:
            print("\nCould not load current SlackEvent enum for comparison or validation.")
            if args.validate:
                validation_success = False
    
    # Exit with appropriate code
    if not validation_success:
        print("\nValidation failed. Exiting with code 1.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
