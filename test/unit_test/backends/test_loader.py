"""
Unit tests for the backend loader mechanism.

These tests verify that the backend loader correctly handles different scenarios:
- No backends available
- Requested backend found
- Requested backend not found
- Auto-selecting non-memory backend
- Falling back to memory backend
"""

import os
from typing import Any, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from slack_mcp.backends.loader import BACKEND_ENTRY_POINT_GROUP, load_backend
from slack_mcp.backends.queue.memory import MemoryBackend
from slack_mcp.backends.base.protocol import QueueBackend


class MockEntryPoint:
    """Mock EntryPoint class for testing."""

    def __init__(self, name: str, backend_class: Optional[Any] = None):
        self.name = name
        self._backend_class = backend_class or MagicMock(spec=QueueBackend)
        # Ensure the backend class has a from_env method
        if not hasattr(self._backend_class, "from_env"):
            self._backend_class.from_env = MagicMock(return_value=self._backend_class())

    def load(self):
        """Return the mock backend class."""
        return self._backend_class


def create_mock_entry_points(names: List[str]) -> List[MockEntryPoint]:
    """Create a list of mock entry points with the given names."""
    return [MockEntryPoint(name) for name in names]


@pytest.fixture
def reset_env():
    """Reset environment variables before each test."""
    old_env = os.environ.copy()
    # Remove QUEUE_BACKEND if present
    if "QUEUE_BACKEND" in os.environ:
        del os.environ["QUEUE_BACKEND"]
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(old_env)


def test_no_backends_available(reset_env):
    """Test behavior when no backends are registered."""
    with (
        patch("slack_mcp.backends.loader.entry_points", return_value=[]),
        patch("slack_mcp.backends.loader.warnings.warn") as mock_warn,
        patch("slack_mcp.backends.queue.memory.MemoryBackend.from_env", return_value=MemoryBackend()),
    ):

        backend = load_backend()

        # Check that a warning was issued
        mock_warn.assert_called_once()
        assert "No queue backends registered" in mock_warn.call_args[0][0]
        # Check that a MemoryBackend was returned
        assert isinstance(backend, MemoryBackend)


def test_requested_backend_found(reset_env):
    """Test behavior when requested backend is available."""
    # Create mock backend
    mock_redis_backend = MagicMock(spec=QueueBackend)
    mock_redis_backend.from_env.return_value = mock_redis_backend

    # Create mock entry point
    mock_entry_point = MockEntryPoint("redis", mock_redis_backend)

    # Set environment variable
    os.environ["QUEUE_BACKEND"] = "redis"

    with patch("slack_mcp.backends.loader.entry_points", return_value=[mock_entry_point]):
        backend = load_backend()

        # Check that the correct backend was returned
        assert backend is mock_redis_backend
        mock_redis_backend.from_env.assert_called_once()


def test_requested_backend_not_found(reset_env):
    """Test behavior when requested backend is not available."""
    # Create mock entry points without the requested backend
    mock_entry_points = [MockEntryPoint("memory")]

    # Set environment variable to a non-existent backend
    os.environ["QUEUE_BACKEND"] = "nonexistent"

    with patch("slack_mcp.backends.loader.entry_points", return_value=mock_entry_points):
        # Check that RuntimeError is raised with proper message
        with pytest.raises(RuntimeError) as exc_info:
            load_backend()

        # Check that the error message includes installation instructions with emojis
        error_message = str(exc_info.value)
        assert "❌ Unknown backend 'nonexistent'" in error_message
        assert "💡 Try one of the following installation methods:" in error_message
        assert "🔹 by pip:" in error_message
        assert "pip install slack-mcp-mq-nonexistent" in error_message
        assert "🔹 by poetry:" in error_message
        assert "poetry add slack-mcp-mq-nonexistent" in error_message
        assert "🔹 by uv:" in error_message
        assert "uv add slack-mcp-mq-nonexistent" in error_message


