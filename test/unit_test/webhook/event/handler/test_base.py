"""
PyTest-based tests for the BaseSlackEventHandler class.

This module tests the BaseSlackEventHandler functionality including:
- Method resolution for various event types
- Proper handling of event types with subtypes
- Custom handler implementations via subclassing
- Fallback to on_unknown for unimplemented handlers
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from slack_mcp.webhook.event.handler.base import BaseSlackEventHandler


class TestBaseSlackEventHandler:
    """Test suite for BaseSlackEventHandler."""

    @pytest.fixture
    def handler(self) -> BaseSlackEventHandler:
        """Fixture providing a BaseSlackEventHandler instance."""
        return BaseSlackEventHandler()

    @pytest.mark.asyncio
    async def test_resolve_basic_event(self, handler: BaseSlackEventHandler) -> None:
        """Test that _resolve correctly identifies handlers for basic event types."""
        # Patch the handler methods
        with patch.object(handler, "on_message") as mock_on_message:
            event = {"type": "message", "text": "Hello"}
            fn = handler._resolve(event)
            await fn(event)
            mock_on_message.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_resolve_event_with_subtype(self, handler: BaseSlackEventHandler) -> None:
        """Test that _resolve correctly identifies handlers for events with subtypes."""
        # Patch the handler methods
        with patch.object(handler, "on_message__channels") as mock_on_message_channels:
            event = {"type": "message", "subtype": "channels", "text": "Channel message"}
            fn = handler._resolve(event)
            await fn(event)
            mock_on_message_channels.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_fallback_to_type_when_no_subtype_handler(self, handler: BaseSlackEventHandler) -> None:
        """Test fallback to type-only handler when no handler exists for the subtype."""
        # Patch the handler methods
        with patch.object(handler, "on_message") as mock_on_message:
            # Create event with subtype that doesn't have a specific handler
            event = {"type": "message", "subtype": "nonexistent_subtype", "text": "Test"}

            # First confirm the specific handler doesn't exist
            assert not hasattr(handler, "on_message__nonexistent_subtype")

            # Then test the fallback
            fn = handler._resolve(event)
            await fn(event)
            mock_on_message.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_fallback_to_unknown_handler(self, handler: BaseSlackEventHandler) -> None:
        """Test fallback to on_unknown when no handler exists for the event type."""
        # Patch the handler methods
        with patch.object(handler, "on_unknown") as mock_on_unknown:
            event = {"type": "nonexistent_event_type", "text": "Test"}
            fn = handler._resolve(event)
            await fn(event)
            mock_on_unknown.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_event(self, handler: BaseSlackEventHandler) -> None:
        """Test the main handle_event method delegates correctly."""
        # Create a spy on _resolve to check it's being called
        with patch.object(handler, "_resolve") as mock_resolve:
            # Mock what _resolve would return - use AsyncMock for async function
            mock_handler = AsyncMock()
            mock_resolve.return_value = mock_handler

            # Call handle_event
            event = {"type": "message", "text": "Test message"}
            await handler.handle_event(event)

            # Verify _resolve was called with the event
            mock_resolve.assert_called_once_with(event)

            # Verify the handler returned by _resolve was called with the event
            mock_handler.assert_called_once_with(event)


class CustomHandler(BaseSlackEventHandler):
    """Custom handler implementation for testing subclassing behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.events_received: List[Dict[str, Any]] = []

    async def on_message(self, event: Dict[str, Any]) -> None:
        self.events_received.append(event)
        event["processed_by"] = "on_message"

    async def on_reaction_added(self, event: Dict[str, Any]) -> None:
        self.events_received.append(event)
        event["processed_by"] = "on_reaction_added"

    async def on_app_home_opened(self, event: Dict[str, Any]) -> None:
        self.events_received.append(event)
        event["processed_by"] = "on_app_home_opened"

    async def on_unknown(self, event: Dict[str, Any]) -> None:
        self.events_received.append(event)
        event["processed_by"] = "on_unknown"


class TestCustomHandler:
    """Test suite for custom handler implementations."""

    @pytest.fixture
    def custom_handler(self) -> CustomHandler:
        """Fixture providing a CustomHandler instance."""
        return CustomHandler()

    @pytest.mark.asyncio
    async def test_custom_message_handler(self, custom_handler: CustomHandler) -> None:
        """Test that custom message handler is called."""
        event = {"type": "message", "text": "Hello world"}
        await custom_handler.handle_event(event)

        assert len(custom_handler.events_received) == 1
        assert custom_handler.events_received[0] == event
        assert event["processed_by"] == "on_message"

    @pytest.mark.asyncio
    async def test_custom_reaction_handler(self, custom_handler: CustomHandler) -> None:
        """Test that custom reaction handler is called."""
        event = {"type": "reaction_added", "reaction": "thumbsup"}
        await custom_handler.handle_event(event)

        assert len(custom_handler.events_received) == 1
        assert custom_handler.events_received[0] == event
        assert event["processed_by"] == "on_reaction_added"

    @pytest.mark.asyncio
    async def test_unknown_event_handler(self, custom_handler: CustomHandler) -> None:
        """Test that custom unknown handler is called for unimplemented events."""
        event = {"type": "not_implemented_type"}
        await custom_handler.handle_event(event)

        assert len(custom_handler.events_received) == 1
        assert custom_handler.events_received[0] == event
        assert event["processed_by"] == "on_unknown"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "event_data,expected_handler",
        [
            ({"type": "message"}, "on_message"),
            ({"type": "reaction_added"}, "on_reaction_added"),
            ({"type": "app_home_opened"}, "on_app_home_opened"),
            ({"type": "nonexistent_type"}, "on_unknown"),
        ],
    )
    async def test_multiple_event_types(
        self, custom_handler: CustomHandler, event_data: Dict[str, Any], expected_handler: str
    ) -> None:
        """Test handling of multiple event types using parametrize."""
        await custom_handler.handle_event(event_data)
        assert event_data["processed_by"] == expected_handler


class ExtensiveTestHandler(BaseSlackEventHandler):
    """Handler implementation for testing many of the newly added event types."""

    def __init__(self) -> None:
        super().__init__()
        self.handled_events: Dict[str, Dict[str, Any]] = {}

    async def on_file_created(self, event: Dict[str, Any]) -> None:
        self.handled_events["file_created"] = event

    async def on_workflow_step_execute(self, event: Dict[str, Any]) -> None:
        self.handled_events["workflow_step_execute"] = event

    async def on_user_huddle_changed(self, event: Dict[str, Any]) -> None:
        self.handled_events["user_huddle_changed"] = event

    async def on_channel_rename(self, event: Dict[str, Any]) -> None:
        self.handled_events["channel_rename"] = event

    async def on_team_join(self, event: Dict[str, Any]) -> None:
        self.handled_events["team_join"] = event


class TestExtensiveHandler:
    """Test suite for newly added event type handlers."""

    @pytest.fixture
    def handler(self) -> ExtensiveTestHandler:
        """Fixture providing an ExtensiveTestHandler instance."""
        return ExtensiveTestHandler()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "event_type", ["file_created", "workflow_step_execute", "user_huddle_changed", "channel_rename", "team_join"]
    )
    async def test_new_event_types(self, handler: ExtensiveTestHandler, event_type: str) -> None:
        """Test that newly added event handlers are called correctly."""
        event = {"type": event_type, "data": f"Test data for {event_type}"}
        await handler.handle_event(event)

        assert event_type in handler.handled_events
        assert handler.handled_events[event_type]["data"] == f"Test data for {event_type}"
