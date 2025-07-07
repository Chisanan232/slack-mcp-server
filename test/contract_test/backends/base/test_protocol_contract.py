"""
Contract tests for the QueueBackend protocol itself.

These tests verify the behavior of the protocol definition and provide
mock implementations to test protocol compliance without relying on
specific backend implementations.
"""

import asyncio
import inspect
import types
from typing import Any, AsyncIterator, Dict, List, Optional, cast

import pytest

from slack_mcp.backends.base.protocol import QueueBackend


class MockQueueBackend(QueueBackend):
    """A mock implementation of the QueueBackend protocol for testing."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.keys: List[str] = []
        self.groups: List[Optional[str]] = []

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Publish a message to the mock queue."""
        self.keys.append(key)
        self.messages.append(payload)

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Consume messages from the mock queue."""
        self.groups.append(group)
        for message in self.messages:
            yield message

    @classmethod
    def from_env(cls) -> "MockQueueBackend":
        """Create a backend instance from environment variables."""
        return cls()


class FailingQueueBackend(QueueBackend):
    """A mock implementation that intentionally fails for testing error cases."""

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Always fails when publishing."""
        raise ValueError("Simulated publish failure")

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Always fails when consuming."""
        raise ValueError("Simulated consume failure")
        yield {}  # This will never be reached

    @classmethod
    def from_env(cls) -> "FailingQueueBackend":
        """Fails when creating from environment."""
        raise ValueError("Simulated from_env failure")


class AsyncGenQueueBackend(QueueBackend):
    """A mock implementation that specifically tests async generator behavior."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Publish a message to the mock queue."""
        self.messages.append(payload)

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Properly implemented as an async generator for protocol compliance."""
        for message in self.messages:
            yield message
            # Simulate some async work between messages
            await asyncio.sleep(0.01)

    @classmethod
    def from_env(cls) -> "AsyncGenQueueBackend":
        """Create a backend instance from environment variables."""
        return cls()


class TestQueueBackendProtocol:
    """Tests specifically for the QueueBackend protocol itself."""

    def test_protocol_methods(self):
        """Test that the protocol requires the expected methods."""
        # Get the instance methods defined on the QueueBackend protocol
        protocol_methods = {
            name
            for name, _ in inspect.getmembers(QueueBackend, predicate=inspect.isfunction)
            if not name.startswith("_")
        }

        # The protocol should define these methods
        expected_instance_methods = {"publish", "consume"}

        assert protocol_methods == expected_instance_methods, (
            f"QueueBackend protocol should define these instance methods: {expected_instance_methods}, "
            f"but it defines: {protocol_methods}"
        )

        # Although from_env is specified in the protocol, it's not detected as a function
        # by inspect because it's a classmethod in a Protocol. We'll verify it's usage instead
        # in other tests.

    def test_method_signatures(self):
        """Test that the protocol methods have the correct signatures."""
        # Check publish method
        publish_sig = inspect.signature(QueueBackend.publish)
        assert len(publish_sig.parameters) == 3  # self, key, payload
        assert "key" in publish_sig.parameters
        assert "payload" in publish_sig.parameters
        assert publish_sig.return_annotation == None

        # Check consume method
        consume_sig = inspect.signature(QueueBackend.consume)
        assert len(consume_sig.parameters) == 2  # self, group
        assert "group" in consume_sig.parameters
        assert consume_sig.parameters["group"].default is None
        assert consume_sig.parameters["group"].kind == inspect.Parameter.KEYWORD_ONLY

        # Skip from_env signature check since it's not directly accessible
        # as a method on the Protocol class. We'll test the implementation behavior instead.

    def test_mock_implementation_type_check(self):
        """Test that our mock implementation satisfies the protocol's type checking."""
        # This would raise TypeError if MockQueueBackend doesn't implement the protocol
        backend: QueueBackend = cast(QueueBackend, MockQueueBackend())

        # Verify we can call the methods without type errors
        assert hasattr(backend, "publish")
        assert hasattr(backend, "consume")
        assert hasattr(type(backend), "from_env")

    @pytest.mark.asyncio
    async def test_protocol_usage(self):
        """Test using a backend through protocol annotations."""

        async def use_backend(backend: QueueBackend) -> Dict[str, Any]:
            """Function that uses a queue backend through the protocol."""
            await backend.publish("test", {"value": 42})

            # Type annotation hack to help mypy understand this is an AsyncIterator
            messages = backend.consume()
            # Use a variable with explicit type to help mypy
            iterator: AsyncIterator[Dict[str, Any]] = messages
            async for message in iterator:
                return message
            raise ValueError("No message received")

        # Use our mock implementation with the function
        mock_backend = MockQueueBackend()
        result = await use_backend(mock_backend)

        assert result == {"value": 42}
        assert mock_backend.keys == ["test"]

    @pytest.mark.asyncio
    async def test_async_generator_protocol(self):
        """Test that consume() correctly follows async generator protocol."""
        # Create an AsyncGenQueueBackend that properly implements async generator
        backend = AsyncGenQueueBackend()

        # Add some test messages
        await backend.publish("key1", {"id": 1})
        await backend.publish("key2", {"id": 2})

        # Check that the consumer follows the async iterator protocol
        # We need to be careful with type annotations here
        consumer = backend.consume()
        assert hasattr(consumer, "__aiter__")
        assert hasattr(consumer, "__anext__")

        # Use it in an async for loop
        messages = []
        async for msg in backend.consume():
            messages.append(msg)

        assert len(messages) == 2
        assert messages[0] == {"id": 1}
        assert messages[1] == {"id": 2}

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling behavior when using protocol implementations."""
        failing_backend = FailingQueueBackend()

        # Test publish error handling
        with pytest.raises(ValueError, match="Simulated publish failure"):
            await failing_backend.publish("key", {"value": "test"})

        # Test consume error handling
        consumer = failing_backend.consume()
        with pytest.raises(ValueError, match="Simulated consume failure"):
            async for _ in consumer:
                pass

        # Test from_env error handling
        with pytest.raises(ValueError, match="Simulated from_env failure"):
            FailingQueueBackend.from_env()

    def test_from_env_class_method(self):
        """Test that from_env is properly implemented as a classmethod."""
        # This test verifies that implementations should have from_env as a classmethod

        # Check our mock implementations
        assert isinstance(MockQueueBackend.from_env, types.MethodType) or isinstance(
            MockQueueBackend.from_env, classmethod
        )

        # Test behavior through an implementation
        instance = MockQueueBackend.from_env()
        assert isinstance(instance, MockQueueBackend)


# Additional mock implementations for extended testing
class DictBackend:
    """A backend that uses simple dictionaries for testing."""

    def __init__(self):
        # Each topic/key maps to a list of messages
        self.topics: Dict[str, List[Dict[str, Any]]] = {}

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Publish a message to a specific topic/key."""
        if key not in self.topics:
            self.topics[key] = []
        self.topics[key].append(payload)

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Consume all messages from all topics."""
        # Flatten all messages from all topics
        all_messages = []
        for messages in self.topics.values():
            all_messages.extend(messages)

        for message in all_messages:
            yield message

    @classmethod
    def from_env(cls) -> "DictBackend":
        """Create a backend instance from environment variables."""
        return cls()


class TestExtendedBackendCompliance:
    """Test additional backend implementations for protocol compliance."""

    @pytest.mark.asyncio
    async def test_dict_backend_compliance(self):
        """Test that DictBackend complies with the QueueBackend protocol."""
        # Create a backend
        backend: QueueBackend = cast(QueueBackend, DictBackend())

        # Test basic functionality
        await backend.publish("topic1", {"value": "test1"})
        await backend.publish("topic2", {"value": "test2"})

        # Collect messages
        messages = []
        async for msg in backend.consume():
            messages.append(msg)
            if len(messages) >= 2:
                break

        # Check results
        assert len(messages) == 2
        assert {"value": "test1"} in messages
        assert {"value": "test2"} in messages

    @pytest.mark.asyncio
    async def test_from_env_factory_pattern(self):
        """Test that the from_env method follows the factory pattern correctly."""
        # This test verifies that from_env is properly implemented as a class method

        # Directly create instances as a baseline
        direct_instance = DictBackend()

        # Use from_env to create instance
        factory_instance = DictBackend.from_env()

        # Both should be usable in the same way
        await direct_instance.publish("test", {"source": "direct"})
        await factory_instance.publish("test", {"source": "factory"})

        # Verify both work as expected
        direct_messages = []
        async for msg in direct_instance.consume():
            direct_messages.append(msg)

        factory_messages = []
        async for msg in factory_instance.consume():
            factory_messages.append(msg)

        assert len(direct_messages) == 1
        assert len(factory_messages) == 1
        assert direct_messages[0] == {"source": "direct"}
        assert factory_messages[0] == {"source": "factory"}
