"""Unit tests for the CLI entry point ``slack_mcp.entry``."""

from __future__ import annotations

import importlib
import threading
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


class _DummyServer(FastMCP):  # pragma: no cover – trivial stub
    """Subclass of :class:`FastMCP` capturing ``run`` invocations."""

    def __init__(self) -> None:
        super().__init__(name="Dummy")
        self.called: bool = False
        self.called_args: tuple[Any, ...] = ()
        self.called_kwargs: dict[str, Any] = {}
        
        # Track calls to app methods
        self.sse_app_calls: list[dict[str, Any]] = []
        self.streamable_http_app_calls: list[dict[str, Any]] = []

    def run(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 – override
        """Capture run method calls with parameters."""
        self.called = True
        self.called_args = args
        self.called_kwargs = kwargs
        
    def sse_app(self, mount_path: str | None = None) -> SimpleNamespace:
        """Mock the sse_app method."""
        self.sse_app_calls.append({"mount_path": mount_path})
        return SimpleNamespace()
    
    def streamable_http_app(self, mount_path: str | None = None) -> SimpleNamespace:
        """Mock the streamable_http_app method."""
        self.streamable_http_app_calls.append({"mount_path": mount_path})
        return SimpleNamespace()


@pytest.fixture()
def _patch_entry(monkeypatch: pytest.MonkeyPatch):  # noqa: D401 – fixture
    """Provide patched ``slack_mcp.entry`` module with non-blocking server."""

    # Fresh reload to reset module state.
    entry = importlib.reload(importlib.import_module("slack_mcp.entry"))

    dummy_server = _DummyServer()

    # Patch server instance and bypass logging setup **after** reload.
    monkeypatch.setattr(entry, "_server_instance", dummy_server, raising=True)
    monkeypatch.setattr(entry.logging, "basicConfig", lambda *a, **k: None, raising=True)
    
    # Patch uvicorn.run to prevent actual server startup
    monkeypatch.setattr(entry.uvicorn, "run", lambda *a, **k: None, raising=True)

    return SimpleNamespace(entry=entry, dummy=dummy_server)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_entry_default_args(_patch_entry):
    """Running with no CLI flags should default to *stdio* transport."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy

    # Run with a timeout guard in case something blocks unexpectedly.
    def run_with_timeout():
        entry.main([])

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    assert dummy.called is True
    assert dummy.called_kwargs == {"transport": "stdio"}


def test_entry_custom_transport(_patch_entry):
    """Custom transport and mount path are forwarded to FastMCP properly."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy

    argv = ["--transport", "sse", "--mount-path", "/mcp", "--log-level", "DEBUG"]

    # Run with a timeout guard in case something blocks unexpectedly.
    def run_with_timeout():
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    # For SSE transport, verify sse_app method was called with correct mount path
    assert len(dummy.sse_app_calls) == 1
    assert dummy.sse_app_calls[0]["mount_path"] == "/mcp"
    
    
def test_entry_streamable_http_transport(_patch_entry):
    """Streamable HTTP transport uses the streamable_http_app method."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy

    argv = ["--transport", "streamable-http", "--mount-path", "/api", "--log-level", "INFO"]

    # Run with a timeout guard in case something blocks unexpectedly.
    def run_with_timeout():
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    # For streamable-http transport, verify streamable_http_app method was called with correct mount path
    assert len(dummy.streamable_http_app_calls) == 1
    assert dummy.streamable_http_app_calls[0]["mount_path"] == "/api"