def test_auto_select_non_memory_backend(reset_env):
    """Test auto-selection of first non-memory backend."""
    # Create mock entry points
    memory_backend = MagicMock(spec=QueueBackend)
    kafka_backend = MagicMock(spec=QueueBackend)

    # Set up return value for from_env
    memory_backend_instance = MagicMock(spec=QueueBackend)
    kafka_backend_instance = MagicMock(spec=QueueBackend)
    memory_backend.from_env.return_value = memory_backend_instance
    kafka_backend.from_env.return_value = kafka_backend_instance

    mock_entry_points = [MockEntryPoint("memory", memory_backend), MockEntryPoint("kafka", kafka_backend)]

    with patch("slack_mcp.backends.loader.entry_points", return_value=mock_entry_points):
        backend = load_backend()

        # Check that kafka backend was auto-selected
        assert backend is kafka_backend_instance
        kafka_backend.from_env.assert_called_once()
        memory_backend.from_env.assert_not_called()


def test_fallback_to_memory_backend(reset_env):
    """Test fallback to memory backend when only memory backend is available."""
    # Create mock memory backend
    mock_memory_instance = MagicMock(spec=QueueBackend)

    # When only memory backend is available, load_backend() directly uses MemoryBackend.from_env()
    # rather than loading it via the entry point
    with (
        patch("slack_mcp.backends.loader.entry_points") as mock_entry_points,
        patch("slack_mcp.backends.loader.warnings") as mock_warnings,
        patch("slack_mcp.backends.loader.MemoryBackend.from_env", return_value=mock_memory_instance),
    ):

        # Setup entry point that only has memory backend
        mock_ep = MagicMock()
        mock_ep.name = "memory"
        mock_entry_points.return_value = [mock_ep]

        # The loader will build a dict from entry points and use it
        result = load_backend()

        # Verify warning was issued
        mock_warnings.warn.assert_called_with(
            "No external backend found — using MemoryBackend (dev only).", UserWarning
        )

        # Check that the entry point's load method was NOT called
        # This is the correct behavior - the function bypasses loading memory backend via entry point
        mock_ep.load.assert_not_called()

        # Verify we got the expected instance
        assert result is mock_memory_instance


def test_entry_point_group_name():
    """Ensure the entry point group name is correctly defined."""
    assert BACKEND_ENTRY_POINT_GROUP == "slack_mcp.backends.queue"


# Integration of TestBackendLoader tests (converted to pytest style)


def test_legacy_no_backends_available(reset_env):
    """Test loading when no backends are available (legacy test)."""
    # Create a mock memory backend instance to return
    mock_memory_instance = MagicMock(spec=MemoryBackend)

    with (
        patch("slack_mcp.backends.loader.entry_points", return_value=[]),
        patch("slack_mcp.backends.loader.warnings") as mock_warnings,
        patch("slack_mcp.backends.loader.MemoryBackend") as mock_memory_class,
    ):

        # Configure the mock to return our instance
        mock_memory_class.from_env.return_value = mock_memory_instance

        # Call the function under test
        backend = load_backend()

        # Verify warnings
        mock_warnings.warn.assert_any_call(
            "No queue backends registered. Using MemoryBackend (development only).", UserWarning
        )

        # Verify the memory backend was created
        mock_memory_class.from_env.assert_called_once()

        # Verify we got the instance from our mock
        assert backend is mock_memory_instance


