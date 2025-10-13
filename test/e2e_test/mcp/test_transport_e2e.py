"""Test that Slack MCP server starts up successfully with different transports."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi import FastAPI

pytestmark = pytest.mark.asyncio

# Set up logging for better diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _DummyServer:
    """Mock FastMCP server for testing."""

    def __init__(self):
        """Initialize with dummy attributes for testing."""
        self.run_called = False
        self.run_transport = None
        self.sse_app_called = False
        self.sse_mount_path = None
        self.streamable_http_app_called = False
        self._app = FastAPI()

    def run(self, transport="stdio", **kwargs):
        """Record run calls."""
        self.run_called = True
        self.run_transport = transport
        return None

    def sse_app(self, mount_path=None):
        """Return a dummy app for SSE transport."""
        self.sse_app_called = True
        self.sse_mount_path = mount_path
        return self._app

    def streamable_http_app(self):
        """Return a dummy app for streamable HTTP transport.

        Note: Unlike sse_app, this method doesn't accept mount_path parameter
        in the actual FastMCP implementation.
        """
        self.streamable_http_app_called = True
        return self._app


@pytest.mark.parametrize(
    "transport,mount_path,warning_expected",
    [("sse", "/mcp-sse", False), ("streamable-http", "/mcp-http", True), ("streamable-http", None, False)],
)
async def test_server_http_transports(transport, mount_path, warning_expected, caplog):
    """Test that the server uses the correct transport methods."""
    from slack_mcp.mcp import entry

    mock_server = _DummyServer()

    # Create dummy args
    argv = ["--transport", transport, "--host", "localhost", "--port", "8000", "--log-level", "info"]

    # Add mount path if specified
    if mount_path:
        argv.extend(["--mount-path", mount_path])

    # Reset singleton factory for clean test state
    from slack_mcp.mcp.app import MCPServerFactory

    MCPServerFactory.reset()

    with (
        patch("slack_mcp.mcp.app.mcp_factory.get", return_value=mock_server),
        patch("slack_mcp.mcp.entry.mcp_factory.get", return_value=mock_server),
        patch("slack_mcp.mcp.entry.setup_logging_from_args"),
        patch("uvicorn.run") as mock_uvicorn_run,
    ):

        # Run the main entry point
        entry.main(argv)

        if transport == "sse":
            # For SSE transport, check that sse_app was called with correct mount path
            assert mock_server.sse_app_called
            assert mock_server.sse_mount_path == mount_path
            assert not mock_server.streamable_http_app_called
            mock_uvicorn_run.assert_called_once()

        elif transport == "streamable-http":
            # For streamable-http transport, check that streamable_http_app was called
            # (but not with mount_path as parameter since the method doesn't accept it)
            assert mock_server.streamable_http_app_called
            assert not mock_server.sse_app_called
            mock_uvicorn_run.assert_called_once()

            # Check for warning log if mount_path is provided with streamable-http
            if warning_expected:
                assert any(
                    "mount-path is not supported for streamable-http transport" in record.message
                    for record in caplog.records
                )

        # Make sure run was not called for HTTP transports
        assert not mock_server.run_called

        logger.info(f"Test passed for {transport} transport with mount path {mount_path}")


async def test_server_stdio_transport():
    """Test that the server runs correctly for stdio transport."""
    from slack_mcp.mcp import entry

    mock_server = _DummyServer()

    # Create dummy args with stdio transport
    argv = ["--transport", "stdio", "--log-level", "info"]

    # Reset singleton factory for clean test state
    from slack_mcp.mcp.app import MCPServerFactory

    MCPServerFactory.reset()

    with (
        patch("slack_mcp.mcp.app.mcp_factory.get", return_value=mock_server),
        patch("slack_mcp.mcp.entry.mcp_factory.get", return_value=mock_server),
        patch("slack_mcp.mcp.entry.setup_logging_from_args"),
    ):
        # Run the main entry point
        entry.main(argv)

        # For stdio transport, check that run was called
        assert mock_server.run_called
        assert mock_server.run_transport == "stdio"
        assert not mock_server.sse_app_called
        assert not mock_server.streamable_http_app_called

        logger.info("Test passed for stdio transport")
