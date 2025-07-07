"""
Queue backend loading mechanism.

This module handles discovery and loading of queue backends from entry points.
"""

import os
import warnings
from importlib.metadata import entry_points

from slack_mcp.backends.base.protocol import QueueBackend
from slack_mcp.backends.queue.memory import MemoryBackend

# Entry point group name for queue backends
BACKEND_ENTRY_POINT_GROUP = "slack_mcp.backends.queue"


def load_backend() -> QueueBackend:
    """Load a queue backend based on configuration or available plugins.

    The selection process follows these steps:
    1. Use the backend specified by QUEUE_BACKEND environment variable if set
    2. If no backend is specified, auto-select the first non-memory plugin
    3. If no plugins are found, fall back to MemoryBackend with a warning

    Returns:
        An instance of a QueueBackend implementation

    Raises:
        RuntimeError: If the requested backend isn't found and can't be installed
    """
    # Check if a specific backend is requested
    requested_backend = os.getenv("QUEUE_BACKEND")

    # Get all available backends from entry points
    backends = entry_points(group=BACKEND_ENTRY_POINT_GROUP)

    if not backends:
        warnings.warn("No queue backends registered. Using MemoryBackend (development only).", UserWarning)
        return MemoryBackend.from_env()

    # Convert entry points to a dict for easier lookup
    backend_dict = {ep.name: ep for ep in backends}

    if requested_backend:
        # User explicitly requested a backend
        if requested_backend in backend_dict:
            # Load the requested backend
            backend_class = backend_dict[requested_backend].load()
            return backend_class.from_env()
        else:
            # Backend not found, suggest installation
            raise RuntimeError(
                f"❌ Unknown backend '{requested_backend}'. \n"
                f"💡 Try one of the following installation methods: \n"
                f"🔹 by pip:    pip install slack-mcp-mq-{requested_backend}\n"
                f"🔹 by poetry: poetry add slack-mcp-mq-{requested_backend}\n"
                f"🔹 by uv:     uv add slack-mcp-mq-{requested_backend}"
            )

    # Auto-select the first non-memory backend if available
    for name, ep in backend_dict.items():
        if name != "memory":
            backend_class = ep.load()
            return backend_class.from_env()

    # Fall back to memory backend
    warnings.warn("No external backend found — using MemoryBackend (dev only).", UserWarning)
    return MemoryBackend.from_env()
