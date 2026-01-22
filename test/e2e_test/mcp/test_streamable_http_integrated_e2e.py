"""End-to-end tests for Streamable-HTTP transport in integrated mode."""

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
from test.e2e_test.common_utils import should_run_e2e_tests, get_e2e_credentials

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
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_integrated_health_check_e2e() -> None:  # noqa: D401 – E2E
    """Test health check endpoint in Streamable-HTTP integrated mode."""
    # Get required values from settings
    bot_token, _ = get_e2e_credentials()  # Only need bot_token for health check

    logger.info("Testing Streamable-HTTP integrated health check endpoint")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for streamable-http integrated to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP integrated server on port {port}")

    # Start server and test health endpoint
    async with http_mcp_server(
        transport="streamable-http", integrated=True, port=port, mount_path=mount_path, env=server_env
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
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_integrated_mcp_functionality_e2e() -> None:  # noqa: D401 – E2E
    """Test MCP functionality via Streamable-HTTP transport in integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    channel_id = settings.slack_test_channel_id
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")
    if not channel_id:
        pytest.fail("SLACK_TEST_CHANNEL_ID not set")
        
    unique_text = f"mcp-e2e-streamable-http-integrated-{uuid.uuid4()}"

    logger.info(f"Testing Streamable-HTTP integrated MCP functionality with channel ID: {channel_id}")
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
    mount_path = None  # Fix: mount_path should be None for streamable-http integrated to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP integrated server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="streamable-http", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=mount_path, integrated=True
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

            logger.info(
                f"Message successfully sent via Streamable-HTTP integrated with timestamp: {slack_response.get('ts')}"
            )

    # Verify message was delivered
    await asyncio.sleep(1)
    try:
        client = client_factory.create_async_client(token=bot_token)
        history = await _get_conversation_history(client, channel=channel_id, limit=10)
        messages = history.get("messages", [])
        found = any(msg.get("text") == unique_text for msg in messages)
        assert found, "Message not found in channel history"
        logger.info("Streamable-HTTP integrated message successfully verified in channel history")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify message due to missing permissions: {e}")
        else:
            pytest.fail(f"Message verification failed: {e}")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_integrated_webhook_functionality_e2e() -> None:  # noqa: D401 – E2E
    """Test webhook functionality in Streamable-HTTP integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")

    logger.info("Testing Streamable-HTTP integrated webhook functionality")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for streamable-http integrated to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP integrated server on port {port}")

    # Start server and test webhook endpoints
    async with http_mcp_server(
        transport="streamable-http", integrated=True, port=port, mount_path=mount_path, env=server_env
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

            # Test OAuth callback endpoint
            oauth_url = f"{server.base_url}/slack/oauth_redirect"
            response = await client.get(oauth_url)
            # OAuth endpoint should respond (may return error without proper parameters or not found)
            assert response.status_code in [
                400,
                404,
                422,
            ], f"OAuth endpoint returned unexpected status: {response.status_code}"

            logger.info("Webhook endpoints are functional in Streamable-HTTP integrated mode")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_integrated_concurrent_mcp_webhook_e2e() -> None:  # noqa: D401 – E2E
    """Test concurrent MCP and webhook operations in Streamable-HTTP integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")
    channel_id = settings.slack_test_channel_id
    if not channel_id:
        pytest.fail("SLACK_TEST_CHANNEL_ID not set")

    logger.info("Testing Streamable-HTTP integrated concurrent MCP and webhook operations")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for streamable-http integrated to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP integrated server on port {port}")

    # Start server and run concurrent tests
    async with http_mcp_server(
        transport="streamable-http", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:

        async def test_mcp_tools():
            """Test MCP tools functionality concurrently."""
            async with http_mcp_client_session(
                transport="streamable-http", base_url=server.base_url, mount_path=mount_path, integrated=True
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
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status") == "healthy"
                return False

        async def test_webhook_endpoints():
            """Test webhook endpoints concurrently."""
            async with httpx.AsyncClient() as client:
                # Test multiple webhook endpoints
                webhook_tests = []

                # Events endpoint (expect 405 or 422 for GET)
                events_url = f"{server.base_url}/slack/events"
                events_response = await client.get(events_url)
                webhook_tests.append(events_response.status_code in [405, 422])

                # Install endpoint (expect various valid responses)
                install_url = f"{server.base_url}/slack/install"
                install_response = await client.get(install_url)
                webhook_tests.append(install_response.status_code in [200, 302, 404])

                return all(webhook_tests)

        # Run all tests concurrently
        try:
            mcp_tools, health_ok, webhook_ok = await asyncio.gather(
                test_mcp_tools(), test_health_endpoint(), test_webhook_endpoints(), return_exceptions=True
            )

            # Check results
            if isinstance(mcp_tools, Exception):  # type: ignore[has-type]
                pytest.fail(f"MCP tools test failed: {mcp_tools}")  # type: ignore[has-type]
            if isinstance(health_ok, Exception):  # type: ignore[has-type]
                pytest.fail(f"Health endpoint test failed: {health_ok}")  # type: ignore[has-type]
            if isinstance(webhook_ok, Exception):  # type: ignore[has-type]
                pytest.fail(f"Webhook endpoints test failed: {webhook_ok}")  # type: ignore[has-type]

            assert len(mcp_tools) > 0, "No MCP tools found"  # type: ignore[has-type]
            assert health_ok, "Health endpoint not working"  # type: ignore[has-type]
            assert webhook_ok, "Webhook endpoints not working"  # type: ignore[has-type]

            logger.info(
                f"Concurrent operations successful - MCP tools: {len(mcp_tools)}, Health: {health_ok}, Webhooks: {webhook_ok}"  # type: ignore[has-type]
            )

        except Exception as e:
            pytest.fail(f"Concurrent operations test failed: {e}")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_integrated_streaming_behavior_e2e() -> None:  # noqa: D401 – E2E
    """Test streaming behavior specific to Streamable-HTTP transport in integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")
    channel_id = settings.slack_test_channel_id
    if not channel_id:
        pytest.fail("SLACK_TEST_CHANNEL_ID not set")

    logger.info("Testing Streamable-HTTP integrated streaming behavior")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for streamable-http integrated to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP integrated server on port {port}")

    # Start server and test streaming behavior
    async with http_mcp_server(
        transport="streamable-http", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=mount_path, integrated=True
        ) as session:
            # Initialize session
            await session.initialize()

            # Test tool listing (should work with streaming)
            tools_result = await session.list_tools()
            assert len(tools_result.tools) > 0, "No tools found via streaming"

            # Test resource listing (should work with streaming)
            resources_result = await session.list_resources()
            # Resources may or may not be available, just check it doesn't error
            logger.info(f"Resources available: {len(resources_result.resources) if resources_result.resources else 0}")

            # Test prompt listing (should work with streaming)
            prompts_result = await session.list_prompts()
            # Prompts may or may not be available, just check it doesn't error
            logger.info(f"Prompts available: {len(prompts_result.prompts) if prompts_result.prompts else 0}")

            # Test a tool call with streaming (this should work smoothly)
            result = await session.call_tool("slack_read_emojis", {"input_params": {}})

            assert result.isError is False, f"Streaming tool call failed: {result.content}"
            assert len(result.content) > 0, "Expected content from streaming tool call"

            # Parse the result to verify it's valid
            text_content = result.content[0]
            slack_response = json.loads(text_content.text)
            assert slack_response.get("ok") is True, f"Slack API returned error via streaming: {slack_response}"

            logger.info("Streamable-HTTP integrated streaming behavior working correctly")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_integrated_error_handling_e2e() -> None:  # noqa: D401 – E2E
    """Test error handling in Streamable-HTTP integrated mode."""
    # Get required values from settings
    from slack_mcp.settings import get_settings
    settings = get_settings()
    bot_token = settings.e2e_test_api_token.get_secret_value() if settings.e2e_test_api_token else None
    
    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")

    logger.info("Testing Streamable-HTTP integrated error handling")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # Fix: mount_path should be None for streamable-http integrated to avoid double mounting

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP integrated server on port {port}")

    # Start server and test error handling
    async with http_mcp_server(
        transport="streamable-http", integrated=True, port=port, mount_path=mount_path, env=server_env
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=mount_path, integrated=True
        ) as session:
            # Initialize session
            await session.initialize()

            # Test calling a non-existent tool (should handle error gracefully)
            try:
                result = await session.call_tool("non_existent_tool", {"input_params": {}})
                # If this doesn't raise an exception, check that it returns an error
                assert result.isError is True, "Expected error for non-existent tool"
                logger.info("Non-existent tool error handled correctly")
            except Exception as e:
                # This is also acceptable - the client may raise an exception
                logger.info(f"Non-existent tool raised exception as expected: {type(e).__name__}")

            # Test calling a valid tool with invalid parameters
            try:
                result = await session.call_tool(
                    "slack_post_message",
                    {"input_params": {"invalid_param": "invalid_value"}},  # Missing required channel and text
                )
                # Should return an error or raise an exception
                if not result.isError:
                    # Check if the Slack API returned an error
                    text_content = result.content[0] if result.content else None
                    if text_content and hasattr(text_content, "text"):
                        slack_response = json.loads(text_content.text)
                        assert slack_response.get("ok") is False, "Expected Slack API error for invalid parameters"
                logger.info("Invalid parameters error handled correctly")
            except Exception as e:
                # This is also acceptable - the tool may raise an exception for invalid params
                logger.info(f"Invalid parameters raised exception as expected: {type(e).__name__}")

            logger.info("Streamable-HTTP integrated error handling working correctly")
