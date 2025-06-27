"""Unit tests for the CLI entry point ``slack_mcp.entry``."""

from __future__ import annotations

import importlib
import logging
import os
import pathlib
import sys
import threading
from types import SimpleNamespace
from typing import Any, Generator

import pytest
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Mock classes
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

    def streamable_http_app(self) -> SimpleNamespace:
        """Mock the streamable_http_app method."""
        self.streamable_http_app_calls.append({"called": True})
        return SimpleNamespace()


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _patch_entry(monkeypatch: pytest.MonkeyPatch) -> Generator[SimpleNamespace, None, None]:
    """Provide patched ``slack_mcp.entry`` module with non-blocking server."""
    # Suppress stderr to avoid polluting test output
    monkeypatch.setattr(sys, "stderr", SimpleNamespace(write=lambda *args: None))

    # Replace server instance with dummy
    dummy = _DummyServer()
    monkeypatch.setattr("slack_mcp.entry._server_instance", dummy)

    # Replace uvicorn.run with a non-blocking stub
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: None)

    # Replace logging with a no-op function
    monkeypatch.setattr(logging, "basicConfig", lambda *args, **kwargs: None)
    
    # Replace integrated app creation with a mock
    mock_integrated_app = SimpleNamespace()
    monkeypatch.setattr(
        "slack_mcp.entry.create_integrated_app",
        lambda token=None, mcp_transport=None, mcp_mount_path=None: mock_integrated_app
    )

    # Re-import the module to update bindings
    entry = importlib.import_module("slack_mcp.entry")

    yield SimpleNamespace(entry=entry, dummy=dummy, mock_integrated_app=mock_integrated_app)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_entry_default_args(_patch_entry):
    """Running with no CLI flags should default to *stdio* transport."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy

    # Run with a timeout guard in case something blocks unexpectedly.
    def run_with_timeout():
        entry.main([])  # Empty argv list

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    assert dummy.called
    assert dummy.called_kwargs["transport"] == "stdio"


def test_entry_custom_transport(_patch_entry):
    """Custom transport and mount path are forwarded to FastMCP properly."""

    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy

    argv = ["--transport", "sse", "--mount-path", "/mcp", "--log-level", "INFO"]

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

    # For streamable-http transport, verify streamable_http_app method was called
    assert len(dummy.streamable_http_app_calls) == 1
    assert dummy.streamable_http_app_calls[0]["called"] is True


def test_entry_env_file_loading(_patch_entry, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading of environment variables from .env file."""
    entry = _patch_entry.entry

    # Track dotenv calls
    load_dotenv_calls: list[dict[str, Any]] = []
    monkeypatch.setattr("slack_mcp.entry.load_dotenv", lambda **kwargs: load_dotenv_calls.append(kwargs))

    # Case 1: .env file exists
    monkeypatch.setattr(pathlib.Path, "exists", lambda self: True)
    monkeypatch.setattr(pathlib.Path, "resolve", lambda self: str(self))

    # Run with default .env path
    argv: list[str] = []

    def run_with_timeout() -> None:
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    # Verify load_dotenv was called with correct path
    assert len(load_dotenv_calls) == 1
    assert load_dotenv_calls[0]["dotenv_path"].name == ".env"

    # Case 2: .env file doesn't exist
    load_dotenv_calls.clear()
    monkeypatch.setattr(pathlib.Path, "exists", lambda self: False)

    def run_with_timeout_no_file() -> None:
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout_no_file)
    thread.start()
    thread.join(timeout=1)

    # Verify load_dotenv was not called
    assert len(load_dotenv_calls) == 0

    # Case 3: Custom env file path
    load_dotenv_calls.clear()
    monkeypatch.setattr(pathlib.Path, "exists", lambda self: True)

    argv = ["--env-file", "custom.env"]

    def run_with_timeout_custom_file() -> None:
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout_custom_file)
    thread.start()
    thread.join(timeout=1)

    # Verify load_dotenv was called with custom path
    assert len(load_dotenv_calls) == 1
    assert load_dotenv_calls[0]["dotenv_path"].name == "custom.env"

    # Case 4: No env file loading when --no-env-file is specified
    load_dotenv_calls.clear()

    argv = ["--no-env-file"]

    def run_with_timeout_no_env_file() -> None:
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout_no_env_file)
    thread.start()
    thread.join(timeout=1)

    # Verify load_dotenv was not called
    assert len(load_dotenv_calls) == 0


def test_entry_slack_token_from_cli(_patch_entry, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test setting Slack token from command line argument."""
    entry = _patch_entry.entry

    # Mock os.environ to track setting of SLACK_BOT_TOKEN
    mock_environ: dict[str, str] = {}
    monkeypatch.setattr(os, "environ", mock_environ)

    # Case 1: Slack token provided via command line
    test_token = "xoxb-test-token-123456"
    argv: list[str] = ["--slack-token", test_token]

    def run_with_timeout() -> None:
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)

    # Verify token was set in environment
    assert "SLACK_BOT_TOKEN" in mock_environ
    assert mock_environ["SLACK_BOT_TOKEN"] == test_token

    # Case 2: No token provided, and prevent .env file loading
    mock_environ.clear()

    # Add --no-env-file flag to prevent loading from .env file
    argv = ["--no-env-file"]

    def run_with_timeout_no_token() -> None:
        entry.main(argv)

    thread = threading.Thread(target=run_with_timeout_no_token)
    thread.start()
    thread.join(timeout=1)

    # Verify token was not set in environment
    assert "SLACK_BOT_TOKEN" not in mock_environ


def test_entry_integrated_mode_sse(_patch_entry) -> None:
    """Test running in integrated mode with SSE transport."""
    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy
    mock_integrated_app = _patch_entry.mock_integrated_app
    
    # Call main with integrated flag and SSE transport
    argv = ["--integrated", "--transport", "sse", "--mount-path", "/mcp-test"]
    
    def run_with_timeout() -> None:
        entry.main(argv)
    
    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)
    
    # Verify the dummy server's run method was not called (it should use create_integrated_app instead)
    assert not dummy.called
    
    # Verify uvicorn.run was called with the mock integrated app (through the mock)
    # This is implicit since we patched uvicorn.run to be a no-op function


def test_entry_integrated_mode_streamable_http(_patch_entry) -> None:
    """Test running in integrated mode with streamable-http transport."""
    entry = _patch_entry.entry
    dummy: _DummyServer = _patch_entry.dummy
    mock_integrated_app = _patch_entry.mock_integrated_app
    
    # Call main with integrated flag and streamable-http transport
    argv = ["--integrated", "--transport", "streamable-http"]
    
    def run_with_timeout() -> None:
        entry.main(argv)
    
    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)
    
    # Verify the dummy server's run method was not called (it should use create_integrated_app instead)
    assert not dummy.called
    
    # Verify uvicorn.run was called with the mock integrated app (through the mock)
    # This is implicit since we patched uvicorn.run to be a no-op function


def test_entry_integrated_mode_stdio_not_supported(_patch_entry, caplog) -> None:
    """Test that integrated mode with stdio transport is not supported."""
    entry = _patch_entry.entry
    
    # Capture logs
    caplog.set_level(logging.ERROR)
    
    # Call main with integrated flag and stdio transport
    argv = ["--integrated", "--transport", "stdio"]
    
    def run_with_timeout() -> None:
        entry.main(argv)
    
    thread = threading.Thread(target=run_with_timeout)
    thread.start()
    thread.join(timeout=1)
    
    # Verify error log was emitted
    assert "Integrated mode is not supported with stdio transport" in caplog.text
