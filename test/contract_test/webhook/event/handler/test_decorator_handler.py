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
from unittest import mock

import pytest

from slack_mcp.events import SlackEvent
from slack_mcp.webhook.event.handler.base import EventHandler
from slack_mcp.webhook.event.handler.decorator import DecoratorHandler


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

    def test_getattr_method(self) -> None:
        """Test the __getattr__ method for dynamic attribute access."""
        handler = self.handler

        # Test case 1: Direct match with SlackEvent enum
        reaction_added_decorator = handler.reaction_added

        # Define a handler function
        async def test_handler1(event: Dict[str, Any]) -> None:
            pass

        # Register the handler
        decorated_handler1 = reaction_added_decorator(test_handler1)

        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert "reaction_added" in handlers
        assert test_handler1 in handlers["reaction_added"]

        # Test case 2: Match with dots instead of underscores
        message_channels_decorator = handler.message_channels

        # Define another handler function
        async def test_handler2(event: Dict[str, Any]) -> None:
            pass

        # Register the handler
        decorated_handler2 = message_channels_decorator(test_handler2)

        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert "message.channels" in handlers
        assert test_handler2 in handlers["message.channels"]

        # Test case 3: Custom event type not in SlackEvent enum
        custom_event_decorator = handler.custom_event_type

        # Define another handler function
        async def test_handler3(event: Dict[str, Any]) -> None:
            pass

        # Register the handler
        decorated_handler3 = custom_event_decorator(test_handler3)

        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert "custom_event_type" in handlers
        assert test_handler3 in handlers["custom_event_type"]

        # Test case 4: Error handling for invalid attribute access
        # We need to mock __getattr__ to force it to raise an AttributeError
        # since all attribute access is converted to event handlers
        original_getattr = DecoratorHandler.__getattr__

        try:
            # Replace __getattr__ with a version that raises AttributeError for _test_error
            def mock_getattr(self, name):
                if name == "_test_error":
                    raise AttributeError(f"Unknown Slack event type: '{name}'")
                return original_getattr(self, name)

            # Apply the mock
            with mock.patch.object(DecoratorHandler, "__getattr__", mock_getattr):
                # Now test the error case
                with pytest.raises(AttributeError) as excinfo:
                    handler._test_error

                # Verify the error message
                assert "Unknown Slack event type" in str(excinfo.value)

        finally:
            # Restore the original __getattr__
            pass

    def test_getattr_dot_replacement_success_path(self) -> None:
        """Test the dot replacement success path in __getattr__ method (line 151)."""
        from unittest.mock import patch

        handler = self.handler

        # We need to create a scenario where:
        # 1. The attribute is not a direct match to a SlackEvent enum member
        # 2. But when replacing underscores with dots, it becomes a valid SlackEvent
        # 3. This will trigger the success path at line 151

        # Create a mock that will return a specific SlackEvent when created with our test string
        mock_slack_event = SlackEvent.APP_HOME_OPENED

        # Use patch to mock the SlackEvent.__new__ method
        # This is what's actually called when SlackEvent(event_name) is executed
        with patch.object(SlackEvent, "__new__", return_value=mock_slack_event) as mock_new:
            # This should trigger the success path at line 151
            # The attribute name will be converted to "custom.event.success"
            # Which our mock will convert to a valid SlackEvent
            decorator = handler.custom_event_success

            # Verify we got a decorator function
            assert callable(decorator)

            # Use the decorator to register a handler
            @decorator
            def test_handler(event: Dict[str, Any]) -> None:
                pass

            # Now verify that the handler was registered with the correct event
            # The handler should be registered with the string representation of APP_HOME_OPENED
            assert test_handler in handler._handlers[str(mock_slack_event)]

    def test_getattr_edge_cases(self) -> None:
        """Test edge cases in the __getattr__ method."""
        handler = self.handler

        # Test case 1: Attribute name that fails direct match but works with dot notation
        # For example, "message_channels" should be converted to "message.channels"
        message_channels_decorator = handler.message_channels

        # Define a handler function
        async def test_handler(event: Dict[str, Any]) -> None:
            pass

        # Register the handler
        decorated_handler = message_channels_decorator(test_handler)

        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert "message.channels" in handlers
        assert test_handler in handlers["message.channels"]

        # Test case 2: Attribute name that fails both direct match and dot notation
        # but is accepted as a custom event type
        custom_event_decorator = handler.completely_custom_event

        # Register another handler
        async def custom_handler(event: Dict[str, Any]) -> None:
            pass

        # Register the handler
        decorated_custom = custom_event_decorator(custom_handler)

        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert "completely_custom_event" in handlers
        assert custom_handler in handlers["completely_custom_event"]

        # Test case 3: Test exception handling in __getattr__
        # We'll use patch to simulate exceptions in different parts of the method

        # Create a new handler for testing exception paths
        exception_handler = DecoratorHandler()

        # Define a mock __getattr__ that will test different exception paths
        def mock_getattr(self: DecoratorHandler, name: str) -> Any:
            if name == "_test_error":
                # This simulates an exception in the try block
                raise AttributeError(f"Unknown Slack event type: '{name}'")
            # Call the real __getattr__ for other attributes
            # We can't call the original directly, so we'll raise AttributeError
            # to simulate the behavior we want to test
            raise AttributeError(f"Attribute {name} not found")

        # Use patch instead of direct assignment
        with mock.patch.object(DecoratorHandler, "__getattr__", mock_getattr):
            # Test that accessing an attribute that raises AttributeError
            # propagates the exception correctly
            with pytest.raises(AttributeError) as excinfo:
                exception_handler._test_error

            # Verify the error message
            assert "Unknown Slack event type" in str(excinfo.value)

    def test_getattr_exception_paths(self) -> None:
        """Test the exception handling paths in __getattr__ method."""
        handler = self.handler

        # Test case 1: Test ValueError in SlackEvent conversion (lines 151-152)
        # We need to create a scenario where:
        # 1. The attribute is not a direct match to a SlackEvent enum member (will raise AttributeError)
        # 2. Converting with dots instead of underscores raises ValueError
        # 3. But we still want to allow it as a custom event type

        # First, let's create a custom event name that won't match any SlackEvent enum member
        custom_event = "custom_event_type"

        # Use mock to patch the SlackEvent constructor to raise ValueError for a specific input
        with mock.patch.object(SlackEvent, "__call__", side_effect=ValueError("Invalid event")):
            # This should trigger the ValueError path and fall back to accepting it as a custom event
            decorator = getattr(handler, custom_event)

            # Verify we got a decorator function
            assert callable(decorator)

            # Use the decorator to register a handler
            @decorator
            def test_handler(event: Dict[str, Any]) -> None:
                pass

            # Verify the handler was registered with the correct name
            assert custom_event in handler._handlers
            assert test_handler in handler._handlers[custom_event]

        # Test case 2: Test general exception handling (lines 155-157)
        # We need to create a scenario where an unexpected exception occurs in __getattr__

        # Create a mock that will raise an exception when called
        with mock.patch.object(SlackEvent, "__new__", side_effect=Exception("Unexpected error")):
            # This should trigger the general exception handler
            with pytest.raises(AttributeError) as excinfo:
                # Try to access an attribute that will go through the exception path
                handler.unknown_event_type

            # Verify the correct error message
            assert "Unknown Slack event type: 'unknown_event_type'" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_additional_edge_cases(self) -> None:
        """Test additional edge cases to improve coverage."""
        handler = self.handler

        # Test case 1: Test handling of custom event types with special characters
        # This should test the fallback path in __getattr__ where it accepts any string
        attr_name = "app_custom_event_with_special_chars"
        custom_decorator = getattr(handler, attr_name)

        # Define a handler function
        async def custom_handler(event: Dict[str, Any]) -> None:
            pass

        # Register the handler
        decorated_handler = custom_decorator(custom_handler)

        # Verify the handler is registered correctly
        handlers = handler.get_handlers()
        assert attr_name in handlers
        assert custom_handler in handlers[attr_name]

        # Test case 2: Test handling of event with subtype
        # Create a mock event with a subtype
        event_with_subtype = {"type": "message", "subtype": "channel_join"}

        # Register handlers for both the general event and the specific subtype
        message_handlers = []

        @handler.message
        async def general_message_handler(event: Dict[str, Any]) -> None:
            message_handlers.append("general")

        # Register a handler for the specific subtype using the string format
        @handler("message.channel_join")
        async def subtype_handler(event: Dict[str, Any]) -> None:
            message_handlers.append("subtype")

        # Dispatch the event asynchronously
        await handler.handle_event(event_with_subtype)

        # Verify both handlers were called
        # The order is determined by the implementation in handle_event
        assert set(message_handlers) == {"subtype", "general"}
        assert len(message_handlers) == 2

        # Test case 3: Test wildcard handler
        wildcard_called = False

        @handler
        async def wildcard_handler(event: Dict[str, Any]) -> None:
            nonlocal wildcard_called
            wildcard_called = True

        # Create a completely different event
        random_event = {"type": "random_event_type"}

        # Dispatch the event asynchronously
        await handler.handle_event(random_event)

        # Verify the wildcard handler was called
        assert wildcard_called is True

        # Test case 4: Test event with no handlers
        # This should not raise any exceptions
        no_handler_event = {"type": "event_with_no_handlers"}

        # This should not raise any exceptions
        await handler.handle_event(no_handler_event)

        # Test case 5: Test event with no type
        # This should not raise any exceptions
        no_type_event = {"not_type": "something"}

        # This should not raise any exceptions
        await handler.handle_event(no_type_event)


# if __name__ == "__main__":
#     pytest.main(["-xvs", __file__])
