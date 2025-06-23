"""Test that Slack MCP server starts up successfully with SSE transport."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

pytestmark = pytest.mark.asyncio

# Set up logging for better diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sse_startup_test")


class _DummyServer:
    """Mock FastMCP server for testing."""
    
    def __init__(self):
        """Initialize with dummy attributes for testing."""
        self.run_called = False
        self.run_transport = None
        self.sse_app_called = False
        self.sse_mount_path = None
        self.streamable_http_app_called = False
        self.streamable_http_mount_path = None
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
    
    def streamable_http_app(self, mount_path=None):
        """Return a dummy app for streamable HTTP transport."""
        self.streamable_http_app_called = True
        self.streamable_http_mount_path = mount_path
        return self._app


@pytest.mark.parametrize(
    "transport,mount_path", 
    [
        ("sse", "/mcp-sse"),
        ("streamable-http", "/mcp-http")
    ]
)
async def test_server_http_transports(transport, mount_path):
    """Test that the server uses the correct transport methods."""
    from slack_mcp import entry
    
    mock_server = _DummyServer()
    
    # Create dummy args
    argv = [
        "--transport", transport,
        "--mount-path", mount_path,
        "--host", "localhost",
        "--port", "8000",
        "--log-level", "INFO"
    ]
    
    with patch("slack_mcp.entry._server_instance", mock_server), \
         patch("uvicorn.run") as mock_uvicorn_run:
        
        # Run the main entry point
        entry.main(argv)
        
        if transport == "sse":
            # For SSE transport, check that sse_app was called with correct mount path
            assert mock_server.sse_app_called
            assert mock_server.sse_mount_path == mount_path
            assert not mock_server.streamable_http_app_called
            mock_uvicorn_run.assert_called_once()
            
        elif transport == "streamable-http":
            # For streamable-http transport, check that streamable_http_app was called with correct mount path
            assert mock_server.streamable_http_app_called
            assert mock_server.streamable_http_mount_path == mount_path
            assert not mock_server.sse_app_called
            mock_uvicorn_run.assert_called_once()
        
        # Make sure run was not called for HTTP transports
        assert not mock_server.run_called
        
        logger.info(f"Test passed for {transport} transport with mount path {mount_path}")


async def test_server_stdio_transport():
    """Test that the server runs correctly for stdio transport."""
    from slack_mcp import entry
    
    mock_server = _DummyServer()
    
    # Create dummy args with stdio transport
    argv = [
        "--transport", "stdio",
        "--log-level", "INFO"
    ]
    
    with patch("slack_mcp.entry._server_instance", mock_server):
        # Run the main entry point
        entry.main(argv)
        
        # For stdio transport, check that run was called
        assert mock_server.run_called
        assert mock_server.run_transport == "stdio"
        assert not mock_server.sse_app_called
        assert not mock_server.streamable_http_app_called
        
        logger.info("Test passed for stdio transport")
