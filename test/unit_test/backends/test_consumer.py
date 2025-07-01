"""
Unit tests for the event consumer implementations.
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from unittest import mock

import pytest

from slack_mcp.backends.consumer import AsyncLoopConsumer
from slack_mcp.backends.protocol import QueueBackend


class MockBackend:
    """Test double that directly implements QueueBackend for testing purposes."""
    
    def __init__(self):
        """Initialize the mock backend with default values."""
        self.items = []
        self.sleep_time = 0
        self.group_used = None
        self.publish_called = False
        self.publish_messages = []
        self.consumed_count = 0
    
    async def publish(self, message: Dict[str, Any]) -> None:
        """Mock implementation of publish that records calls."""
        self.publish_called = True
        self.publish_messages.append(message)
    
    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Mock implementation of consume that yields configured items."""
        self.group_used = group
        self.consumed_count += 1
        
        for item in self.items:
            if self.sleep_time > 0:
                await asyncio.sleep(self.sleep_time)
            yield item
    
    @classmethod
    def from_env(cls) -> "MockBackend":
        """Factory method to satisfy protocol."""
        return cls()


class TestAsyncLoopConsumer:
    """Test the AsyncLoopConsumer implementation."""
    
    @pytest.mark.asyncio
    async def test_run_calls_handler_for_each_message(self):
        """Test that the handler is called for each consumed message."""
        # Create a mock backend
        mock_backend = MockBackend()
        mock_backend.items = [{"id": 1}, {"id": 2}]
        
        # Create a mock handler
        mock_handler = mock.AsyncMock()
        
        # Create the consumer
        consumer = AsyncLoopConsumer(mock_backend)
        
        # Run the consumer with a timeout to avoid hanging the test
        try:
            await asyncio.wait_for(consumer.run(mock_handler), timeout=0.5)
        except asyncio.TimeoutError:
            pass
        
        # Verify the handler was called with each message
        assert mock_handler.call_count == 2
        mock_handler.assert_any_call({"id": 1})
        mock_handler.assert_any_call({"id": 2})
    
    @pytest.mark.asyncio
    async def test_run_with_consumer_group(self):
        """Test running the consumer with a consumer group."""
        # Create a mock backend
        mock_backend = MockBackend()
        
        # Consumer group to test
        group_name = "test-group"
        
        # Create a mock handler
        mock_handler = mock.AsyncMock()
        
        # Create the consumer with a group
        consumer = AsyncLoopConsumer(mock_backend, group=group_name)
        
        # Run the consumer with a timeout to avoid hanging the test
        try:
            await asyncio.wait_for(consumer.run(mock_handler), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        
        # Verify the backend was called with the group
        assert mock_backend.group_used == group_name
    
    @pytest.mark.asyncio
    async def test_handler_error_doesnt_stop_consumer(self):
        """Test that the consumer continues even if the handler raises an exception."""
        # Create a mock backend
        mock_backend = MockBackend()
        
        # Set up the mock to yield three messages
        mock_backend.items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        # Create a handler that raises an exception on the second message
        processed_ids = []
        async def failing_handler(msg):
            if msg["id"] == 2:
                raise ValueError("Test error")
            processed_ids.append(msg["id"])
        
        # Create the consumer
        consumer = AsyncLoopConsumer(mock_backend)
        
        # Run the consumer with a timeout
        try:
            await asyncio.wait_for(consumer.run(failing_handler), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        
        # Verify both messages 1 and 3 were processed, even though 2 raised an error
        assert 1 in processed_ids
        assert 3 in processed_ids
        assert 2 not in processed_ids
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test that shutdown cancels the consumer task."""
        # Create a mock backend that blocks indefinitely
        mock_backend = MockBackend()
        
        # Set up the mock to simulate a long-running process
        mock_backend.items = [{"id": 1}, {"id": 2}, {"id": 3}]
        mock_backend.sleep_time = 1.0  # Simulate slow message processing
        
        # Create a mock handler
        mock_handler = mock.AsyncMock()
        
        # Create the consumer
        consumer = AsyncLoopConsumer(mock_backend)
        
        # Start the consumer in a background task
        task = asyncio.create_task(consumer.run(mock_handler))
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Verify the task was cancelled
        assert task.cancelled() or task.done()
    
    @pytest.mark.asyncio
    async def test_idempotent_run(self):
        """Test that calling run multiple times doesn't restart the consumer."""
        # Create a mock backend
        mock_backend = MockBackend()
        # Add some items so the consumer doesn't exit immediately
        mock_backend.sleep_time = 0.5
        mock_backend.items = [{"id": 1}]
        
        # Create a mock handler
        mock_handler = mock.AsyncMock()
        
        # Create the consumer
        consumer = AsyncLoopConsumer(mock_backend)
        
        # Run the consumer twice with small timeouts
        task1 = asyncio.create_task(consumer.run(mock_handler))
        await asyncio.sleep(0.1)
        task2 = asyncio.create_task(consumer.run(mock_handler))
        await asyncio.sleep(0.1)
        
        # Cancel the tasks to clean up
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass
        
        # The second task should return immediately since consumer is already running
        # so it should already be done
        assert task2.done()
        
        # Only one consume call should happen
        assert mock_backend.consumed_count == 1
