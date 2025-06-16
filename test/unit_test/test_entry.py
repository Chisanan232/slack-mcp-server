"""Unit tests for the CLI entry point ``slack_mcp.entry``."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Final

import importlib
import sys
import pytest
import threading

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

    def run(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 – override
        self.called = True
        self.called_args = args
        self.called_kwargs = kwargs


@pytest.fixture()
def _patch_entry(monkeypatch: pytest.MonkeyPatch):  # noqa: D401 – fixture
    """Provide patched ``slack_mcp.entry`` module with non-blocking server."""

    # Fresh reload to reset module state.
    entry = importlib.reload(importlib.import_module("slack_mcp.entry"))

    dummy_server = _DummyServer()

    # Patch server instance and bypass logging setup **after** reload.
    monkeypatch.setattr(entry, "_server_instance", dummy_server, raising=True)
    monkeypatch.setattr(entry.logging, "basicConfig", lambda *a, **k: None, raising=True)

    return SimpleNamespace(entry=entry, dummy=dummy_server)

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_entry_default_args(_patch_entry):
    """Running with no CLI flags should default to *stdio* transport."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy  # type: ignore[attr-defined]

    # Run with a timeout guard in case something blocks unexpectedly.
    def run_with_timeout():
        entry.main([])

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    assert dummy.called is True
    assert dummy.called_kwargs == {"transport": "stdio", "mount_path": None}


def test_entry_custom_transport(_patch_entry):
    """Custom transport and mount path are forwarded to ``FastMCP.run``."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy  # type: ignore[attr-defined]

    argv = ["--transport", "sse", "--mount-path", "/mcp", "--log-level", "DEBUG"]

    # Run with a timeout guard in case something blocks unexpectedly.
    def run_with_timeout():
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    assert dummy.called is True
    assert dummy.called_kwargs == {"transport": "sse", "mount_path": "/mcp"}
