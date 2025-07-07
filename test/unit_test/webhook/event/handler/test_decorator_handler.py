"""
Tests for the DecoratorHandler class.

This module tests the DecoratorHandler functionality including:
- Attribute-style registration (@handler.reaction_added)
- Enum-style registration (@handler(SlackEvent.REACTION_ADDED))
- Event handling and routing
"""

import asyncio
from typing import Any, Dict, List

import pytest

from slack_mcp.events import SlackEvent
from slack_mcp.webhook.event.handler import DecoratorHandler


class TestDecoratorHandler:
    """Test suite for DecoratorHandler."""

    def setup_method(self) -> None:
        """Set up a fresh handler for each test."""
        self.handler = DecoratorHandler()
        self.handled_events: Dict[str, List[Dict[str, Any]]] = {
            "message": [],
            "reaction_added": [],
            "app_mention": [],
            "wildcard": [],
        }

    def test_attribute_style_registration(self) -> None:
        """Test attribute-style registration (@handler.reaction_added)."""
        handler = self.handler

        @handler.reaction_added
        def handle_reaction(event: Dict[str, Any]) -> None:
            self.handled_events["reaction_added"].append(event)

        # Verify the handler was registered
        handlers = handler.get_handlers()
        assert "reaction_added" in handlers
        assert len(handlers["reaction_added"]) == 1

    def test_enum_style_registration(self) -> None:
        """Test enum-style registration (@handler(SlackEvent.REACTION_ADDED))."""
        handler = self.handler

        @handler(SlackEvent.REACTION_ADDED)
        def handle_reaction(event: Dict[str, Any]) -> None:
            self.handled_events["reaction_added"].append(event)

        # Verify the handler was registered
        handlers = handler.get_handlers()
        assert "reaction_added" in handlers
        assert len(handlers["reaction_added"]) == 1

    def test_wildcard_registration(self) -> None:
        """Test wildcard registration (@handler)."""
        handler = self.handler

        @handler
        def handle_all(event: Dict[str, Any]) -> None:
            self.handled_events["wildcard"].append(event)

        # Verify the handler was registered
        handlers = handler.get_handlers()
        assert "*" in handlers
        assert len(handlers["*"]) == 1

    @pytest.mark.asyncio
    async def test_event_handling(self) -> None:
        """Test that events are routed to the correct handlers."""
        handler = self.handler

        # Register handlers using both styles
        @handler.message
        def handle_message(event: Dict[str, Any]) -> None:
            self.handled_events["message"].append(event)

        @handler(SlackEvent.REACTION_ADDED)
        def handle_reaction(event: Dict[str, Any]) -> None:
            self.handled_events["reaction_added"].append(event)

        @handler
        def handle_all(event: Dict[str, Any]) -> None:
            self.handled_events["wildcard"].append(event)

        # Handle a message event
        message_event = {"type": "message", "text": "Hello"}
        await handler.handle_event(message_event)

        # Handle a reaction_added event
        reaction_event = {"type": "reaction_added", "reaction": "thumbsup"}
        await handler.handle_event(reaction_event)

        # Verify the events were handled by the correct handlers
        assert len(self.handled_events["message"]) == 1
        assert self.handled_events["message"][0] == message_event

        assert len(self.handled_events["reaction_added"]) == 1
        assert self.handled_events["reaction_added"][0] == reaction_event

        # Wildcard handler should have received both events
        assert len(self.handled_events["wildcard"]) == 2

    @pytest.mark.asyncio
    async def test_async_handlers(self) -> None:
        """Test that async handlers are properly awaited."""
        handler = self.handler

        # Register an async handler
        @handler.message
        async def handle_message_async(event: Dict[str, Any]) -> None:
            # Simulate some async work
            await asyncio.sleep(0.01)
            self.handled_events["message"].append(event)

        # Handle a message event
        message_event = {"type": "message", "text": "Hello"}
        await handler.handle_event(message_event)

        # Verify the event was handled
        assert len(self.handled_events["message"]) == 1
        assert self.handled_events["message"][0] == message_event

    def test_clear_handlers(self) -> None:
        """Test that clear_handlers removes all registered handlers."""
        handler = self.handler

        @handler.message
        def handle_message(event: Dict[str, Any]) -> None:
            pass

        @handler.reaction_added
        def handle_reaction(event: Dict[str, Any]) -> None:
            pass

        # Verify handlers were registered
        handlers = handler.get_handlers()
        assert "message" in handlers
        assert "reaction_added" in handlers

        # Clear handlers
        handler.clear_handlers()

        # Verify handlers were cleared
        handlers = handler.get_handlers()
        assert not handlers

    @pytest.mark.asyncio
    async def test_subtype_handling(self) -> None:
        """Test handling of events with subtypes."""
        handler = self.handler

        # Track calls to the handler
        calls = []

        # Register a handler for message.channels
        @handler(SlackEvent.MESSAGE_CHANNELS)
        def handle_channel_message(event: Dict[str, Any]) -> None:
            calls.append(("channel_message", event))

        # Register a handler for general messages
        @handler.message
        def handle_message(event: Dict[str, Any]) -> None:
            calls.append(("message", event))

        # Handle a message with subtype
        channel_message = {"type": "message", "subtype": "channels", "text": "Hello"}
        await handler.handle_event(channel_message)

        # Verify both handlers were called
        assert len(calls) == 2
        assert ("message", channel_message) in calls
        assert ("channel_message", channel_message) in calls
