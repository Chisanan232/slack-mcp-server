"""End-to-end test for reading thread messages from Slack via the MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from test.e2e_test.slack_retry_utils import retry_slack_api_call

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


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_read_thread_messages_e2e() -> None:  # noqa: D401 – E2E
    """Spawn the server via stdio, post a message, create a thread, and read thread messages."""
    # Import here to avoid heavy dependencies at collection time
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()
        
    unique_text = f"mcp-e2e-thread-test-{uuid.uuid4()}"

    logger.info(f"Testing with channel ID: {channel_id}")
    logger.info(f"Using unique message text: {unique_text}")

    # Verify token works with direct API call first
    try:
        # Use the RetryableSlackClientFactory instead of direct AsyncWebClient instantiation
        test_client = client_factory.create_async_client(token=bot_token)
        auth_test = await _auth_test(test_client)
        logger.info(f"Auth test successful: {auth_test['user']} / {auth_test['team']}")
    except Exception as e:
        pytest.fail(f"Slack API authentication failed: {e}")

    # Prepare server with explicit environment set
    custom_env = {**os.environ}  # Create a copy
    custom_env["E2E_TEST_API_TOKEN"] = bot_token  # Ensure token is explicitly set

    # Note: The server will automatically read E2E_TEST_API_TOKEN 
    # from settings thanks to the AliasChoices in the settings model

    # Use simple transport args with explicit log level and stdio transport
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "slack_mcp.mcp.entry", "--transport", "stdio"],
        env=custom_env,
    )

    logger.info("Starting MCP server via stdio")

    # Set a reasonable timeout for operations
    read_timeout = timedelta(seconds=30)

    try:
        # First create a message with a thread for testing
        logger.info("Creating a test message with thread replies")
        # Use the client factory with retry for test setup
        test_client = client_factory.create_async_client(token=bot_token)
        parent_message = await _post_message(test_client, channel_id, unique_text)
        parent_ts = parent_message["ts"]
        logger.info(f"Posted parent message with ts: {parent_ts}")

        # Post 2 replies to create a thread
        reply1 = await _post_message(test_client, channel_id, f"Reply 1 to {unique_text}", parent_ts)
        logger.info(f"Posted reply 1 with ts: {reply1['ts']}")

        reply2 = await _post_message(test_client, channel_id, f"Reply 2 to {unique_text}", parent_ts)
        logger.info(f"Posted reply 2 with ts: {reply2['ts']}")

        # Wait briefly to ensure messages are fully processed
        await asyncio.sleep(2)

        # Connect to the server
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream, read_timeout_seconds=read_timeout) as session:
                # Initialize the session first
                logger.info("Initializing MCP session...")
                init_result = await session.initialize()
                logger.info(f"Initialization successful: {init_result}")

                # Wait a moment to ensure server is ready
                await asyncio.sleep(1)

                # List available tools for debugging
                logger.info("Listing available tools...")
                tools = await session.list_tools()
                tool_names = [tool.name for tool in tools.tools]
                logger.info(f"Found tools: {tool_names}")

                if "slack_read_thread_messages" not in tool_names:
                    pytest.fail("slack_read_thread_messages tool not found in server")

                # Call our test tool
                logger.info(
                    f"Calling slack_read_thread_messages tool with channel: {channel_id} and thread_ts: {parent_ts}"
                )
                result = await session.call_tool(
                    "slack_read_thread_messages",
                    {
                        "input_params": {
                            "channel": channel_id,
                            "thread_ts": parent_ts,
                        }
                    },
                    read_timeout_seconds=read_timeout,
                )

                # Log the result
                logger.info(f"Tool result content type: {type(result.content).__name__}")

                # Verify the result is successful
                assert result.isError is False, f"Tool execution failed: {result.content}"
                assert len(result.content) > 0, "Expected non-empty content in response"

                # The content is a list of TextContent objects
                text_content = result.content[0]
                logger.info(f"Content item type: {type(text_content).__name__}")

                # Extract response from TextContent
                assert hasattr(text_content, "text"), "TextContent missing text field"
                logger.info(f"Response text preview: {text_content.text[:100]}...")

                # Parse the JSON response
                slack_response = json.loads(text_content.text)
                logger.info(f"Parsed Slack response: {slack_response.get('ok')}")

                # Verify the result is successful
                assert slack_response.get("ok") is True, f"Slack API returned error: {slack_response}"
                assert "messages" in slack_response, "Missing messages in Slack response"

                # Verify we got at least 3 messages (parent + 2 replies)
                assert (
                    len(slack_response["messages"]) >= 3
                ), f"Expected at least 3 messages, got {len(slack_response['messages'])}"

                # Verify message content
                thread_messages = slack_response["messages"]
                assert thread_messages[0]["ts"] == parent_ts, "First message should be the parent message"

                # Check for our unique messages in the thread
                found_parent = False
                found_reply1 = False
                found_reply2 = False

                for msg in thread_messages:
                    if msg["text"] == unique_text:
                        found_parent = True
                    elif msg["text"] == f"Reply 1 to {unique_text}":
                        found_reply1 = True
                    elif msg["text"] == f"Reply 2 to {unique_text}":
                        found_reply2 = True

                assert found_parent, "Parent message not found in thread"
                assert found_reply1, "Reply 1 not found in thread"
                assert found_reply2, "Reply 2 not found in thread"

                logger.info("Thread messages successfully verified")

    except Exception as e:
        logger.error(f"Error: {repr(e)}")
        import traceback

        logger.error(traceback.format_exc())
        pytest.fail(f"MCP client operation failed: {e}")
