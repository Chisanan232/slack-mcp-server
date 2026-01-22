"""End-to-end tests for SSE transport in standalone mode."""

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

import pytest
from test.e2e_test.common_utils import should_run_e2e_tests, get_e2e_credentials
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
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_standalone_post_message_e2e() -> None:  # noqa: D401 – E2E
    """Test posting a message via SSE transport in standalone mode."""
    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()
    
    unique_text = f"mcp-e2e-sse-standalone-{uuid.uuid4()}"

    logger.info(f"Testing SSE standalone with channel ID: {channel_id}")
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
    mount_path = None  # No mount path in standalone mode

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE standalone server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="sse",
        integrated=False,
        port=port,
        mount_path=None,  # No mount path in standalone mode
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="sse", base_url=server.base_url, mount_path=None, integrated=False
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

            logger.info(f"Message successfully sent via SSE standalone with timestamp: {slack_response.get('ts')}")

    # Verify message was delivered
    await asyncio.sleep(1)
    try:
        client = client_factory.create_async_client(token=bot_token)
        history = await _get_conversation_history(client, channel=channel_id, limit=10)
        messages = history.get("messages", [])
        found = any(msg.get("text") == unique_text for msg in messages)
        assert found, "Message not found in channel history"
        logger.info("SSE standalone message successfully verified in channel history")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify message due to missing permissions: {e}")
        else:
            pytest.fail(f"Message verification failed: {e}")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_standalone_thread_reply_e2e() -> None:  # noqa: D401 – E2E
    """Test sending thread replies via SSE transport in standalone mode."""
    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()
    
    unique_parent_text = f"mcp-e2e-sse-standalone-parent-{uuid.uuid4()}"
    unique_reply_texts = [
        f"mcp-e2e-sse-standalone-reply1-{uuid.uuid4()}",
        f"mcp-e2e-sse-standalone-reply2-{uuid.uuid4()}",
    ]

    logger.info(f"Testing SSE standalone thread replies with channel ID: {channel_id}")

    # First, post a parent message directly using Slack SDK
    try:
        client = client_factory.create_async_client(token=bot_token)
        parent_response = await _post_message(client, channel=channel_id, text=unique_parent_text)
        assert parent_response["ok"] is True, "Failed to send parent message"
        parent_ts = parent_response["ts"]
        logger.info(f"Posted parent message with timestamp: {parent_ts}")
    except Exception as e:
        pytest.fail(f"Failed to post parent message: {e}")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # No mount path in standalone mode

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE standalone server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="sse",
        integrated=False,
        port=port,
        mount_path=None,  # No mount path in standalone mode
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="sse", base_url=server.base_url, mount_path=None, integrated=False
        ) as session:
            # Initialize session and verify tools
            expected_tools = ["slack_thread_reply"]
            await initialize_and_test_tools(session, expected_tools)

            # Call slack_thread_reply tool with timeout protection
            logger.info(f"Calling slack_thread_reply tool with channel: {channel_id} and thread_ts: {parent_ts}")
            result = await safe_call_tool(
                session,
                "slack_thread_reply",
                {"input_params": {"channel": channel_id, "thread_ts": parent_ts, "texts": unique_reply_texts}},
            )

            # Verify the result is successful
            assert result.isError is False, f"Tool execution failed: {result.content}"
            assert len(result.content) > 0, "Expected non-empty content in response"

            # Extract and parse response
            text_content = result.content[0]
            response_data = json.loads(text_content.text)

            # Verify responses
            assert "responses" in response_data, "Missing 'responses' key in response data"
            slack_responses = response_data["responses"]
            assert len(slack_responses) == len(unique_reply_texts), "Response count doesn't match sent messages count"

            # Check each response
            for i, response in enumerate(slack_responses):
                assert response.get("ok") is True, f"Reply {i+1} failed: {response}"

            logger.info("All thread replies successfully sent via SSE standalone")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_sse_standalone_read_channel_messages_e2e() -> None:  # noqa: D401 – E2E
    """Test reading channel messages via SSE transport in standalone mode."""
    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()

    logger.info(f"Testing SSE standalone read messages from channel ID: {channel_id}")

    # Get a free port for testing
    port = get_free_port()
    mount_path = None  # No mount path in standalone mode

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting SSE standalone server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="sse",
        integrated=False,
        port=port,
        mount_path=None,  # No mount path in standalone mode
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="sse", base_url=server.base_url, mount_path=None, integrated=False
        ) as session:
            # Initialize session and verify tools
            expected_tools = ["slack_read_channel_messages"]
            await initialize_and_test_tools(session, expected_tools)

            # Call slack_read_channel_messages tool with timeout protection
            logger.info(f"Calling slack_read_channel_messages tool with channel: {channel_id}")
            result = await safe_call_tool(
                session, "slack_read_channel_messages", {"input_params": {"channel": channel_id, "limit": 5}}
            )

            # Check if we got an error related to permissions
            if result.isError:
                error_text = result.content[0].text if result.content and hasattr(result.content[0], "text") else ""
                if "missing_scope" in error_text:
                    pytest.skip(f"Bot token lacks required permission scope: {error_text}")
                else:
                    pytest.fail(f"Tool execution failed: {error_text}")

            # Verify successful result
            assert len(result.content) > 0, "Expected non-empty content in response"

            # Extract and parse response
            text_content = result.content[0]
            slack_response = json.loads(text_content.text)

            # Verify Slack API response
            assert slack_response.get("ok") is True, f"Slack API returned error: {slack_response}"
            assert "messages" in slack_response, "Missing messages in Slack response"

            messages = slack_response.get("messages", [])
            logger.info(f"Successfully read {len(messages)} messages via SSE standalone")
