"""
Contract tests for EventConsumer implementations.

These tests verify that all EventConsumer implementations conform to the expected
behavior defined by the protocol. Any new consumer implementation must pass these tests.
"""

import abc
import asyncio
from typing import Any, Dict, List, Optional, Type
from unittest import mock

import pytest

from slack_mcp.backends.consumer import AsyncLoopConsumer, EventConsumer
from slack_mcp.backends.protocol import QueueBackend
from slack_mcp.backends.memory import MemoryBackend


class EventConsumerContractTest(abc.ABC):
    """Abstract base class for EventConsumer contract tests.

    This class defines a set of tests that all EventConsumer implementations
    must pass to be considered compliant with the protocol.
    """

    @abc.abstractmethod
    def create_consumer(self, backend: QueueBackend, group: Optional[str] = None) -> EventConsumer:
        """Create a new instance of the consumer being tested.
        
        Args:
            backend: The queue backend to use with this consumer
            group: Optional consumer group name
            
        Returns:
            An instance of the EventConsumer implementation being tested
        """
        pass

    @pytest.fixture
    def mock_backend(self) -> mock.AsyncMock:
        """Fixture providing a mock backend for testing."""
        backend = mock.AsyncMock(spec=QueueBackend)
        return backend

    @pytest.fixture
    def memory_backend(self) -> MemoryBackend:
        """Fixture providing a real memory backend for testing."""
        # Reset the class-level queue to ensure tests don't interfere with each other
        MemoryBackend._queue = asyncio.Queue()
        return MemoryBackend()

    @pytest.mark.asyncio
    async def test_basic_message_processing(self, mock_backend: mock.AsyncMock) -> None:
        """Test that the consumer processes messages using the provided handler."""
        # Set up the mock backend to yield test messages
        test_messages = [
            {"type": "message", "text": "Hello", "channel": "C12345"},
            {"type": "message", "text": "World", "channel": "C12345"}
        ]
        mock_backend.consume.return_value.__aiter__.return_value = test_messages
        
        # Create a mock handler and track processed messages
        processed_messages: List[Dict[str, Any]] = []
        async def handler(message: Dict[str, Any]) -> None:
            processed_messages.append(message)
        
        # Create the consumer
        consumer = self.create_consumer(mock_backend)
        
        # Run the consumer with a timeout
        # (In a real scenario, the consumer would run indefinitely)
        consumer_task = asyncio.create_task(consumer.run(handler))
        await asyncio.sleep(0.1)  # Give the consumer time to process messages
        await consumer.shutdown()
        
        # Verify all messages were processed
        assert len(processed_messages) == len(test_messages)
        assert processed_messages == test_messages

    @pytest.mark.asyncio
    async def test_consumer_group_support(self, mock_backend: mock.AsyncMock) -> None:
        """Test that the consumer passes consumer group to the backend."""
        # Create the consumer with a group
        group_name = "test-group"
        consumer = self.create_consumer(mock_backend, group=group_name)
        
        # Run the consumer briefly
        async def handler(message: Dict[str, Any]) -> None:
            pass
            
        consumer_task = asyncio.create_task(consumer.run(handler))
        await asyncio.sleep(0.1)
        await consumer.shutdown()
        
        # Verify the backend was called with the correct group
        mock_backend.consume.assert_called_once_with(group=group_name)

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_backend: mock.AsyncMock) -> None:
        """Test that the consumer properly handles errors in the handler."""
        # Set up the mock backend to yield test messages
        test_messages = [
            {"id": 1, "data": "good"},
            {"id": 2, "data": "will_fail"},
            {"id": 3, "data": "good_again"}
        ]
        mock_backend.consume.return_value.__aiter__.return_value = test_messages
        
        # Create a handler that fails on the second message
        processed_ids: List[int] = []
        async def failing_handler(message: Dict[str, Any]) -> None:
            if message["id"] == 2:
                raise ValueError("Expected test error")
            processed_ids.append(message["id"])
        
        # Create the consumer
        consumer = self.create_consumer(mock_backend)
        
        # Run the consumer
        consumer_task = asyncio.create_task(consumer.run(failing_handler))
        await asyncio.sleep(0.1)
        await consumer.shutdown()
        
        # Verify the consumer processed the other messages despite the error
        assert 1 in processed_ids
        assert 3 in processed_ids
        assert 2 not in processed_ids  # This one failed

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, mock_backend: mock.AsyncMock) -> None:
        """Test that the consumer shuts down gracefully."""
        # Set up the mock backend to yield a never-ending stream of messages
        async def infinite_messages():
            for i in range(1000):  # Large enough to not finish during the test
                yield {"id": i}
                await asyncio.sleep(0.01)
                
        mock_backend.consume.return_value.__aiter__.side_effect = infinite_messages
        
        # Create the consumer
        consumer = self.create_consumer(mock_backend)
        
        # Track processed messages
        processed_messages: List[Dict[str, Any]] = []
        async def handler(message: Dict[str, Any]) -> None:
            processed_messages.append(message)
        
        # Run the consumer
        consumer_task = asyncio.create_task(consumer.run(handler))
        
        # Let it process some messages
        await asyncio.sleep(0.05)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Verify some messages were processed before shutdown
        assert len(processed_messages) > 0

    @pytest.mark.asyncio
    async def test_real_world_processing_with_memory_backend(self, memory_backend: MemoryBackend) -> None:
        """Test with a real memory backend to ensure end-to-end functionality."""
        # Create sample Slack-like messages
        slack_messages = [
            {
                "type": "message",
                "user": "U12345",
                "text": "Hello, is this working?",
                "ts": "1625097600.000100",
                "channel": "C12345"
            },
            {
                "type": "reaction_added",
                "user": "U67890",
                "reaction": "thumbsup",
                "item": {
                    "type": "message",
                    "channel": "C12345",
                    "ts": "1625097600.000100"
                },
                "ts": "1625097605.000200"
            },
            {
                "type": "message",
                "user": "U67890",
                "text": "Yes, it's working!",
                "ts": "1625097610.000300",
                "channel": "C12345",
                "thread_ts": "1625097600.000100"
            }
        ]
        
        # Event to signal when all messages are processed
        processing_done = asyncio.Event()
        expected_message_count = len(slack_messages)
        
        # Process messages with a handler that categorizes by type
        message_types: Dict[str, int] = {}
        thread_replies: List[Dict[str, Any]] = []
        processed_count = 0
        
        async def categorizing_handler(message: Dict[str, Any]) -> None:
            nonlocal processed_count
            
            msg_type = message.get("type", "unknown")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
            
            # Track thread replies
            if msg_type == "message" and "thread_ts" in message:
                thread_replies.append(message)
            
            processed_count += 1
            if processed_count >= expected_message_count:
                processing_done.set()
        
        # Create the consumer
        consumer = self.create_consumer(memory_backend)
        
        # Start the consumer task
        consumer_task = asyncio.create_task(consumer.run(categorizing_handler))
        
        # Now publish the messages (after consumer is running)
        for i, message in enumerate(slack_messages):
            await memory_backend.publish(f"slack-event-{i}", message)
        
        # Wait for all messages to be processed or timeout
        try:
            await asyncio.wait_for(processing_done.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass  # We'll check counts below regardless
        
        # Cancel the consumer task directly instead of using shutdown
        # This avoids potential race conditions with the memory backend
        consumer_task.cancel()
        try:
            await consumer_task
        except (asyncio.CancelledError, ValueError):
            # Ignore cancellation and any ValueError from task_done
            pass
        
        # Verify message categorization
        assert message_types.get("message", 0) == 2
        assert message_types.get("reaction_added", 0) == 1
        
        # Verify thread identification
        assert len(thread_replies) == 1
        assert thread_replies[0]["ts"] == "1625097610.000300"
        assert thread_replies[0]["thread_ts"] == "1625097600.000100"


class TestAsyncLoopConsumerContract(EventConsumerContractTest):
    """Contract tests for the AsyncLoopConsumer implementation."""

    def create_consumer(self, backend: QueueBackend, group: Optional[str] = None) -> AsyncLoopConsumer:
        """Create a new AsyncLoopConsumer instance for testing."""
        return AsyncLoopConsumer(backend, group=group)

    @pytest.mark.asyncio
    async def test_run_idempotence(self, mock_backend: mock.AsyncMock) -> None:
        """Test that calling run multiple times doesn't restart the consumer."""
        # Set up the mock backend
        mock_backend.consume.return_value.__aiter__.return_value = []
        
        # Create the consumer
        consumer = self.create_consumer(mock_backend)
        
        # Create a mock handler
        mock_handler = mock.AsyncMock()
        
        # Call run twice
        task1 = asyncio.create_task(consumer.run(mock_handler))
        await asyncio.sleep(0.05)
        task2 = asyncio.create_task(consumer.run(mock_handler))
        await asyncio.sleep(0.05)
        
        # Shutdown the consumer
        await consumer.shutdown()
        
        # Verify consume was only called once
        mock_backend.consume.assert_called_once()
