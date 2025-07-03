"""
PyTest-based tests for the SlackEventConsumer class.

This module tests the SlackEventConsumer functionality including:
- Integration with both OO-style handlers and decorator-based handlers
- Event dispatch to appropriate handlers
- Error handling and graceful shutdown
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Dict, Generator, List, Optional, cast
from unittest.mock import patch

import pytest

from slack_mcp.backends.protocol import QueueBackend
from slack_mcp.consumer import SlackEventConsumer
from slack_mcp.dispatcher import dispatch_event, slack_event
from slack_mcp.events import SlackEvent
from slack_mcp.handler.base import BaseSlackEventHandler


class MockQueueBackend(QueueBackend):
    """Mock implementation of QueueBackend for testing."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self.published_events: List[Dict[str, Any]] = []

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Mock implementation of publish method."""
        self.published_events.append(payload)

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Mock implementation of consume method yielding events."""
        for event in self.events:
            yield event
        # Signal end of events
        await asyncio.sleep(0.1)

    @classmethod
    def from_env(cls) -> QueueBackend:
        """Mock implementation of from_env classmethod."""
        return cls()


class TestHandler(BaseSlackEventHandler):
    """Test implementation of BaseSlackEventHandler."""

    def __init__(self) -> None:
        super().__init__()
        self.handled_events: Dict[str, List[Dict[str, Any]]] = {
            "message": [],
            "reaction_added": [],
            "app_mention": [],
            "unknown": [],
        }

    async def on_message(self, event: Dict[str, Any]) -> None:
        """Handle message events."""
        self.handled_events["message"].append(event)

    async def on_reaction_added(self, event: Dict[str, Any]) -> None:
        """Handle reaction_added events."""
        self.handled_events["reaction_added"].append(event)

    async def on_app_mention(self, event: Dict[str, Any]) -> None:
        """Handle app_mention events."""
        self.handled_events["app_mention"].append(event)

    async def on_unknown(self, event: Dict[str, Any]) -> None:
        """Handle unknown events."""
        self.handled_events["unknown"].append(event)


@pytest.fixture
def clear_registry() -> Generator[None, None, None]:
    """Fixture to clear the event handler registry between tests."""
    # Access the internal registry directly to clear it
    from slack_mcp.dispatcher import _HANDLERS

    _HANDLERS.clear()
    yield None
    _HANDLERS.clear()  # Clean up after test


@pytest.fixture
def mock_backend() -> MockQueueBackend:
    """Create a mock backend for testing."""
    return MockQueueBackend()


@pytest.fixture
def mock_handler() -> Generator[TestHandler, None, None]:
    """Create a mock handler for testing."""
    handler = TestHandler()
    yield handler


