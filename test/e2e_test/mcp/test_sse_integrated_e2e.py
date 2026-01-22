"""End-to-end tests for SSE transport in integrated mode."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from test.e2e_test.mcp.http_test_utils import (
    get_free_port,
    http_mcp_client_session,
    http_mcp_server,
    initialize_and_test_tools,
    safe_call_tool,
)
from test.e2e_test.slack_retry_utils import retry_slack_api_call

import httpx
import pytest
from dotenv import load_dotenv

from slack_mcp.client.factory import RetryableSlackClientFactory

pytestmark = pytest.mark.asyncio

# Set up logging for better diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_env() -> None:  # noqa: D401 – fixture
    """Load secrets from ``test/e2e_test/.env`` if present."""
    env_path = Path("./.env")
    logger.info(f"Loading secrets from {env_path}")
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Environment loaded")
    else:
        logger.warning(f"Environment file not found: {env_path}")


load_env()

# Create a retry-enabled client factory with a higher retry count for e2e tests
client_factory = RetryableSlackClientFactory(max_retry_count=5)


@retry_slack_api_call
async def _auth_test(client):
    return await client.auth_test()


@retry_slack_api_call
async def _post_message(client, channel, text, thread_ts=None):
    if thread_ts:
        return await client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
    else:
        return await client.chat_postMessage(channel=channel, text=text)


@retry_slack_api_call
async def _get_conversation_history(client, channel, limit):
    return await client.conversations_history(channel=channel, limit=limit)


@pytest.mark.skipif(
    not os.getenv("E2E_TEST_API_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_integrated_health_check_e2e() -> None:  # noqa: D401 – E2E
    """Test health check endpoint in SSE integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None

    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")

    logger.info("Testing SSE integrated health check endpoint")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for integrated mode to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE integrated server on port {port}")

    # Start server and test health endpoint
    async with http_mcp_server(
        transport="sse", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:
        # Test health endpoint
        health_url = f"{server.base_url}/health"
        async with httpx.AsyncClient() as client:
            response = await client.get(health_url)
            assert response.status_code == 200, f"Health endpoint returned {response.status_code}"

            health_data = response.json()
            assert health_data["status"] == "healthy", f"Health status is not healthy: {health_data}"
            assert health_data["service"] == "slack-webhook-server", "Wrong service name in health response"
            assert "components" in health_data, "Missing components in health response"
            # Note: Integrated server doesn't include transport info in health response

            logger.info(f"Health check successful: {health_data}")


@pytest.mark.skipif(
    not os.getenv("E2E_TEST_API_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_integrated_mcp_functionality_e2e() -> None:  # noqa: D401 – E2E
    """Test MCP functionality via SSE transport in integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    channel_id = settings.slack_test_channel_id
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")
    if not channel_id:
        pytest.fail("SLACK_TEST_CHANNEL_ID not set")
        
    unique_text = f"mcp-e2e-sse-integrated-{uuid.uuid4()}"

    logger.info(f"Testing SSE integrated MCP functionality with channel ID: {channel_id}")
    logger.info(f"Using unique message text: {unique_text}")

    # Verify token works with direct API call first
    try:
        test_client = client_factory.create_async_client(token=bot_token)
        auth_test = await _auth_test(test_client)
        logger.info(f"Auth test successful: {auth_test['user']} / {auth_test['team']}")
    except Exception as e:
        pytest.fail(f"Slack API authentication failed: {e}")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for integrated mode to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE integrated server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="sse", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:
        async with http_mcp_client_session(
            transport="sse", base_url=server.base_url, mount_path=mount_path, integrated=True
        ) as session:
            # Initialize session and verify tools
            expected_tools = ["slack_post_message", "slack_read_channel_messages", "slack_thread_reply"]
            tool_names = await initialize_and_test_tools(session, expected_tools)

            # Call slack_post_message tool with timeout protection
            logger.info(f"Calling slack_post_message tool with channel: {channel_id}")
            result = await safe_call_tool(
                session,
                "slack_post_message",
                {
                    "input_params": {
                        "channel": channel_id,
                        "text": unique_text,
                    }
                },
            )

            # Verify the result is successful
            assert result.isError is False, f"Tool execution failed: {result.content}"
            assert len(result.content) > 0, "Expected non-empty content in response"

            # Extract and parse response
            text_content = result.content[0]
            assert hasattr(text_content, "text"), "TextContent missing text field"
            slack_response = json.loads(text_content.text)

            # Verify Slack API response
            assert slack_response.get("ok") is True, f"Slack API returned error: {slack_response}"
            assert "ts" in slack_response, "Missing timestamp in Slack response"

            logger.info(f"Message successfully sent via SSE integrated with timestamp: {slack_response.get('ts')}")

    # Verify message was delivered
    await asyncio.sleep(1)
    try:
        client = client_factory.create_async_client(token=bot_token)
        history = await _get_conversation_history(client, channel=channel_id, limit=10)
        messages = history.get("messages", [])
        found = any(msg.get("text") == unique_text for msg in messages)
        assert found, "Message not found in channel history"
        logger.info("SSE integrated message successfully verified in channel history")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify message due to missing permissions: {e}")
        else:
            pytest.fail(f"Message verification failed: {e}")


@pytest.mark.skipif(
    not os.getenv("E2E_TEST_API_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_integrated_webhook_availability_e2e() -> None:  # noqa: D401 – E2E
    """Test webhook endpoints availability in SSE integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")

    logger.info("Testing SSE integrated webhook endpoint availability")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for integrated mode to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE integrated server on port {port}")

    # Start server and test webhook endpoints
    async with http_mcp_server(
        transport="sse", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:
        async with httpx.AsyncClient() as client:
            # Test webhook events endpoint (should exist but require proper headers/auth)
            webhook_url = f"{server.base_url}/slack/events"
            response = await client.get(webhook_url)
            # Webhook endpoint should respond (likely with 405 Method Not Allowed for GET, but it exists)
            assert response.status_code in [
                405,
                422,
            ], f"Webhook endpoint returned unexpected status: {response.status_code}"

            # Test webhook install endpoint
            install_url = f"{server.base_url}/slack/install"
            response = await client.get(install_url)
            # Install endpoint should respond (may redirect or show install page)
            assert response.status_code in [
                200,
                302,
                404,
            ], f"Install endpoint returned unexpected status: {response.status_code}"

            logger.info("Webhook endpoints are available in SSE integrated mode")


@pytest.mark.skipif(
    not os.getenv("E2E_TEST_API_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_integrated_concurrent_access_e2e() -> None:  # noqa: D401 – E2E
    """Test concurrent access to both MCP and webhook functionality in SSE integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    channel_id = settings.slack_test_channel_id
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")
    if not channel_id:
        pytest.fail("SLACK_TEST_CHANNEL_ID not set")

    logger.info("Testing SSE integrated concurrent access to MCP and webhook functionality")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for integrated mode to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE integrated server on port {port}")

    # Start server and run concurrent tests
    async with http_mcp_server(
        transport="sse", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:

        async def test_mcp_functionality():
            """Test MCP functionality concurrently."""
            async with http_mcp_client_session(
                transport="sse", base_url=server.base_url, mount_path=mount_path, integrated=True
            ) as session:
                # Initialize and list tools
                await session.initialize()
                await asyncio.sleep(0.5)
                tools = await session.list_tools()
                return [tool.name for tool in tools.tools]

        async def test_health_endpoint():
            """Test health endpoint concurrently."""
            async with httpx.AsyncClient() as client:
                health_url = f"{server.base_url}/health"
                response = await client.get(health_url)
                return response.status_code == 200

        async def test_webhook_endpoint():
            """Test webhook endpoint availability concurrently."""
            async with httpx.AsyncClient() as client:
                webhook_url = f"{server.base_url}/slack/events"
                response = await client.get(webhook_url)
                return response.status_code in [405, 422]  # Expected for GET request

        # Run all tests concurrently
        try:
            mcp_tools, health_ok, webhook_ok = await asyncio.gather(
                test_mcp_functionality(), test_health_endpoint(), test_webhook_endpoint(), return_exceptions=True
            )

            # Check results
            if isinstance(mcp_tools, Exception):  # type: ignore[has-type]
                pytest.fail(f"MCP functionality test failed: {mcp_tools}")  # type: ignore[has-type]
            if isinstance(health_ok, Exception):  # type: ignore[has-type]
                pytest.fail(f"Health endpoint test failed: {health_ok}")  # type: ignore[has-type]
            if isinstance(webhook_ok, Exception):  # type: ignore[has-type]
                pytest.fail(f"Webhook endpoint test failed: {webhook_ok}")  # type: ignore[has-type]

            assert len(mcp_tools) > 0, "No MCP tools found"  # type: ignore[has-type]
            assert health_ok, "Health endpoint not accessible"  # type: ignore[has-type]
            assert webhook_ok, "Webhook endpoint not accessible"  # type: ignore[has-type]

            logger.info(
                f"Concurrent access successful - MCP tools: {len(mcp_tools)}, Health: {health_ok}, Webhook: {webhook_ok}"  # type: ignore[has-type]
            )

        except Exception as e:
            pytest.fail(f"Concurrent access test failed: {e}")


@pytest.mark.skipif(
    not os.getenv("E2E_TEST_API_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_integrated_multiple_mcp_sessions_e2e() -> None:  # noqa: D401 – E2E
    """Test multiple concurrent MCP sessions in SSE integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    channel_id = settings.slack_test_channel_id
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")
    if not channel_id:
        pytest.fail("SLACK_TEST_CHANNEL_ID not set")

    logger.info("Testing SSE integrated multiple concurrent MCP sessions")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for integrated mode to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE integrated server on port {port}")

    # Start server and run multiple session test
    async with http_mcp_server(
        transport="sse", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:

        async def create_mcp_session(session_id: int):
            """Create and test an MCP session."""
            try:
                async with http_mcp_client_session(
                    transport="sse", base_url=server.base_url, mount_path=mount_path, integrated=True
                ) as session:
                    # Initialize session
                    await session.initialize()
                    await asyncio.sleep(0.1)

                    # List tools
                    tools = await session.list_tools()
                    tool_names = [tool.name for tool in tools.tools]

                    logger.info(f"Session {session_id}: Found {len(tool_names)} tools")
                    return session_id, len(tool_names)
            except Exception as e:
                logger.error(f"Session {session_id} failed: {e}")
                return session_id, 0

        # Create multiple concurrent sessions
        num_sessions = 3
        session_tasks = [create_mcp_session(i) for i in range(num_sessions)]

        try:
            results = await asyncio.gather(*session_tasks, return_exceptions=True)

            successful_sessions = 0
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Session failed with exception: {result}")
                else:
                    session_id, tool_count = result  # type: ignore[misc]
                    if tool_count > 0:
                        successful_sessions += 1
                        logger.info(f"Session {session_id} successful with {tool_count} tools")

            assert (
                successful_sessions >= num_sessions * 0.8
            ), f"Only {successful_sessions}/{num_sessions} sessions successful"
            logger.info(f"Multiple MCP sessions test successful: {successful_sessions}/{num_sessions} sessions worked")

        except Exception as e:
            pytest.fail(f"Multiple MCP sessions test failed: {e}")
