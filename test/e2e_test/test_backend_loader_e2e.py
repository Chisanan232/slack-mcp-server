"""
End-to-end tests for the backend loader functionality.

These tests verify the backend loader behavior in a real environment,
focusing on error messages and behavior that can be reliably tested.
"""

import os
import warnings

import pytest

# Import the components to test
from slack_mcp.backends.loader import load_backend
from slack_mcp.backends.memory import MemoryBackend


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


def test_memory_backend_fallback_e2e(reset_env):
    """Test fallback to memory backend when no plugins are specified."""
    # Reset the environment and ensure no backend is specified
    if "QUEUE_BACKEND" in os.environ:
        del os.environ["QUEUE_BACKEND"]

    # In a real environment, we'll get the memory backend as the fallback
    # when no specific backend is requested
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        backend = load_backend()

        # Verify that we got a memory backend
        assert isinstance(backend, MemoryBackend)

        # Check that at least one warning was issued (either "no backends registered"
        # or "no external backend found")
        assert len(w) >= 1
        warning_texts = [str(warning.message) for warning in w]
        assert any(("No queue backends" in text) or ("No external backend found" in text) for text in warning_texts)


def test_nonexistent_backend_error_message_e2e(reset_env):
    """
    Test the behavior when a non-existent backend is requested.

    This test sets the QUEUE_BACKEND environment variable to a name that's unlikely to exist,
    then checks either for:
    1. A RuntimeError with properly formatted error message, OR
    2. A fallback to MemoryBackend with appropriate warning
    """
    # Request a backend that's unlikely to exist
    os.environ["QUEUE_BACKEND"] = "this_backend_definitely_does_not_exist_xyz123"

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        try:
            backend = load_backend()

            # If we get here, the loader fell back to a default backend
            # Verify it's a MemoryBackend and that a warning was issued
            assert isinstance(backend, MemoryBackend), "When unknown backend is requested, should use MemoryBackend"

            # Check that warnings were issued
            warning_texts = [str(warning.message) for warning in w]
            assert any(
                "Unknown backend" in text
                or "No queue backends registered" in text
                or "No external backend found" in text
                for text in warning_texts
            ), "Should issue warning about unknown/unavailable backend"

        except RuntimeError as e:
            # If the loader raises an error (the other valid behavior),
            # check that the error message is properly formatted
            error_msg = str(e)

            # Check that the error message contains the expected elements
            assert "❌" in error_msg, "Error message should contain the error emoji"
            assert "Unknown backend 'this_backend_definitely_does_not_exist_xyz123'" in error_msg
            assert "💡 Try one of the following installation methods:" in error_msg
            assert "🔹 by pip:" in error_msg
            assert "pip install slack-mcp-mq-this_backend_definitely_does_not_exist_xyz123" in error_msg
            assert "🔹 by poetry:" in error_msg
            assert "poetry add slack-mcp-mq-this_backend_definitely_does_not_exist_xyz123" in error_msg
            assert "🔹 by uv:" in error_msg
            assert "uv add slack-mcp-mq-this_backend_definitely_does_not_exist_xyz123" in error_msg


def test_existing_backend_loaded_correctly(reset_env):
    """
    Test that the memory backend is loaded correctly when specifically requested.

    This test sets QUEUE_BACKEND to 'memory' which should always be available.
    """
    # Request the memory backend which should always be available
    os.environ["QUEUE_BACKEND"] = "memory"

    # Load the backend and verify it's a memory backend
    backend = load_backend()
    assert isinstance(backend, MemoryBackend)
