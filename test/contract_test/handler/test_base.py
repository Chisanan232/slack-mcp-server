"""
PyTest-based contract tests for the BaseSlackEventHandler class.

This module verifies that:
1. Each Slack event type has a corresponding handler method in BaseSlackEventHandler
2. The event routing logic correctly maps events to their handlers
3. Type annotations follow PEP 484/585 standards
"""

import inspect
from typing import Any, Dict, List, Tuple, cast, get_type_hints, Optional, Type
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from slack_mcp.events import SlackEvent
from slack_mcp.handler.base import BaseSlackEventHandler


class TestBaseSlackEventHandler:
    """Test suite for BaseSlackEventHandler contract tests."""

    def test_all_slack_events_have_handlers(self) -> None:
        """Verify that each SlackEvent enum value has a corresponding handler method."""
        base_handler = BaseSlackEventHandler()
        
        # Get all method names from the BaseSlackEventHandler
        handler_methods = [
            method for method in dir(base_handler) 
            if callable(getattr(base_handler, method)) and method.startswith("on_")
        ]
        
        # Check that each SlackEvent has a corresponding handler
        missing_handlers: List[str] = []
        
        for event in SlackEvent:
            # Convert the enum's name to the handler method format (replacing dots with double underscores)
            event_type_parts = event.value.split(".")
            
            if len(event_type_parts) == 1:
                # Simple event type (e.g., "message")
                expected_handler = f"on_{event_type_parts[0]}"
                if expected_handler not in handler_methods:
                    missing_handlers.append(f"{event.value} -> {expected_handler}")
            else:
                # Event type with subtype (e.g., "message.channels")
                event_type = event_type_parts[0]
                subtype = event_type_parts[1]
                expected_handler = f"on_{event_type}__{subtype}"
                if expected_handler not in handler_methods:
                    missing_handlers.append(f"{event.value} -> {expected_handler}")
                
                # Also check for the main type handler
                main_handler = f"on_{event_type}"
                if main_handler not in handler_methods:
                    missing_handlers.append(f"{event_type} -> {main_handler}")
        
        # Assert all event types have handlers
        assert not missing_handlers, f"Missing handlers for events: {missing_handlers}"

    def test_handler_method_signatures(self) -> None:
        """Verify all handler methods have correct signatures and type annotations."""
        handler_cls = BaseSlackEventHandler
        
        # Get all handler methods from the class (not instance)
        handler_methods = [
            method for method in dir(handler_cls) 
            if callable(getattr(handler_cls, method)) and method.startswith("on_")
        ]
        
        for method_name in handler_methods:
            method = getattr(handler_cls, method_name)
            
            # Check method is async
            assert inspect.iscoroutinefunction(method), f"Handler {method_name} is not async"
            
            # Check signature has event parameter
            sig = inspect.signature(method)
            params = list(sig.parameters.values())
            assert len(params) == 2, f"Handler {method_name} should have exactly 2 parameters (self and event), got {params}"
            assert params[0].name == "self", f"First parameter of {method_name} should be 'self'"
            assert params[1].name == "event", f"Second parameter of {method_name} should be 'event'"
            
            # Check type annotations
            type_hints = get_type_hints(method)
            assert "event" in type_hints, f"Handler {method_name} is missing type hint for 'event'"
            assert type_hints["event"] == Dict[str, Any], f"Handler {method_name} 'event' parameter should be Dict[str, Any]"
            assert "return" in type_hints, f"Handler {method_name} is missing return type hint"
            
            # In Python's type system, None return annotation is represented by NoneType
            none_type: Type = type(None)
            assert type_hints["return"] == none_type, f"Handler {method_name} should return None, got {type_hints['return']}"

    @pytest.mark.asyncio
    async def test_event_routing(self) -> None:
        """Test that events are routed to the correct handler methods."""
        # Create a subclass that tracks called methods
        class TrackingHandler(BaseSlackEventHandler):
            def __init__(self) -> None:
                super().__init__()
                self.called_methods: List[str] = []
            
            async def on_message(self, event: Dict[str, Any]) -> None:
                self.called_methods.append("on_message")
            
            async def on_message__channels(self, event: Dict[str, Any]) -> None:
                self.called_methods.append("on_message__channels")
                
            async def on_reaction_added(self, event: Dict[str, Any]) -> None:
                self.called_methods.append("on_reaction_added")
                
            async def on_unknown(self, event: Dict[str, Any]) -> None:
                self.called_methods.append("on_unknown")
        
        handler = TrackingHandler()
        
        # Test routing to type + subtype handler
        await handler.handle_event({"type": "message", "subtype": "channels"})
        assert handler.called_methods == ["on_message__channels"]
        handler.called_methods.clear()
        
        # Test routing to type handler when subtype doesn't have a specific handler
        await handler.handle_event({"type": "message", "subtype": "nonexistent"})
        assert handler.called_methods == ["on_message"]
        handler.called_methods.clear()
        
        # Test routing to simple type handler
        await handler.handle_event({"type": "reaction_added"})
        assert handler.called_methods == ["on_reaction_added"]
        handler.called_methods.clear()
        
        # Test routing to unknown handler
        await handler.handle_event({"type": "nonexistent_event"})
        assert handler.called_methods == ["on_unknown"]

    @pytest.mark.asyncio
    async def test_resolve_method_logic(self) -> None:
        """Test the _resolve method logic for finding the correct handler."""
        handler = BaseSlackEventHandler()
        
        # Create spy methods to test routing
        with patch.object(handler, 'on_message', new_callable=AsyncMock) as mock_message, \
             patch.object(handler, 'on_message__channels', new_callable=AsyncMock) as mock_message_channels, \
             patch.object(handler, 'on_unknown', new_callable=AsyncMock) as mock_unknown:
            
            # Test type + subtype resolution
            event1 = {"type": "message", "subtype": "channels"}
            resolved1 = handler._resolve(event1)
            await resolved1(event1)
            mock_message_channels.assert_called_once_with(event1)
            
            # Test type-only resolution
            event2 = {"type": "message"}
            resolved2 = handler._resolve(event2)
            await resolved2(event2)
            mock_message.assert_called_once_with(event2)
            
            # Test unknown type resolution
            event3 = {"type": "nonexistent"}
            resolved3 = handler._resolve(event3)
            await resolved3(event3)
            mock_unknown.assert_called_once_with(event3)
            
            # Test missing type resolution
            event4 = {}
            resolved4 = handler._resolve(event4)
            await resolved4(event4)
            mock_unknown.assert_called_with(event4)

    @pytest.mark.parametrize("event_data, expected_handler", [
        ({"type": "message"}, "on_message"),
        ({"type": "message", "subtype": "channels"}, "on_message__channels"),
        ({"type": "message", "subtype": "nonexistent"}, "on_message"),
        ({"type": "reaction_added"}, "on_reaction_added"),
        ({"type": "nonexistent_event"}, "on_unknown"),
        ({}, "on_unknown"),
    ])
    @pytest.mark.asyncio
    async def test_parametrized_event_routing(
        self, event_data: Dict[str, Any], expected_handler: str
    ) -> None:
        """Test event routing with parameterized test cases."""
        handler = BaseSlackEventHandler()
        
        # Create mocks for all the methods we might call
        method_mocks = {}
        for method_name in ["on_message", "on_message__channels", "on_reaction_added", "on_unknown"]:
            mock = AsyncMock()
            method_mocks[method_name] = mock
            setattr(handler, method_name, mock)
        
        # Handle the event
        await handler.handle_event(event_data)
        
        # Check that only the expected handler was called
        for name, mock in method_mocks.items():
            if name == expected_handler:
                mock.assert_called_once_with(event_data)
            else:
                mock.assert_not_called()

    def test_comprehensive_handler_coverage(self) -> None:
        """Test that BaseSlackEventHandler provides handlers for all known Slack events."""
        # Get all handler methods from BaseSlackEventHandler
        handler = BaseSlackEventHandler()
        handler_methods = {
            method for method in dir(handler) 
            if callable(getattr(handler, method)) and method.startswith("on_")
        }
        
        # Remove special handlers like on_unknown
        special_handlers = {"on_unknown"}
        handler_methods -= special_handlers
        
        # Check for unexpected handler methods without corresponding SlackEvent enum
        unexpected_handlers: List[str] = []
        for method in handler_methods:
            if method.startswith("on_"):
                if "__" in method:
                    # This is a type + subtype handler
                    parts = method[3:].split("__")
                    event_name = f"{parts[0]}.{parts[1]}"
                else:
                    # This is a type-only handler
                    event_name = method[3:]
                
                # Try to find a matching SlackEvent
                try:
                    SlackEvent.from_type_subtype(event_name)
                except ValueError:
                    unexpected_handlers.append(f"{method} -> {event_name}")
        
        # Assert no unexpected handlers
        assert not unexpected_handlers, f"Unexpected handlers without SlackEvent enums: {unexpected_handlers}"