@pytest.mark.usefixtures("clear_registry")
class TestSlackEventConsumer:
    """Test suite for SlackEventConsumer."""

    @pytest.fixture
    def oo_handler(self) -> TestHandler:
        """Fixture providing a TestHandler instance."""
        return TestHandler()

    @pytest.fixture
    def consumer_with_oo_handler(self, mock_backend: MockQueueBackend, oo_handler: TestHandler) -> SlackEventConsumer:
        """Fixture providing a SlackEventConsumer with an OO-style handler."""
        return SlackEventConsumer(backend=mock_backend, handler=oo_handler)

    @pytest.fixture
    def consumer_with_decorators(self, mock_backend: MockQueueBackend) -> SlackEventConsumer:
        """Fixture providing a SlackEventConsumer with decorator-based handlers."""

        # These decorator registrations are local to this fixture
        @slack_event(SlackEvent.MESSAGE)
        async def handle_message(event: Dict[str, Any]) -> None:
            event["handled_by_decorator"] = "message"

        @slack_event(SlackEvent.REACTION_ADDED)
        async def handle_reaction(event: Dict[str, Any]) -> None:
            event["handled_by_decorator"] = "reaction_added"

        return SlackEventConsumer(mock_backend)

    @pytest.fixture
    def consumer_with_both(self, mock_backend: MockQueueBackend, oo_handler: TestHandler) -> SlackEventConsumer:
        """Fixture providing a SlackEventConsumer with both handler types."""

        # These decorator registrations are local to this fixture
        @slack_event(SlackEvent.MESSAGE)
        async def handle_message(event: Dict[str, Any]) -> None:
            event["handled_by_decorator"] = "message"

        return SlackEventConsumer(mock_backend, handler=oo_handler)

    @pytest.mark.asyncio
    async def test_oo_handler_processing(
        self, mock_backend: MockQueueBackend, consumer_with_oo_handler: SlackEventConsumer, oo_handler: TestHandler
    ) -> None:
        """Test that events are processed by OO-style handlers."""
        # Add test events
        mock_backend.events = [
            {"type": "message", "text": "Hello"},
            {"type": "reaction_added", "reaction": "thumbsup"},
            {"type": "app_mention", "text": "<@U123> hello"},
            {"type": "unknown_type", "data": "test"},
        ]

        # Create a task to run the consumer and wait briefly
        task = asyncio.create_task(consumer_with_oo_handler.run(handler=oo_handler.handle_event))
        await asyncio.sleep(0.2)

        # Stop the consumer and wait for it to finish
        await consumer_with_oo_handler.shutdown()
        await task

        # Verify events were processed by the OO-style handler
        assert len(oo_handler.handled_events["message"]) == 1
        assert len(oo_handler.handled_events["reaction_added"]) == 1
        assert len(oo_handler.handled_events["app_mention"]) == 1
        assert len(oo_handler.handled_events["unknown"]) == 1

    @pytest.mark.asyncio
    async def test_decorator_handler_processing(
        self, mock_backend: MockQueueBackend, consumer_with_decorators: SlackEventConsumer
    ) -> None:
        """Test that events are processed by decorator-based handlers."""
        # Add test events
        test_events = [{"type": "message", "text": "Hello"}, {"type": "reaction_added", "reaction": "thumbsup"}]
        mock_backend.events = test_events.copy()

        # Create a task to run the consumer and wait briefly
        # For decorator-based handlers, we need to use the dispatch_event function
        # Create a wrapper to make the return type compatible
        async def dispatch_wrapper(event: Dict[str, Any]) -> None:
            await dispatch_event(event)

        task = asyncio.create_task(consumer_with_decorators.run(handler=dispatch_wrapper))
        await asyncio.sleep(0.2)

        # Stop the consumer and wait for it to finish
        await consumer_with_decorators.shutdown()
        await task

        # Verify events were processed by decorators
        assert mock_backend.events[0].get("handled_by_decorator") == "message"
        assert mock_backend.events[1].get("handled_by_decorator") == "reaction_added"

    @pytest.mark.asyncio
    async def test_both_handler_types(
        self, mock_backend: MockQueueBackend, consumer_with_both: SlackEventConsumer, oo_handler: TestHandler
    ) -> None:
        """Test that events are processed by both handler types when both are present."""
        # Add test event
        mock_backend.events = [{"type": "message", "text": "Hello"}]

        # Create a task to run the consumer and wait briefly
        task = asyncio.create_task(consumer_with_both.run(handler=oo_handler.handle_event))
        await asyncio.sleep(0.2)

        # Stop the consumer and wait for it to finish
        await consumer_with_both.shutdown()
        await task

        # Verify the event was processed by the OO-style handler only
        # (SlackEventConsumer only uses OO handler when provided, not decorator handlers)
        assert len(oo_handler.handled_events["message"]) == 1

        # Create a separate consumer with only decorator handlers to verify they work too
        decorator_only_consumer = SlackEventConsumer(backend=cast(QueueBackend, mock_backend))  # No OO handler
        mock_backend.events = [{"type": "message", "text": "Hello"}]

        # Run the decorator-only consumer
        # Create a wrapper to make the return type compatible
        async def dispatch_wrapper(event: Dict[str, Any]) -> None:
            await dispatch_event(event)

        task = asyncio.create_task(decorator_only_consumer.run(handler=dispatch_wrapper))
        await asyncio.sleep(0.2)

        # Stop the consumer and wait for it to finish
        await decorator_only_consumer.shutdown()
        await task

        # Now verify the decorator handler was called in this scenario
        assert mock_backend.events[0].get("handled_by_decorator") == "message"

    @pytest.mark.asyncio
    async def test_error_handling(
        self, mock_backend: MockQueueBackend, consumer_with_oo_handler: SlackEventConsumer, oo_handler: TestHandler
    ) -> None:
        """Test that errors in event processing are caught and logged."""
        # The consumer uses the module-level logger, not an instance variable
        with patch("slack_mcp.consumer.slack_event._LOG") as mock_logger:
            # Create an event that will cause an error in the handler
            mock_backend.events = [{"will_cause_error": True}]

            # Patch the _process_event method to raise an exception
            with patch.object(consumer_with_oo_handler, "_process_event", side_effect=ValueError("Test error")):
                # Create a task to run the consumer and wait briefly
                # Use a simple async handler that returns None to satisfy the type requirements
                async def dummy_handler(event: Dict[str, Any]) -> None:
                    pass

                task = asyncio.create_task(consumer_with_oo_handler.run(handler=dummy_handler))
                await asyncio.sleep(0.2)

                # Stop the consumer and wait for it to finish
                await consumer_with_oo_handler.shutdown()
                await task

            # Verify the error was logged
            mock_logger.exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown(
        self, mock_backend: MockQueueBackend, consumer_with_oo_handler: SlackEventConsumer, oo_handler: TestHandler
    ) -> None:
        """Test that the consumer shuts down gracefully when stopped."""
        # Add a lot of test events
        mock_backend.events = [{"type": "message", "text": f"Message {i}"} for i in range(100)]

        # Create a task to run the consumer
        # Use a simple async handler that returns None to satisfy the type requirements
        async def dummy_handler(event: Dict[str, Any]) -> None:
            pass

        task = asyncio.create_task(consumer_with_oo_handler.run(handler=dummy_handler))

        # Allow some events to be processed
        await asyncio.sleep(0.1)

        # Stop the consumer
        await consumer_with_oo_handler.shutdown()

        # Wait for the consumer to finish
        await task

    @pytest.mark.asyncio
    async def test_stop_signal_handling(self, mock_backend: MockQueueBackend) -> None:
        """Test that the consumer stops processing when _stop event is set."""

        # Create a custom backend that will yield events indefinitely
        class NeverEndingBackend(QueueBackend):
            async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
                # This will keep yielding events until the consumer stops
                counter = 0
                while True:
                    yield {"type": "message", "text": f"Message {counter}"}
                    counter += 1
                    await asyncio.sleep(0.01)  # Small delay to avoid CPU hogging

            async def publish(self, key: str, payload: Dict[str, Any]) -> None:
                """Required by QueueBackend protocol but not used in this test."""

            @classmethod
            def from_env(cls) -> QueueBackend:
                """Required by QueueBackend protocol but not used in this test."""
                return cls()

        # Create a handler that counts processed events
        class CountingHandler(BaseSlackEventHandler):
            def __init__(self) -> None:
                super().__init__()
                self.processed_count = 0

            async def handle_event(self, event: Dict[str, Any]) -> None:
                self.processed_count += 1
                await super().handle_event(event)

        # Create the handler and consumer
        handler = CountingHandler()
        consumer = SlackEventConsumer(backend=NeverEndingBackend(), handler=handler)

        # Start the consumer
        with patch("slack_mcp.consumer.slack_event._LOG") as mock_logger:
            consumer_task = asyncio.create_task(consumer.run(handler=handler.handle_event))

            # Let it process some events
            await asyncio.sleep(0.1)

            # Set the stop event directly
            consumer._stop.set()

            # Wait for the consumer to finish (should exit the loop due to stop signal)
            await asyncio.wait_for(consumer_task, timeout=1.0)

            # Verify the log message was called
            mock_logger.info.assert_any_call("Received stop signal, shutting down")

        # Verify that some events were processed before stopping
        assert handler.processed_count > 0

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self, mock_backend: MockQueueBackend) -> None:
        """Test that unexpected exceptions in the consumer's run method are caught and logged."""

        # Create a backend that raises an unexpected exception
        class ExplodingBackend(QueueBackend):
            async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
                # Process a few events normally
                for i in range(3):
                    yield {"type": "message", "text": f"Message {i}"}
                    await asyncio.sleep(0.01)

                # Then simulate a connection error or other unexpected exception
                raise ConnectionError("Simulated connection failure")

            async def publish(self, key: str, payload: Dict[str, Any]) -> None:
                """Required by QueueBackend protocol but not used in this test."""

            @classmethod
            def from_env(cls) -> QueueBackend:
                """Required by QueueBackend protocol but not used in this test."""
                return cls()

        # Create a handler and consumer
        handler = TestHandler()
        consumer = SlackEventConsumer(backend=ExplodingBackend(), handler=handler)

        # Start the consumer and verify exception handling
        with patch("slack_mcp.consumer.slack_event._LOG") as mock_logger:
            # Run the consumer - it should catch the exception and log it
            await consumer.run(handler=handler.handle_event)

            # Verify the exception was logged
            mock_logger.exception.assert_called_once()
            assert "Unexpected error in consumer" in mock_logger.exception.call_args[0][0]
            assert "Simulated connection failure" in mock_logger.exception.call_args[0][0]

            # Verify the "consumer stopped" message was logged in the finally block
            mock_logger.info.assert_any_call("Slack event consumer stopped")

        # Verify that events were processed before the exception
        assert len(handler.handled_events["message"]) == 3
