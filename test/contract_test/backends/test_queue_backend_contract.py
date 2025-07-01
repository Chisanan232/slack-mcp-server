"""
Contract tests for QueueBackend implementations.

These tests verify that all QueueBackend implementations conform to the expected
behavior defined by the protocol. Any new backend must pass these tests.
"""

import abc
import asyncio
from typing import Any, Dict, List

import pytest

from slack_mcp.backends.memory import MemoryBackend
from slack_mcp.backends.protocol import QueueBackend


class QueueBackendContractTest(abc.ABC):
    """Abstract base class for QueueBackend contract tests.

    This class defines a set of tests that all QueueBackend implementations
    must pass to be considered compliant with the protocol.
    """

    @abc.abstractmethod
    def create_backend(self) -> QueueBackend:
        """Create a new instance of the backend being tested."""

    @pytest.fixture
    def backend(self) -> QueueBackend:
        """Fixture providing a fresh backend instance for each test."""
        return self.create_backend()

    @pytest.mark.asyncio
    async def test_publish_and_consume(self, backend: QueueBackend) -> None:
        """Test that a message can be published and consumed."""
        # Publish a message
        test_key = "test-key"
        test_payload = {"message": "Hello, World!", "id": 123}

        await backend.publish(test_key, test_payload)

        # Consume the message
        async def get_first_message() -> Dict[str, Any]:
            async for msg in backend.consume():
                return msg

            # Fail the test if no message is received within timeout
            pytest.fail("No message received from consume()")

        # Use asyncio.wait_for to avoid hanging if the backend doesn't yield
        received_msg = await asyncio.wait_for(get_first_message(), 2.0)

        # The message content should match what was published
        assert received_msg == test_payload

    @pytest.mark.asyncio
    async def test_multiple_messages(self, backend: QueueBackend) -> None:
        """Test publishing and consuming multiple messages."""
        # Publish multiple messages
        messages = [{"id": 1, "data": "first"}, {"id": 2, "data": "second"}, {"id": 3, "data": "third"}]

        for i, msg in enumerate(messages):
            await backend.publish(f"key-{i}", msg)

        # Collect received messages
        received_messages: List[Dict[str, Any]] = []

        async def collect_messages() -> None:
            count = 0
            async for msg in backend.consume():
                received_messages.append(msg)
                count += 1
                if count >= len(messages):
                    break

        # Use asyncio.wait_for to avoid hanging if the backend doesn't yield enough
        await asyncio.wait_for(collect_messages(), 2.0)

        # Verify all messages were received
        assert len(received_messages) == len(messages)

        # Verify each message was received exactly once
        for msg in messages:
            assert msg in received_messages

    @pytest.mark.asyncio
    async def test_consumer_group(self, backend: QueueBackend) -> None:
        """Test consuming with a consumer group."""
        # Publish a test message
        test_payload = {"test": "consumer group"}
        await backend.publish("test-group-key", test_payload)

        # Try to consume with a group name
        async def get_with_group() -> Dict[str, Any]:
            async for msg in backend.consume(group="test-group"):
                return msg
            pytest.fail("No message received from consume() with group")

        # Backend may or may not support consumer groups; if it doesn't,
        # it should still work (possibly ignoring the group parameter)
        try:
            received = await asyncio.wait_for(get_with_group(), 2.0)
            assert received == test_payload
        except Exception as e:
            # If the backend doesn't support groups, it should raise a specific
            # exception, not just fail to yield any messages
            if "not supported" not in str(e).lower() and "unsupported" not in str(e).lower():
                raise

    @pytest.mark.asyncio
    async def test_message_ordering(self, backend: QueueBackend) -> None:
        """Test that message ordering is preserved if the backend guarantees it."""
        # Check if this backend guarantees ordering
        # This is implementation-specific, so we'll skip the test if we can't determine it
        try:
            # Memory backend does guarantee ordering
            if isinstance(backend, MemoryBackend):
                preserves_order = True
            else:
                # For other backends, let's assume they might not guarantee order
                # A real implementation would have a way to check this
                preserves_order = hasattr(backend, "preserves_order") and getattr(backend, "preserves_order")
        except (TypeError, AttributeError):
            # If we can't determine, skip the test
            pytest.skip("Cannot determine if backend preserves message order")
            return

        if not preserves_order:
            pytest.skip("This backend does not guarantee message ordering")
            return

        # Publish ordered messages
        messages = [{"order": i} for i in range(5)]
        for i, msg in enumerate(messages):
            await backend.publish("order-test", msg)

        # Collect received messages
        received: List[Dict[str, Any]] = []

        async def collect_ordered_messages() -> None:
            count = 0
            async for msg in backend.consume():
                received.append(msg)
                count += 1
                if count >= len(messages):
                    break

        await asyncio.wait_for(collect_ordered_messages(), 2.0)

        # Verify order
        assert len(received) == len(messages)
        for i, msg in enumerate(received):
            assert msg["order"] == i

    @pytest.mark.asyncio
    async def test_backend_handles_complex_data(self, backend: QueueBackend) -> None:
        """Test that the backend can handle complex nested data structures."""
        # Create a complex nested structure
        complex_data = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "null": None,
            "nested": {"list": [1, 2, 3], "dict": {"a": 1, "b": 2}},
            "list_of_dicts": [{"name": "item1"}, {"name": "item2"}],
        }

        # Publish the complex data
        await backend.publish("complex-data", complex_data)

        # Consume the message
        async def get_complex_message() -> Dict[str, Any]:
            async for msg in backend.consume():
                return msg
            pytest.fail("No message received")

        received = await asyncio.wait_for(get_complex_message(), 2.0)

        # Verify all the data was preserved
        assert received == complex_data

    @pytest.mark.asyncio
    async def test_from_env_creates_valid_instance(self) -> None:
        """Test that from_env creates a valid instance of the backend."""
        # Get the class of the backend being tested
        backend_class = self.create_backend().__class__

        # Call from_env to get an instance
        try:
            instance = backend_class.from_env()
        except Exception as e:
            pytest.fail(f"from_env failed to create instance: {e}")

        # Verify the instance is of the correct type
        assert isinstance(instance, backend_class)

        # Basic functionality test
        test_payload = {"test": "from_env"}
        await instance.publish("from-env-test", test_payload)

        async def get_message() -> Dict[str, Any]:
            async for msg in instance.consume():
                return msg
            pytest.fail("No message received")

        received = await asyncio.wait_for(get_message(), 2.0)
        assert received == test_payload


class TestMemoryBackendContract(QueueBackendContractTest):
    """Contract tests for the MemoryBackend implementation."""

    def create_backend(self) -> MemoryBackend:
        """Create a new MemoryBackend instance for testing."""
        # Reset the class-level queue to ensure tests don't interfere with each other
        MemoryBackend._queue = asyncio.Queue()
        return MemoryBackend()
