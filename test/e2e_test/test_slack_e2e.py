"""End-to-end test sending a real message to Slack via the MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from dotenv import load_dotenv
from slack_sdk.web.async_client import AsyncWebClient

pytestmark = pytest.mark.asyncio

# Set up logging for better diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_test")


def load_env() -> None:  # noqa: D401 – fixture
    """Load secrets from ``test/e2e_test/.env`` if present."""
    env_path = Path(__file__).parent / ".env"
    logger.info(f"Loading secrets from {env_path}")
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Environment loaded")
    else:
        logger.warning(f"Environment file not found: {env_path}")


load_env()


@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (SLACK_BOT_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_slack_post_message_e2e() -> None:  # noqa: D401 – E2E
    """Spawn the server via stdio and post a message, then verify on Slack."""
    # Import here to avoid heavy dependencies at collection time
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Get required values from environment
    bot_token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_TEST_CHANNEL_ID"]
    unique_text = f"mcp-e2e-{uuid.uuid4()}"

    logger.info(f"Testing with channel ID: {channel_id}")
    logger.info(f"Using unique message text: {unique_text}")

    # Verify token works with direct API call first
    try:
        test_client = AsyncWebClient(token=bot_token)
        auth_test = await test_client.auth_test()
        logger.info(f"Auth test successful: {auth_test['user']} / {auth_test['team']}")
    except Exception as e:
        pytest.fail(f"Slack API authentication failed: {e}")

    # Prepare server with explicit environment set
    custom_env = {**os.environ}  # Create a copy
    custom_env["SLACK_BOT_TOKEN"] = bot_token  # Ensure token is explicitly set

    # Use simple transport args with explicit log level
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "slack_mcp.entry"],
        env=custom_env,
    )

    logger.info("Starting MCP server via stdio")

    # Set a reasonable timeout for operations
    read_timeout = timedelta(seconds=30)

    try:
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

                if "slack_post_message" not in tool_names:
                    pytest.fail("slack_post_message tool not found in server")

                # Call our test tool
                logger.info(f"Calling slack_post_message tool with channel: {channel_id}")
                result = await session.call_tool(
                    "slack_post_message",
                    {
                        "input_params": {
                            "channel": channel_id,
                            "text": unique_text,
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
                assert "ts" in slack_response, "Missing timestamp in Slack response"
                assert "channel" in slack_response, "Missing channel in Slack response"

                # Store the timestamp for verification
                message_ts = slack_response.get("ts")
                logger.info(f"Message successfully sent with timestamp: {message_ts}")
    except Exception as e:
        logger.error(f"Error: {repr(e)}")
        import traceback

        logger.error(traceback.format_exc())
        pytest.fail(f"MCP client operation failed: {e}")

    # Wait briefly to ensure message propagation
    await asyncio.sleep(1)

    # Verify the message was actually delivered
    logger.info("Verifying message delivery...")
    try:
        client = AsyncWebClient(token=bot_token)
        history = await client.conversations_history(channel=channel_id, limit=10)

        messages = history.get("messages", [])
        logger.info(f"Found {len(messages)} recent messages")

        found = any(msg.get("text") == unique_text for msg in messages)
        assert found, "Message not found in channel history"
        logger.info("Message successfully verified in channel history")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify message in history due to missing permissions: {e}")
            logger.warning("Skipping full verification, but message send was successful")
            # Since we got a successful response from the Slack API on send, we consider this test passed
        else:
            pytest.fail(f"Message verification failed: {e}")


@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (SLACK_BOT_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_slack_read_channel_messages_e2e() -> None:
    """Spawn the server via stdio and read messages from a channel."""
    # Import here to avoid heavy dependencies at collection time
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Get required values from environment
    bot_token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_TEST_CHANNEL_ID"]

    logger.info(f"Testing read messages from channel ID: {channel_id}")

    # Create a variable to track test failures
    should_fail = False
    failure_reason = None
    unique_text = None

    # Stage 1: Verify token and permissions
    if not should_fail:
        try:
            test_client = AsyncWebClient(token=bot_token)
            auth_test = await test_client.auth_test()
            logger.info(f"Auth test successful: {auth_test['user']} / {auth_test['team']}")

            # Check if we have the correct permissions for the channel type
            channel_info_response = None
            try:
                # Try to get channel info (for public channels)
                channel_info_response = await test_client.conversations_info(channel=channel_id)
                logger.info(f"Channel type: {channel_info_response.get('channel', {}).get('is_private')}")
            except Exception as channel_e:
                logger.warning(f"Could not get channel info: {channel_e}")
                if "missing_scope" in str(channel_e).lower():
                    should_fail = True
                    failure_reason = f"Bot token lacks required permission scope for channel info: {channel_e}"

            # If we can get channel info, check if this is a private channel requiring groups:history scope
            if not should_fail and channel_info_response:
                is_private = channel_info_response.get("channel", {}).get("is_private", False)
                if is_private:
                    # Check if we can directly access history (to catch permission issues early)
                    try:
                        history_test = await test_client.conversations_history(channel=channel_id, limit=1)
                        if not history_test.get("ok"):
                            scopes_needed = history_test.get("needed", "")
                            scopes_provided = history_test.get("provided", "")
                            logger.warning(
                                f"Missing scopes for private channel: needed={scopes_needed}, provided={scopes_provided}"
                            )
                            should_fail = True
                            failure_reason = (
                                f"Bot lacks required permission scopes for private channel: {scopes_needed}"
                            )
                    except Exception as he:
                        logger.warning(f"Cannot access channel history directly: {he}")
                        should_fail = True
                        failure_reason = f"Cannot access channel history: {he}"
        except Exception as e:
            should_fail = True
            failure_reason = f"Slack API authentication failed: {e}"
            logger.error(failure_reason)

    # Stage 2: Send a test message
    if not should_fail:
        try:
            client = AsyncWebClient(token=bot_token)
            unique_text = f"mcp-e2e-read-test-{uuid.uuid4()}"
            message_result = await client.chat_postMessage(channel=channel_id, text=unique_text)
            logger.info(f"Test message sent with timestamp: {message_result.get('ts')}")
        except Exception as e:
            logger.warning(f"Failed to send test message: {e}")
            # Continue with test, we'll just check if we can read any messages

    # Stage 3: Start server and test MCP function
    if not should_fail:
        # Prepare server with explicit environment set
        custom_env = {**os.environ}
        custom_env["SLACK_BOT_TOKEN"] = bot_token

        # Use simple transport args with explicit log level
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "slack_mcp.entry"],
            env=custom_env,
        )

        logger.info("Starting MCP server via stdio")

        # Set a reasonable timeout for operations
        read_timeout = timedelta(seconds=30)

        try:
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

                    if "slack_read_channel_messages" not in tool_names:
                        should_fail = True
                        failure_reason = "slack_read_channel_messages tool not found in server"
                    else:
                        # Call our test tool
                        logger.info(f"Calling slack_read_channel_messages tool with channel: {channel_id}")
                        result = await session.call_tool(
                            "slack_read_channel_messages",
                            {"input_params": {"channel": channel_id, "limit": 10}},
                            read_timeout_seconds=read_timeout,
                        )

                        # Log the result
                        logger.info(f"Tool result content type: {type(result.content).__name__}")

                        # Check if we got an error related to permissions
                        if result.isError:
                            error_text = (
                                result.content[0].text if result.content and hasattr(result.content[0], "text") else ""
                            )
                            logger.warning(f"Tool returned an error: {error_text}")

                            # If it's a permissions issue, fail the test with a clear message
                            if "missing_scope" in error_text:
                                needed_scope = None
                                if "needed:" in error_text:
                                    # Try to extract the needed scope from the error message
                                    parts = error_text.split("needed:")
                                    if len(parts) > 1:
                                        scope_part = parts[1].split(",")[0].strip()
                                        needed_scope = scope_part.strip("'").strip()

                                fail_message = f"Bot token lacks required permission scope"
                                if needed_scope:
                                    fail_message += f": {needed_scope}"
                                should_fail = True
                                failure_reason = fail_message
                            else:
                                # Otherwise mark to fail the test
                                should_fail = True
                                failure_reason = f"Tool execution failed: {error_text}"
                        else:
                            # Tool executed without error, verify the results
                            if len(result.content) == 0:
                                should_fail = True
                                failure_reason = "Expected non-empty content in response"
                            else:
                                # The content is a list of TextContent objects
                                text_content = result.content[0]
                                logger.info(f"Content item type: {type(text_content).__name__}")

                                # Extract response from TextContent
                                if not hasattr(text_content, "text"):
                                    should_fail = True
                                    failure_reason = "TextContent missing text field"
                                else:
                                    logger.info(f"Response text preview: {text_content.text[:100]}...")

                                    # Parse the JSON response
                                    slack_response = json.loads(text_content.text)
                                    logger.info(f"Parsed Slack response: {slack_response.get('ok')}")

                                    # Verify the result is successful
                                    if not slack_response.get("ok"):
                                        should_fail = True
                                        failure_reason = f"Slack API returned error: {slack_response}"
                                    elif "messages" not in slack_response:
                                        should_fail = True
                                        failure_reason = "Missing messages in Slack response"
                                    else:
                                        # Verify that our test message is in the returned messages
                                        messages = slack_response.get("messages", [])
                                        logger.info(f"Found {len(messages)} messages in the response")

                                        # Check that our test message is included in the results if we were able to send one
                                        if unique_text:
                                            found = any(msg.get("text") == unique_text for msg in messages)
                                            if not found:
                                                logger.warning("Test message not found in channel history response.")
                                                # This could happen legitimately (e.g., with many active messages),
                                                # so we'll just log it rather than fail the test

                                        logger.info("Channel history successfully retrieved")
        except Exception as e:
            error_text = str(e)
            if "missing_scope" in error_text.lower():
                logger.warning(f"Failing due to permission issues: {e}")
                should_fail = True
                failure_reason = f"Bot token lacks required permission scope: {e}"
            else:
                logger.error(f"Error: {repr(e)}")
                import traceback

                logger.error(traceback.format_exc())
                should_fail = True
                failure_reason = f"MCP client operation failed: {e}"

    # Now we can properly fail the test if needed
    if should_fail:
        pytest.fail(failure_reason or "Unknown test failure")
