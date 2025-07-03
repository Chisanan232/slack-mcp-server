"""
Contract tests for SlackEventConsumer class.

These tests verify that the SlackEventConsumer class adheres to its contract
and provides expected behavior. They focus on:

1. Initialization with QueueBackend and EventHandler
2. Event processing and routing
3. Graceful shutdown
4. Error handling
5. Integration with different handler types
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest import mock

import pytest

from slack_mcp.backends.memory import MemoryBackend
from slack_mcp.backends.protocol import QueueBackend
from slack_mcp.consumer.slack_event import SlackEventConsumer
from slack_mcp.handler.base import EventHandler
from slack_mcp.handler.decorator import DecoratorHandler


class TestSlackEventConsumerContract:
    """Contract tests for SlackEventConsumer."""

    @pytest.fixture
    def mock_backend(self) -> mock.AsyncMock:
        """Fixture providing a mock queue backend."""
        backend = mock.AsyncMock(spec=QueueBackend)
        return backend

    @pytest.fixture
    def mock_handler(self) -> mock.AsyncMock:
        """Fixture providing a mock event handler."""
        handler = mock.AsyncMock(spec=EventHandler)
        return handler

    @pytest.fixture
    def memory_backend(self) -> MemoryBackend:
        """Fixture providing a real memory backend for testing."""
        # Reset the class-level queue to ensure tests don't interfere with each other
        MemoryBackend._queue = asyncio.Queue()
        return MemoryBackend()

    def test_initialization(self, mock_backend: mock.AsyncMock, mock_handler: mock.AsyncMock) -> None:
        """Test that SlackEventConsumer initializes correctly with backend and handler."""
        # Create with both backend and handler
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)
        assert consumer.backend == mock_backend
        assert consumer._slack_handler == mock_handler

        # Create with just backend (should use dispatcher)
        consumer_no_handler = SlackEventConsumer(backend=mock_backend)
        assert consumer_no_handler.backend == mock_backend
        assert consumer_no_handler._slack_handler is None

        # Create with consumer group
        group_name = "test-group"
        consumer_with_group = SlackEventConsumer(
            backend=mock_backend, handler=mock_handler, group=group_name
        )
        assert consumer_with_group.group == group_name

    @pytest.mark.asyncio
    async def test_process_event_with_handler(
        self, mock_backend: mock.AsyncMock, mock_handler: mock.AsyncMock
    ) -> None:
        """Test that _process_event routes events to the handler."""
        # Create consumer with handler
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)

        # Create test event
        test_event = {"type": "message", "text": "Hello", "channel": "C12345"}

        # Process the event
        await consumer._process_event(test_event)

        # Verify handler was called with the event
        mock_handler.handle_event.assert_called_once_with(test_event)

    @pytest.mark.asyncio
    async def test_process_event_with_dispatcher(
        self, mock_backend: mock.AsyncMock
    ) -> None:
        """Test that _process_event uses dispatcher when no handler is provided."""
        # Create consumer without handler
        consumer = SlackEventConsumer(backend=mock_backend)

        # Create test event
        test_event = {"type": "message", "text": "Hello", "channel": "C12345"}

        # Mock the dispatch_event function
        with mock.patch("slack_mcp.consumer.slack_event.dispatch_event") as mock_dispatch:
            # Process the event
            await consumer._process_event(test_event)

            # Verify dispatch_event was called with the event
            mock_dispatch.assert_called_once_with(test_event)

    @pytest.mark.asyncio
    async def test_run_and_shutdown(
        self, mock_backend: mock.AsyncMock, mock_handler: mock.AsyncMock
    ) -> None:
        """Test that run consumes events and shutdown stops consumption."""
        # Set up mock backend to yield test events
        test_events = [
            {"type": "message", "text": "Hello", "channel": "C12345"},
            {"type": "reaction_added", "reaction": "thumbsup"},
        ]
        mock_backend.consume.return_value.__aiter__.return_value = test_events

        # Create consumer
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)

        # Start the consumer
        consumer_task = asyncio.create_task(consumer.run())
        
        # Allow some time for processing
        await asyncio.sleep(0.1)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Wait for the consumer task to complete
        try:
            await asyncio.wait_for(consumer_task, timeout=0.5)
        except asyncio.TimeoutError:
            # If it times out, cancel it forcefully
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        # Verify backend.consume was called with the correct group
        mock_backend.consume.assert_called_once_with(group=None)
        
        # Verify handler.handle_event was called for each event
        assert mock_handler.handle_event.call_count == len(test_events)
        mock_handler.handle_event.assert_has_calls(
            [mock.call(event) for event in test_events]
        )

    @pytest.mark.asyncio
    async def test_error_handling(
        self, mock_backend: mock.AsyncMock, mock_handler: mock.AsyncMock
    ) -> None:
        """Test that errors in event processing are caught and don't crash the consumer."""
        # Set up mock backend to yield test events
        test_events = [
            {"type": "message", "text": "Hello", "channel": "C12345"},
            {"type": "reaction_added", "reaction": "thumbsup"},
            {"type": "message", "text": "World", "channel": "C12345"},
        ]
        mock_backend.consume.return_value.__aiter__.return_value = test_events
        
        # Make the handler raise an exception for the second event
        mock_handler.handle_event.side_effect = [
            None,
            ValueError("Test error"),
            None,
        ]
        
        # Create consumer
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)
        
        # Start the consumer
        consumer_task = asyncio.create_task(consumer.run())
        
        # Allow some time for processing
        await asyncio.sleep(0.1)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Wait for the consumer task to complete
        try:
            await asyncio.wait_for(consumer_task, timeout=0.5)
        except asyncio.TimeoutError:
            # If it times out, cancel it forcefully
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        # Verify handler.handle_event was called for all events despite the error
        assert mock_handler.handle_event.call_count == len(test_events)

    @pytest.mark.asyncio
    async def test_integration_with_decorator_handler(self, memory_backend: MemoryBackend) -> None:
        """Test integration with DecoratorHandler."""
        # Create a DecoratorHandler
        handler = DecoratorHandler()
        
        # Track received events
        received_events: List[Dict[str, Any]] = []
        
        # Register handlers for different event types
        @handler.message
        async def handle_message(event: Dict[str, Any]) -> None:
            received_events.append(("message", event))
        
        @handler.reaction_added
        async def handle_reaction(event: Dict[str, Any]) -> None:
            received_events.append(("reaction", event))
        
        # Create consumer with the handler
        consumer = SlackEventConsumer(backend=memory_backend, handler=handler)
        
        # Start the consumer
        consumer_task = asyncio.create_task(consumer.run())
        
        # Create test events
        test_events = [
            {"type": "message", "text": "Hello", "channel": "C12345"},
            {"type": "reaction_added", "reaction": "thumbsup"},
        ]
        
        # Publish events to the memory backend
        for i, event in enumerate(test_events):
            await memory_backend.publish(f"event-{i}", event)
        
        # Allow time for processing
        await asyncio.sleep(0.1)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Cancel the task if it's still running
        if not consumer_task.done():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        # Verify events were processed by the correct handlers
        assert len(received_events) == 2
        assert received_events[0][0] == "message"
        assert received_events[0][1]["text"] == "Hello"
        assert received_events[1][0] == "reaction"
        assert received_events[1][1]["reaction"] == "thumbsup"

    @pytest.mark.asyncio
    async def test_consumer_group_support(self, mock_backend: mock.AsyncMock) -> None:
        """Test that consumer group is passed to the backend."""
        # Create consumer with group
        group_name = "test-group"
        consumer = SlackEventConsumer(backend=mock_backend, group=group_name)
        
        # Set up mock backend to yield no events
        mock_backend.consume.return_value.__aiter__.return_value = []
        
        # Start the consumer
        consumer_task = asyncio.create_task(consumer.run())
        
        # Allow some time for processing
        await asyncio.sleep(0.1)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Cancel the task if it's still running
        if not consumer_task.done():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        # Verify backend.consume was called with the correct group
        mock_backend.consume.assert_called_once_with(group=group_name)

    @pytest.mark.asyncio
    async def test_cancellation_handling(
        self, mock_backend: mock.AsyncMock, mock_handler: mock.AsyncMock
    ) -> None:
        """Test that the consumer handles task cancellation gracefully."""
        # Set up mock backend to block indefinitely
        async def never_ending_consume(*args, **kwargs):
            while True:
                await asyncio.sleep(1000)
                yield {"type": "message"}  # This will never be reached
        
        mock_backend.consume.return_value.__aiter__.side_effect = never_ending_consume
        
        # Create consumer
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)
        
        # Start the consumer
        consumer_task = asyncio.create_task(consumer.run())
        
        # Allow some time to start
        await asyncio.sleep(0.1)
        
        # Cancel the task directly
        consumer_task.cancel()
        
        # Wait for the task to complete
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        
        # Verify the task is done
        assert consumer_task.done()