def test_legacy_explicit_backend_not_found(reset_env):
    """Test loading an explicit backend that doesn't exist (legacy test)."""
    # Set environment variable for a specific backend
    os.environ["QUEUE_BACKEND"] = "nonexistent"

    # Create a mock memory backend to use
    mock_memory_backend = MagicMock(spec=QueueBackend)
    mock_memory_backend_instance = MagicMock(spec=QueueBackend)
    mock_memory_backend.from_env.return_value = mock_memory_backend_instance

    # Create a mock entry point for the memory backend only
    mock_memory_ep = MagicMock()
    mock_memory_ep.name = "memory"
    mock_memory_ep.load.return_value = mock_memory_backend

    # We need to patch entry_points to return only memory backend
    # Since the requested backend is "nonexistent", this will trigger the error path
    with patch("slack_mcp.backends.loader.entry_points", return_value=[mock_memory_ep]):
        # This should raise a RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            load_backend()

        # Verify error message includes installation instructions
        assert "slack-mcp-mq-nonexistent" in str(exc_info.value)


def test_legacy_load_explicit_backend(reset_env):
    """Test loading an explicitly requested backend (legacy test)."""
    # Set environment variable for a specific backend
    os.environ["QUEUE_BACKEND"] = "redis"

    # Create a mock redis backend
    mock_redis_instance = MagicMock(spec=QueueBackend)
    mock_redis_backend = MagicMock(spec=QueueBackend)
    mock_redis_backend.from_env.return_value = mock_redis_instance

    # Create a mock entry point
    mock_redis_ep = MagicMock()
    mock_redis_ep.name = "redis"
    mock_redis_ep.load.return_value = mock_redis_backend

    with patch("slack_mcp.backends.loader.entry_points", return_value=[mock_redis_ep]):
        # Call load_backend
        result = load_backend()

        # Verify the correct backend was loaded
        mock_redis_ep.load.assert_called_once()
        mock_redis_backend.from_env.assert_called_once()
        assert result is mock_redis_instance


def test_legacy_auto_select_non_memory(reset_env):
    """Test auto-selection of first non-memory backend (legacy test)."""
    # Create mock backends
    mock_memory_instance = MagicMock(spec=QueueBackend)
    mock_memory_backend = MagicMock(spec=QueueBackend)
    mock_memory_backend.from_env.return_value = mock_memory_instance

    mock_kafka_instance = MagicMock(spec=QueueBackend)
    mock_kafka_backend = MagicMock(spec=QueueBackend)
    mock_kafka_backend.from_env.return_value = mock_kafka_instance

    # Create mock entry points
    memory_ep = MagicMock()
    memory_ep.name = "memory"
    memory_ep.load.return_value = mock_memory_backend

    kafka_ep = MagicMock()
    kafka_ep.name = "kafka"
    kafka_ep.load.return_value = mock_kafka_backend

    with patch("slack_mcp.backends.loader.entry_points", return_value=[memory_ep, kafka_ep]):
        # Call load_backend
        result = load_backend()

        # Verify the kafka backend was loaded
        kafka_ep.load.assert_called_once()
        mock_kafka_backend.from_env.assert_called_once()
        assert result is mock_kafka_instance


def test_legacy_fallback_to_memory(reset_env):
    """Test fallback to memory backend when only memory is available (legacy test)."""
    # Create a mock instance for the MemoryBackend.from_env() to return
    mock_memory_instance = MagicMock(spec=QueueBackend)

    # Setup our mocks with the correct expectations
    with (
        patch("slack_mcp.backends.loader.entry_points") as mock_entry_points,
        patch("slack_mcp.backends.loader.warnings") as mock_warnings,
        patch("slack_mcp.backends.loader.MemoryBackend.from_env", return_value=mock_memory_instance),
    ):

        # Setup mock entry point that only has memory backend
        mock_ep = MagicMock()
        mock_ep.name = "memory"
        mock_entry_points.return_value = [mock_ep]

        # Call the function under test
        result = load_backend()

        # Verify warning was issued
        mock_warnings.warn.assert_called_with(
            "No external backend found — using MemoryBackend (dev only).", UserWarning
        )

        # In this case, the loader directly uses MemoryBackend.from_env()
        # and does NOT load through the entry point
        mock_ep.load.assert_not_called()

        # Verify we got our mock instance
        assert result is mock_memory_instance
