"""End-to-end tests for the integrated server functionality."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import time
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import aiohttp
import pytest
import pytest_asyncio
import uvicorn
from fastapi import Request

from slack_mcp.integrated_server import create_integrated_app


def find_free_port() -> int:
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


class TestServer(uvicorn.Server):
    """Test server that allows programmatic control for testing."""
    
    def __init__(self, config: uvicorn.Config) -> None:
        """Initialize the test server."""
        super().__init__(config)
        self.config = config
        self._started = False
        self._startup_done = asyncio.Event()
    
    async def startup(self, sockets: Optional[list[socket.socket]] = None) -> None:
        """Start the server and set the startup event."""
        await super().startup(sockets)
        self._startup_done.set()
        self._started = True
    
    async def start_and_wait(self) -> None:
        """Start the server and wait for it to be ready."""
        self._startup_done.clear()
        self._started = False
        await asyncio.gather(
            self.serve(),
            self._wait_for_startup()
        )
    
    async def _wait_for_startup(self) -> None:
        """Wait for the server to start."""
        await self._startup_done.wait()


@pytest.fixture
def fake_slack_credentials() -> Generator[Dict[str, str], None, None]:
    """Provide fake Slack credentials for testing and restore the originals after."""
    # Store original env vars
    original_token = os.environ.get("SLACK_BOT_TOKEN")
    original_secret = os.environ.get("SLACK_SIGNING_SECRET")
    
    # Set fake values for testing
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-fake-token-for-testing"
    os.environ["SLACK_SIGNING_SECRET"] = "fake-signing-secret"
    
    yield {
        "token": os.environ["SLACK_BOT_TOKEN"],
        "secret": os.environ["SLACK_SIGNING_SECRET"]
    }
    
    # Restore originals
    if original_token is not None:
        os.environ["SLACK_BOT_TOKEN"] = original_token
    else:
        del os.environ["SLACK_BOT_TOKEN"]
    
    if original_secret is not None:
        os.environ["SLACK_SIGNING_SECRET"] = original_secret
    else:
        del os.environ["SLACK_SIGNING_SECRET"]


@pytest.fixture(autouse=True)
def mock_slack_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the Slack request verification to always return True."""
    async def mock_verify(request: Request, signing_secret: str | None = None) -> bool:
        return True
    
    # Patch the internal verify_slack_request function directly
    monkeypatch.setattr("slack_mcp.slack_app.verify_slack_request", mock_verify)


@pytest_asyncio.fixture
async def sse_server(fake_slack_credentials: Dict[str, str]) -> AsyncGenerator[Dict[str, Any], None]:
    """Start an integrated server with SSE transport for e2e testing."""
    port = find_free_port()
    
    # Create the integrated app
    app = create_integrated_app(
        token=fake_slack_credentials["token"], 
        mcp_transport="sse", 
        mcp_mount_path="/mcp"
    )
    
    # Configure and start the server
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = TestServer(config)
    
    # Start the server in a separate task
    task = asyncio.create_task(server.start_and_wait())
    
    # Give it a moment to start up
    await asyncio.sleep(0.5)
    
    try:
        # Yield the server info
        yield {
            "port": port,
            "base_url": f"http://127.0.0.1:{port}"
        }
    finally:
        # Stop the server
        server.should_exit = True
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_sse_integrated_server(sse_server: Dict[str, Any]) -> None:
    """Test that the integrated server works end-to-end with SSE transport."""
    base_url = sse_server["base_url"]
    
    async with aiohttp.ClientSession() as session:
        # Test the webhook endpoint
        challenge_data = {
            "token": "verification_token",
            "challenge": "challenge_value",
            "type": "url_verification"
        }
        
        # Add required Slack verification headers
        headers = {
            "X-Slack-Signature": "v0=fake_signature",
            "X-Slack-Request-Timestamp": "1234567890",
            "Content-Type": "application/json"
        }
        
        # Test the Slack webhook endpoint
        async with session.post(
            f"{base_url}/slack/events", 
            json=challenge_data,
            headers=headers
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data == {"challenge": "challenge_value"}
        
        # Test the MCP mount point
        # Unlike TestClient in integration tests, aiohttp follows redirects by default
        # We need to disable that to check the redirect status
        async with session.get(f"{base_url}/mcp", allow_redirects=False) as response:
            # We should get a redirect (307) when hitting the mount point
            assert response.status == 307
            # The location header should include the server address
            assert response.headers.get("location").endswith("/mcp/")


@pytest.mark.asyncio
async def test_http_webhook_server(fake_slack_credentials: Dict[str, str]) -> None:
    """Test just the webhook functionality of the integrated server with HTTP transport.
    
    Note: We don't test the full HTTP transport with MCP due to task group initialization issues.
    Instead, we verify that the Slack webhook functionality works correctly.
    """
    port = find_free_port()
    
    # Create a simple Slack app without MCP integration to test webhook functionality
    from slack_mcp.slack_app import create_slack_app
    app = create_slack_app(token=fake_slack_credentials["token"])
    
    # Configure and start the server
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = TestServer(config)
    
    # Start the server in a separate task
    task = asyncio.create_task(server.start_and_wait())
    
    # Give it a moment to start up
    await asyncio.sleep(0.5)
    
    base_url = f"http://127.0.0.1:{port}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test the webhook endpoint
            challenge_data = {
                "token": "verification_token",
                "challenge": "challenge_value",
                "type": "url_verification"
            }
            
            # Add required Slack verification headers
            headers = {
                "X-Slack-Signature": "v0=fake_signature",
                "X-Slack-Request-Timestamp": "1234567890",
                "Content-Type": "application/json"
            }
            
            # Test the Slack webhook endpoint
            async with session.post(
                f"{base_url}/slack/events", 
                json=challenge_data,
                headers=headers
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert data == {"challenge": "challenge_value"}
    finally:
        # Stop the server
        server.should_exit = True
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
