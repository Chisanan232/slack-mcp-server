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
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from slack_mcp.backends.memory import MemoryBackend
from slack_mcp.backends.protocol import QueueBackend
from slack_mcp.consumer import SlackEventConsumer
from slack_mcp.handler.base import BaseSlackEventHandler
from slack_mcp.handler.decorator import DecoratorHandler

# Create a module-level DecoratorHandler instance for tests
handler = DecoratorHandler()


class TestSlackEventConsumerContract:
    """Contract tests for SlackEventConsumer."""

    @pytest.fixture
    def mock_backend(self) -> AsyncMock:
        """Fixture providing a mock queue backend."""
        backend = AsyncMock(spec=QueueBackend)
        return backend

    @pytest.fixture
    def mock_handler(self) -> AsyncMock:
        """Fixture providing a mock event handler."""
        handler = AsyncMock(spec=BaseSlackEventHandler)
        return handler

    @pytest.fixture
    def memory_backend(self) -> MemoryBackend:
        """Fixture providing a real memory backend for testing."""
        # Reset the class-level queue to ensure tests don't interfere with each other
        MemoryBackend._queue = asyncio.Queue()
        return MemoryBackend()

    def test_initialization(self, mock_backend: AsyncMock, mock_handler: AsyncMock) -> None:
        """Test that SlackEventConsumer initializes correctly with backend and handler."""
        # Create with both backend and handler
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)
        assert consumer.backend == mock_backend
        assert consumer._slack_handler == mock_handler

        # Create with just backend (should use default DecoratorHandler)
        consumer_no_handler = SlackEventConsumer(backend=mock_backend)
        assert consumer_no_handler.backend == mock_backend
        assert isinstance(consumer_no_handler._slack_handler, DecoratorHandler)

        # Create with consumer group
        group_name = "test-group"
        consumer_with_group = SlackEventConsumer(backend=mock_backend, handler=mock_handler, group=group_name)
        assert consumer_with_group.group == group_name

    @pytest.mark.asyncio
    async def test_process_event_with_handler(self, mock_backend: AsyncMock, mock_handler: AsyncMock) -> None:
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
    async def test_process_event_with_decorator(self, mock_backend: AsyncMock) -> None:
        """Test that _process_event uses DecoratorHandler when no explicit handler is provided."""
        # Create consumer without explicit handler (should use default DecoratorHandler)
        consumer = SlackEventConsumer(backend=mock_backend)

        # Create test event
        test_event = {"type": "message", "text": "Hello", "channel": "C12345"}

        # Process the event
        await consumer._process_event(test_event)

        # Since we're using a real DecoratorHandler, there's no easy way to verify
        # it was called without mocking, but we can verify no exceptions were raised

    @pytest.mark.asyncio
    async def test_run_and_shutdown(self, mock_backend: AsyncMock, mock_handler: AsyncMock) -> None:
        """Test that run consumes events and shutdown stops consumption."""
        # Create consumer
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)

        # Set up the mock backend to yield events and then hang
        events = [
            {"type": "message", "text": "Hello"},
            {"type": "reaction_added", "reaction": "+1"},
        ]

        # Configure the mock to yield events and then wait indefinitely
        mock_backend.consume.return_value.__aiter__.return_value = self._async_iter(events)

        # Create a dummy handler for the run method
        async def dummy_handler(event: Dict[str, Any]) -> None:
            pass

        # Start the consumer in a task
        task = asyncio.create_task(consumer.run(handler=dummy_handler))

        # Wait a bit to ensure it's running
        await asyncio.sleep(0.1)

        # Shutdown the consumer
        await consumer.shutdown()

        # Wait for the task to complete
        await asyncio.wait_for(task, timeout=1.0)

        # Verify the task completed
        assert task.done()

    @staticmethod
    async def _async_iter(items):
        """Helper to create an async iterator from a list."""
        for item in items:
            yield item
            await asyncio.sleep(0.01)
        # Hang indefinitely until cancelled
        while True:
            await asyncio.sleep(3600)

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_backend: AsyncMock, mock_handler: AsyncMock) -> None:
        """Test that errors in event processing are caught and logged."""
        # Create consumer
        consumer = SlackEventConsumer(backend=mock_backend, handler=mock_handler)

        # Set up the mock backend to yield a single event
        mock_backend.consume = AsyncMock()
        mock_backend.consume.return_value.__aiter__ = AsyncMock()

        # Create a generator that yields one event and then raises an exception
        async def mock_generator():
            yield {"type": "message", "text": "Hello"}

        mock_backend.consume.return_value.__aiter__.return_value = mock_generator()

        # Make the handler raise an exception
        mock_handler.handle_event.side_effect = ValueError("Test error")

        # Mock the logger
        with patch("slack_mcp.consumer.slack_event._LOG") as mock_log:
            # Start the consumer in a task
            task = asyncio.create_task(consumer.run(handler=mock_handler.handle_event))

            # Wait a bit to ensure it processes the event
            await asyncio.sleep(0.1)

            # Shutdown the consumer
            await consumer.shutdown()

            # Wait for the task to complete
            await asyncio.wait_for(task, timeout=1.0)

            # Verify the error was logged - check for "Unexpected error" which is what the consumer logs
            mock_log.exception.assert_called_once()
            assert any("error" in str(call).lower() for call in mock_log.exception.call_args_list)

    @pytest.mark.asyncio
    async def test_integration_with_decorator_handler(self, memory_backend: MemoryBackend) -> None:
        """Test integration with DecoratorHandler."""
        # Create a handler and register a test handler function
        handler = DecoratorHandler()

        # Track calls to the handler
        calls = []

        @handler.message
        async def handle_message(event: Dict[str, Any]) -> None:
            calls.append(event)

        # Create consumer with the handler
        consumer = SlackEventConsumer(backend=memory_backend, handler=handler)

        # Publish a test event
        test_event = {"type": "message", "text": "Hello"}
        await memory_backend.publish("test", test_event)

        # Create a dummy handler for the run method
        async def dummy_handler(event: Dict[str, Any]) -> None:
            pass

        # Start the consumer in a task
        task = asyncio.create_task(consumer.run(handler=dummy_handler))

        # Wait a bit to ensure it processes the event
        await asyncio.sleep(0.1)

        # Shutdown the consumer
        await consumer.shutdown()

        # Wait for the task to complete
        await asyncio.wait_for(task, timeout=1.0)

        # Verify the handler was called
        assert len(calls) == 1
        assert calls[0]["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_consumer_group_support(self, mock_backend: AsyncMock) -> None:
        """Test that consumer group is passed to the backend."""
        # Create consumer with group
        group_name = "test-group"
        consumer = SlackEventConsumer(backend=mock_backend, group=group_name)

        # Create a dummy handler for the run method
        async def dummy_handler(event: Dict[str, Any]) -> None:
            pass

        # Start the consumer
        task = asyncio.create_task(consumer.run(handler=dummy_handler))

        # Wait a bit
        await asyncio.sleep(0.1)

        # Shutdown the consumer
        await consumer.shutdown()

        # Wait for the task to complete
        await asyncio.wait_for(task, timeout=1.0)

        # Verify the group was passed to the backend
        mock_backend.consume.assert_called_once_with(group=group_name)

    @pytest.mark.asyncio
    async def test_cancellation_handling(self, mock_backend: AsyncMock) -> None:
        """Test that cancellation is handled gracefully."""
        # Create consumer
        consumer = SlackEventConsumer(backend=mock_backend, handler=AsyncMock(spec=BaseSlackEventHandler))

        mock_backend.consume.return_value.__aiter__.return_value = self._async_iter([])

        # Mock the logger
        with patch("slack_mcp.consumer.slack_event._LOG") as mock_log:
            # Create a dummy handler for the run method
            async def dummy_handler(event: Dict[str, Any]) -> None:
                pass

            # Start the consumer in a task
            task = asyncio.create_task(consumer.run(handler=dummy_handler))

            # Wait a bit
            await asyncio.sleep(0.1)

            # Cancel the task
            task.cancel()

            # Wait for the task to complete or raise CancelledError
            try:
                await task
            except asyncio.CancelledError:
                pass

            # Verify the cancellation was logged
            mock_log.info.assert_any_call("Slack event consumer stopped")
