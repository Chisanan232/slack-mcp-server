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
import re
import warnings
from importlib.metadata import EntryPoint
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

import pytest

from slack_mcp.backends.loader import load_backend, BACKEND_ENTRY_POINT_GROUP
from slack_mcp.backends.memory import MemoryBackend
from slack_mcp.backends.protocol import QueueBackend


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
    with patch('slack_mcp.backends.loader.entry_points', return_value=[]), \
         patch('slack_mcp.backends.loader.warnings.warn') as mock_warn, \
         patch('slack_mcp.backends.memory.MemoryBackend.from_env', return_value=MemoryBackend()):
        
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
    
    with patch('slack_mcp.backends.loader.entry_points', return_value=[mock_entry_point]):
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
    
    with patch('slack_mcp.backends.loader.entry_points', return_value=mock_entry_points):
        with pytest.raises(RuntimeError) as excinfo:
            load_backend()
        
        # Check error message format
        error_msg = str(excinfo.value)
        assert "❌ Unknown backend 'nonexistent'" in error_msg
        assert "💡 Try one of the following installation methods:" in error_msg
        assert "🔹 by pip:" in error_msg
        assert "pip install slack-mcp-mq-nonexistent" in error_msg
        assert "🔹 by poetry:" in error_msg
        assert "poetry add slack-mcp-mq-nonexistent" in error_msg
        assert "🔹 by uv:" in error_msg
        assert "uv add slack-mcp-mq-nonexistent" in error_msg


def test_auto_select_non_memory_backend(reset_env):
    """Test auto-selection of first non-memory backend."""
    # Create mock backends
    mock_memory_backend = MagicMock(spec=MemoryBackend)
    mock_redis_backend = MagicMock(spec=QueueBackend)
    
    mock_memory_backend.from_env.return_value = mock_memory_backend
    mock_redis_backend.from_env.return_value = mock_redis_backend
    
    # Create mock entry points with memory and redis backends
    mock_entry_points = [
        MockEntryPoint("memory", mock_memory_backend),
        MockEntryPoint("redis", mock_redis_backend)
    ]
    
    # No specific backend requested
    with patch('slack_mcp.backends.loader.entry_points', return_value=mock_entry_points):
        backend = load_backend()
        
        # Check that the redis backend was selected
        assert backend is mock_redis_backend
        mock_redis_backend.from_env.assert_called_once()
        # Memory backend should not have been used
        mock_memory_backend.from_env.assert_not_called()


def test_fallback_to_memory_backend(reset_env):
    """Test fallback to memory backend when only memory backend is available."""
    # Create mock memory backend
    mock_memory_backend = MockEntryPoint("memory")
    
    with patch('slack_mcp.backends.loader.entry_points', return_value=[mock_memory_backend]), \
         patch('slack_mcp.backends.loader.warnings.warn') as mock_warn, \
         patch('slack_mcp.backends.memory.MemoryBackend.from_env', return_value=MemoryBackend()):
        
        backend = load_backend()
        
        # Check that a warning was issued
        mock_warn.assert_called_once()
        assert "No external backend found" in mock_warn.call_args[0][0]
        # Check that a MemoryBackend was returned
        assert isinstance(backend, MemoryBackend)


def test_entry_point_group_name():
    """Ensure the entry point group name is correctly defined."""
    assert BACKEND_ENTRY_POINT_GROUP == "slack_mcp.queue_backends"
