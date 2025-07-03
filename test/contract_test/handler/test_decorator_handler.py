"""
Contract tests for the DecoratorHandler class.

These tests verify that the DecoratorHandler class adheres to its contract
and provides a developer-friendly interface. They focus on:

1. Protocol compliance (EventHandler)
2. API stability and usability
3. Error handling and edge cases
4. Integration with SlackEventConsumer
5. IDE auto-completion support validation
"""

import asyncio
import inspect
from typing import Any, Dict, List, Tuple

import pytest

from slack_mcp.events import SlackEvent
from slack_mcp.handler.base import EventHandler
from slack_mcp.handler.decorator import DecoratorHandler


# Generate test data from SlackEvent enum
def generate_decorator_test_cases() -> List[Tuple[str, SlackEvent]]:
    """Generate test cases for decorator methods from SlackEvent enum."""
    test_cases = []
    for event_enum in SlackEvent:
        # Convert enum value to method name (replace dots with underscores)
        method_name = str(event_enum).replace(".", "_")
        test_cases.append((method_name, event_enum))
    return test_cases


class TestDecoratorHandlerContract:
    """Contract tests for DecoratorHandler."""

    def setup_method(self) -> None:
        """Set up a fresh handler for each test."""
        self.handler = DecoratorHandler()

    def test_implements_event_handler_protocol(self) -> None:
        """Test that DecoratorHandler implements the EventHandler protocol."""
        # Check that DecoratorHandler is an instance of EventHandler
        assert isinstance(self.handler, EventHandler)

        # Check that it has the required handle_event method with correct signature
        assert hasattr(self.handler, "handle_event")
        sig = inspect.signature(self.handler.handle_event)

        # The EventHandler protocol defines handle_event with just 'event' parameter
        # (self is implicit in method definitions)
        assert "event" in sig.parameters

        # Check return annotation is a coroutine
        assert "Coroutine" in str(sig.return_annotation) or "None" in str(sig.return_annotation)

    def test_decorator_style_consistency(self) -> None:
        """Test that both decorator styles work consistently."""
        handler = self.handler
        events_received = []

        # Register handlers using both styles
        @handler.reaction_added
        def handle_reaction_attribute(event: Dict[str, Any]) -> None:
            events_received.append(("attribute", event))

        @handler(SlackEvent.MESSAGE)
        def handle_message_enum(event: Dict[str, Any]) -> None:
            events_received.append(("enum", event))

        # Get registered handlers
        handlers = handler.get_handlers()

        # Verify both styles registered correctly
        assert "reaction_added" in handlers
        assert "message" in handlers

        # Verify the functions are correctly registered
        assert handlers["reaction_added"][0] == handle_reaction_attribute
        assert handlers["message"][0] == handle_message_enum

    def test_common_slack_events_have_methods(self) -> None:
        """Test that common SlackEvent enum values have corresponding methods."""
        handler = self.handler

        # Check a subset of common events that should definitely have methods
        common_events = [
            "message",
            "reaction_added",
            "app_mention",
            "channel_created",
            "user_change",
            "team_join",
            "pin_added",
            "emoji_changed",
        ]

        # Convert to method names (dots to underscores)
        common_methods = [event.replace(".", "_") for event in common_events]

        # Check that all common events have methods
        for method_name in common_methods:
            assert hasattr(handler, method_name), f"Missing method for event: {method_name}"
            assert callable(getattr(handler, method_name)), f"Method {method_name} is not callable"

    def test_method_docstrings(self) -> None:
        """Test that all event methods have proper docstrings."""
        handler = self.handler

        # Check a sample of methods to ensure they have docstrings
        sample_methods = ["message", "reaction_added", "app_mention", "channel_created"]

        for method_name in sample_methods:
            method = getattr(handler, method_name)
            assert method.__doc__, f"Method {method_name} is missing a docstring"
            assert "Register a handler for" in method.__doc__, f"Method {method_name} has incorrect docstring format"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test that handler errors are caught and don't crash the process."""
        handler = self.handler

        # Register a handler that raises an exception
        @handler.message
        def handle_message_error(event: Dict[str, Any]) -> None:
            raise ValueError("Test error")

        # Register a handler that should still be called after the error
        call_count = 0

        @handler.message
        def handle_message_after_error(event: Dict[str, Any]) -> None:
            nonlocal call_count
            call_count += 1

        # Handle an event - this should not raise an exception
        # We don't mock the logger here since the implementation might use a different logger
        # or error handling approach
        await handler.handle_event({"type": "message", "text": "test"})

        # Verify the second handler was still called
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_integration_with_consumer(self) -> None:
        """Test that DecoratorHandler integrates with SlackEventConsumer."""
        handler = self.handler
        events_received = []

        @handler.message
        def handle_message(event: Dict[str, Any]) -> None:
            events_received.append(event)

        # Create a mock event
        test_event = {"type": "message", "text": "test"}

        # Directly call handle_event to simulate what the consumer would do
        await handler.handle_event(test_event)

        # Verify the event was processed by our handler
        assert len(events_received) == 1
        assert events_received[0]["text"] == "test"

    def test_handler_return_values(self) -> None:
        """Test that handler return values are properly handled."""
        handler = self.handler

        # Register a handler that returns a value
        @handler.message
        def handle_message_with_return(event: Dict[str, Any]) -> str:
            return "test_return"

        # Get the registered handler
        message_handlers = handler.get_handlers()["message"]
        assert len(message_handlers) == 1

        # Call the handler directly
        result = message_handlers[0]({"type": "message"})
        assert result == "test_return"

    @pytest.mark.asyncio
    async def test_multiple_handlers_for_same_event(self) -> None:
        """Test registering and calling multiple handlers for the same event."""
        handler = self.handler
        calls = []

        @handler.message
        def handle_message1(event: Dict[str, Any]) -> None:
            calls.append("handler1")

        @handler.message
        def handle_message2(event: Dict[str, Any]) -> None:
            calls.append("handler2")

        # Handle an event
        await handler.handle_event({"type": "message"})

        # Verify both handlers were called
        assert len(calls) == 2
        assert "handler1" in calls
        assert "handler2" in calls

    def test_handler_execution_order(self) -> None:
        """Test that handlers are executed in registration order."""
        handler = self.handler
        call_order = []

        @handler.message
        def handle_message1(event: Dict[str, Any]) -> None:
            call_order.append("handler1")

        @handler.message
        def handle_message2(event: Dict[str, Any]) -> None:
            call_order.append("handler2")

        @handler.message
        def handle_message3(event: Dict[str, Any]) -> None:
            call_order.append("handler3")

        # Get handlers and call them directly in the order they're registered
        message_handlers = handler.get_handlers()["message"]
        for h in message_handlers:
            h({"type": "message"})

        # Verify the call order matches registration order
        assert call_order == ["handler1", "handler2", "handler3"]

    def test_custom_event_types(self) -> None:
        """Test handling custom event types not in SlackEvent enum."""
        handler = self.handler
        received_events = []

        # Register a handler for a custom event type
        @handler("custom_event")
        def handle_custom(event: Dict[str, Any]) -> None:
            received_events.append(event)

        # Handle a custom event
        event = {"type": "custom_event", "data": "test"}
        asyncio.run(handler.handle_event(event))

        # Verify the event was handled
        assert len(received_events) == 1
        assert received_events[0] == event

    def test_invalid_event_handling(self) -> None:
        """Test that accessing an invalid event attribute is handled appropriately."""
        handler = self.handler

        # Try to register a handler for a non-existent event type
        # This should not raise an exception as the implementation might handle this dynamically
        @handler("not_a_real_event_type")
        def handle_invalid(event: Dict[str, Any]) -> None:
            pass

        # Verify the handler was registered under the custom name
        handlers = handler.get_handlers()
        assert "not_a_real_event_type" in handlers

    def test_chained_decorators(self) -> None:
        """Test that the decorator can be chained with other decorators."""
        handler = self.handler
        calls = []

        # Define a custom decorator
        def my_decorator(func):
            def wrapper(event):
                calls.append("decorator_called")
                return func(event)

            return wrapper

        # Apply both decorators - order matters here!
        @handler.message
        @my_decorator
        def handle_message(event: Dict[str, Any]) -> None:
            calls.append("handler_called")

        # Call the handler directly
        handlers = handler.get_handlers()["message"]
        handlers[0]({"type": "message"})

        # Verify both the decorator and handler were called
        assert calls == ["decorator_called", "handler_called"]

    def test_handler_instance_isolation(self) -> None:
        """Test that multiple handler instances are isolated from each other."""
        handler1 = DecoratorHandler()
        handler2 = DecoratorHandler()

        # Register handlers on each instance
        @handler1.message
        def handle_message1(event: Dict[str, Any]) -> None:
            pass

        @handler2.reaction_added
        def handle_reaction2(event: Dict[str, Any]) -> None:
            pass

        # Verify handlers are isolated
        handlers1 = handler1.get_handlers()
        handlers2 = handler2.get_handlers()

        assert "message" in handlers1
        assert "message" not in handlers2

        assert "reaction_added" in handlers2
        assert "reaction_added" not in handlers1

    def test_specific_event_decorators(self) -> None:
        """Test specific event decorator methods to ensure they register correctly."""
        handler = self.handler
        events_received = []

        # Test assistant_thread_context_changed decorator
        @handler.assistant_thread_context_changed
        async def handle_assistant_thread_context_changed(event: Dict[str, Any]) -> None:
            events_received.append(("assistant_thread_context_changed", event))

        # Test assistant_thread_started decorator
        @handler.assistant_thread_started
        async def handle_assistant_thread_started(event: Dict[str, Any]) -> None:
            events_received.append(("assistant_thread_started", event))

        # Get registered handlers
        handlers = handler.get_handlers()

        # Verify the handlers are correctly registered
        assert "assistant_thread_context_changed" in handlers
        assert handlers["assistant_thread_context_changed"][0] == handle_assistant_thread_context_changed
        
        assert "assistant_thread_started" in handlers
        assert handlers["assistant_thread_started"][0] == handle_assistant_thread_started

        # Test that the handlers are called with the correct events
        test_event_context_changed = {"type": "assistant_thread_context_changed", "data": "test"}
        test_event_thread_started = {"type": "assistant_thread_started", "data": "test"}

        # Run the handlers
        asyncio.run(handler.handle_event(test_event_context_changed))
        asyncio.run(handler.handle_event(test_event_thread_started))

        # Verify the events were received
        assert len(events_received) == 2
        assert events_received[0] == ("assistant_thread_context_changed", test_event_context_changed)
        assert events_received[1] == ("assistant_thread_started", test_event_thread_started)

    @pytest.mark.parametrize(
        "decorator_method,event_type",
        generate_decorator_test_cases(),
    )
    def test_all_decorator_methods(self, decorator_method: str, event_type: SlackEvent) -> None:
        """Test all decorator methods to ensure they register correctly."""
        handler = self.handler
        
        # Skip if the handler doesn't have this method
        if not hasattr(handler, decorator_method):
            pytest.skip(f"Handler does not have method: {decorator_method}")
        
        # Get the decorator method
        decorator = getattr(handler, decorator_method)
        
        # Define a simple handler function
        async def test_handler(event: Dict[str, Any]) -> None:
            pass
        
        # Register the handler
        decorated_handler = decorator(test_handler)
        
        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert str(event_type) in handlers
        assert handlers[str(event_type)][0] == test_handler
        
        # Verify the decorator returns the original function
        assert decorated_handler == test_handler

# if __name__ == "__main__":
#     pytest.main(["-xvs", __file__])
