"""Utility functions for HTTP-based MCP E2E tests (SSE and Streamable-HTTP transports)."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Any

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger("http_test_utils")


class HttpServerManager:
    """Manages HTTP-based MCP server instances for E2E testing."""
    
    def __init__(
        self, 
        transport: str, 
        integrated: bool = False, 
        host: str = "127.0.0.1", 
        port: int = 8000,
        mount_path: str | None = None
    ):
        self.transport = transport
        self.integrated = integrated
        self.host = host
        self.port = port
        self.mount_path = mount_path
        self.process: subprocess.Popen | None = None
        self.base_url = f"http://{host}:{port}"
        
    async def start_server(self, env: dict[str, str] | None = None) -> None:
        """Start the MCP server process."""
        # Build command arguments
        args = [sys.executable, "-m", "slack_mcp.mcp.entry"]
        args.extend(["--transport", self.transport])
        args.extend(["--host", self.host])
        args.extend(["--port", str(self.port)])
        
        if self.mount_path:
            args.extend(["--mount-path", self.mount_path])
            
        if self.integrated:
            args.append("--integrated")
            # Pass Slack token for integrated mode
            slack_token = os.getenv("SLACK_BOT_TOKEN")
            if slack_token:
                args.extend(["--slack-token", slack_token])
            
        logger.info(f"Starting MCP server with args: {args}")
        
        # Prepare environment
        server_env = {**os.environ}
        if env:
            server_env.update(env)
            
        # Start server process
        self.process = subprocess.Popen(
            args,
            env=server_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to be ready
        await self._wait_for_server_ready()
        
    async def _wait_for_server_ready(self, timeout: int = 30) -> None:
        """Wait for the server to be ready to accept connections."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to connect to the health endpoint or base URL
                health_url = f"{self.base_url}/health" if self.integrated else self.base_url
                async with httpx.AsyncClient() as client:
                    response = await client.get(health_url, timeout=5.0)
                    if response.status_code in [200, 404]:  # 404 is ok for non-health endpoints
                        logger.info(f"Server is ready at {self.base_url}")
                        return
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(0.5)
                continue
                
        raise RuntimeError(f"Server failed to start within {timeout} seconds")
        
    async def stop_server(self) -> None:
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            logger.info("Server stopped")


@asynccontextmanager
async def http_mcp_server(
    transport: str,
    integrated: bool = False,
    host: str = "127.0.0.1", 
    port: int = 8000,
    mount_path: str | None = None,
    env: dict[str, str] | None = None
) -> AsyncGenerator[HttpServerManager, None]:
    """Context manager for HTTP-based MCP server instances."""
    server = HttpServerManager(transport, integrated, host, port, mount_path)
    try:
        await server.start_server(env)
        yield server
    finally:
        await server.stop_server()


@asynccontextmanager
async def http_mcp_client_session(
    transport: str,
    base_url: str,
    mount_path: str | None = None,
    integrated: bool = False
) -> AsyncGenerator[ClientSession, None]:
    """Create MCP client session for HTTP transports."""
    if transport == "sse":
        # SSE transport
        # In integrated mode, use mount_path; in standalone mode, connect to /sse endpoint
        if integrated and mount_path:
            mcp_url = f"{base_url}{mount_path}/sse"
        else:
            mcp_url = f"{base_url}/sse"
        logger.info(f"Connecting SSE client to: {mcp_url}")
        async with sse_client(mcp_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                yield session
    elif transport == "streamable-http":
        # Streamable HTTP transport URL patterns based on working client example
        if integrated and mount_path:
            # In integrated mode, use mount_path + /mcp (e.g., /mcp/mcp)
            mcp_url = f"{base_url}{mount_path}/mcp"
        else:
            # In standalone mode, connect to /mcp endpoint
            mcp_url = f"{base_url}/mcp"
        logger.info(f"Connecting Streamable-HTTP client to: {mcp_url}")
        async with streamablehttp_client(mcp_url) as (read_stream, write_stream, _close_fn):
            async with ClientSession(read_stream, write_stream) as session:
                yield session
    else:
        raise ValueError(f"Unsupported HTTP transport: {transport}")


async def initialize_and_test_tools(session: ClientSession, expected_tools: list[str]) -> list[str]:
    """Initialize MCP session and verify expected tools are available."""
    # Initialize the session
    logger.info("Initializing MCP session...")
    init_result = await session.initialize()
    logger.info(f"Initialization successful: {init_result}")
    
    # Wait a moment to ensure server is ready
    await asyncio.sleep(1)
    
    # List available tools
    logger.info("Listing available tools...")
    tools = await session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    logger.info(f"Found tools: {tool_names}")
    
    # Verify expected tools are present
    for expected_tool in expected_tools:
        if expected_tool not in tool_names:
            raise AssertionError(f"{expected_tool} tool not found in server")
            
    return tool_names


def get_free_port() -> int:
    """Get a free port for testing."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port
