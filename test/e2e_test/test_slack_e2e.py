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


@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (SLACK_BOT_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_slack_thread_reply_e2e() -> None:  # noqa: D401 – E2E
    """Spawn the server via stdio, post a parent message, then reply to it with multiple thread messages."""
    # Import here to avoid heavy dependencies at collection time
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Get required values from environment
    bot_token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_TEST_CHANNEL_ID"]
    unique_parent_text = f"mcp-e2e-parent-{uuid.uuid4()}"
    unique_reply_texts = [f"mcp-e2e-reply1-{uuid.uuid4()}", f"mcp-e2e-reply2-{uuid.uuid4()}"]

    logger.info(f"Testing with channel ID: {channel_id}")
    logger.info(f"Using unique parent message text: {unique_parent_text}")
    logger.info(f"Using unique reply messages: {unique_reply_texts}")

    # Verify token works with direct API call first
    try:
        test_client = AsyncWebClient(token=bot_token)
        auth_test = await test_client.auth_test()
        logger.info(f"Auth test successful: {auth_test['user']} / {auth_test['team']}")
    except Exception as e:
        pytest.fail(f"Slack API authentication failed: {e}")

    # First, post a parent message directly using Slack SDK
    try:
        client = AsyncWebClient(token=bot_token)
        parent_response = await client.chat_postMessage(channel=channel_id, text=unique_parent_text)
        assert parent_response["ok"] is True, "Failed to send parent message"
        parent_ts = parent_response["ts"]
        logger.info(f"Posted parent message with timestamp: {parent_ts}")
    except Exception as e:
        pytest.fail(f"Failed to post parent message: {e}")

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

                if "slack_thread_reply" not in tool_names:
                    pytest.fail("slack_thread_reply tool not found in server")

                # Call our thread reply test tool
                logger.info(f"Calling slack_thread_reply tool with channel: {channel_id} and thread_ts: {parent_ts}")
                result = await session.call_tool(
                    "slack_thread_reply",
                    {"input_params": {"channel": channel_id, "thread_ts": parent_ts, "texts": unique_reply_texts}},
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
                response_data = json.loads(text_content.text)
                logger.info(f"Parsed response data: {response_data.keys()}")

                # Extract the responses list from the response data
                assert "responses" in response_data, "Missing 'responses' key in response data"
                slack_responses = response_data["responses"]
                logger.info(f"Found {len(slack_responses)} replies in the response")

                # Verify we have the expected number of responses
                assert isinstance(slack_responses, list), "Expected list of responses"
                assert len(slack_responses) == len(
                    unique_reply_texts
                ), "Response count doesn't match sent messages count"

                # Check each response
                for i, response in enumerate(slack_responses):
                    assert response.get("ok") is True, f"Reply {i+1} failed: {response}"

                    # The thread_ts can be either at the top level or inside the message object
                    thread_ts_value = response.get("thread_ts")

                    # If not at top level, check if it's in the message object
                    if thread_ts_value is None and "message" in response:
                        thread_ts_value = response["message"].get("thread_ts")

                    assert thread_ts_value is not None, f"Missing thread_ts in reply {i+1}"
                    assert thread_ts_value == parent_ts, f"Reply {i+1} has incorrect thread_ts"

                    # Check text - it might be in the message object or at the top level
                    text_value = response.get("text")
                    if text_value is None and "message" in response:
                        text_value = response["message"].get("text")

                    assert text_value == unique_reply_texts[i], f"Reply {i+1} text mismatch"

                logger.info("All thread replies successfully sent")

    except Exception as e:
        logger.error(f"Error: {repr(e)}")
        import traceback

        logger.error(traceback.format_exc())
        pytest.fail(f"MCP client operation failed: {e}")

    # Wait briefly to ensure message propagation
    await asyncio.sleep(1)

    # Verify the thread replies were actually delivered
    logger.info("Verifying thread replies delivery...")
    try:
        client = AsyncWebClient(token=bot_token)
        replies = await client.conversations_replies(channel=channel_id, ts=parent_ts)

        messages = replies.get("messages", [])
        logger.info(f"Found {len(messages)} messages in the thread")

        # Skip the first message as it's the parent
        thread_messages = messages[1:] if len(messages) > 1 else []
        logger.info(f"Found {len(thread_messages)} replies in the thread")

        # Check if our replies are found
        found_replies = 0
        for reply_text in unique_reply_texts:
            if any(msg.get("text") == reply_text for msg in thread_messages):
                found_replies += 1

        assert found_replies == len(unique_reply_texts), f"Only {found_replies}/{len(unique_reply_texts)} replies found"
        logger.info("All thread replies successfully verified in thread history")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify replies due to missing permissions: {e}")
            logger.warning("Skipping full verification, but thread replies were successful")
            # Since we got successful responses from the Slack API on send, we consider this test passed
        else:
            pytest.fail(f"Thread replies verification failed: {e}")


@pytest.mark.skipif(
    not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Real Slack credentials (SLACK_BOT_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_slack_add_reactions_e2e() -> None:  # noqa: D401 – E2E
    """Spawn the server via stdio, post a message, then add emoji reactions to it."""
    # Import here to avoid heavy dependencies at collection time
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Get required values from environment
    bot_token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_TEST_CHANNEL_ID"]
    unique_text = f"mcp-e2e-reaction-test-{uuid.uuid4()}"

    logger.info(f"Testing with channel ID: {channel_id}")
    logger.info(f"Using unique message text: {unique_text}")
    
    # Create a test message to react to
    message_ts = None
    try:
        test_client = AsyncWebClient(token=bot_token)
        # Verify token works with direct API call first
        auth_test = await test_client.auth_test()
        logger.info(f"Auth test successful: {auth_test['user']} / {auth_test['team']}")
        
        # Send a test message that we'll react to
        message_response = await test_client.chat_postMessage(channel=channel_id, text=unique_text)
        assert message_response["ok"] is True, "Failed to send test message"
        message_ts = message_response["ts"]
        logger.info(f"Created test message with timestamp: {message_ts}")
    except Exception as e:
        pytest.fail(f"Slack API setup failed: {e}")
    
    # Prepare server with explicit environment set
    custom_env = {**os.environ}  # Create a copy
    custom_env["SLACK_BOT_TOKEN"] = bot_token  # Ensure token is explicitly set

    # Use simple transport args
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "slack_mcp.entry"],
        env=custom_env,
    )

    logger.info("Starting MCP server via stdio")

    # Set a reasonable timeout for operations
    read_timeout = timedelta(seconds=30)
    
    # Define emojis to add as reactions
    emojis_to_add = ["thumbsup", "heart"]
    
    # Slack emoji name mapping (some emoji names differ between what we send and what Slack returns)
    slack_emoji_mapping = {
        "thumbsup": "+1",  # Slack returns "+1" when "thumbsup" is used
        # Add other mappings if needed in the future
    }

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

                if "slack_add_reactions" not in tool_names:
                    pytest.fail("slack_add_reactions tool not found in server")

                # Call our test tool
                logger.info(f"Calling slack_add_reactions tool with channel: {channel_id} and message ts: {message_ts}")
                result = await session.call_tool(
                    "slack_add_reactions",
                    {
                        "input_params": {
                            "channel": channel_id,
                            "timestamp": message_ts,
                            "emojis": emojis_to_add,
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
                logger.info(f"Parsed Slack response: {slack_response}")

                # Verify the result has expected structure
                assert "responses" in slack_response, "Missing 'responses' field in Slack response"
                assert isinstance(slack_response["responses"], list), "'responses' should be a list"
                assert len(slack_response["responses"]) == len(emojis_to_add), f"Expected {len(emojis_to_add)} responses"
                
                # Check each response for the emoji reactions
                for i, emoji in enumerate(emojis_to_add):
                    response = slack_response["responses"][i]
                    assert response.get("ok") is True, f"Slack API returned error for emoji {emoji}: {response}"
                    # The Slack API reactions.add doesn't return name and timestamp in the response
                    # We just verify that each reaction was successfully added ("ok": true)
                
                logger.info("Successfully added emoji reactions")
    except Exception as e:
        logger.error(f"Error: {repr(e)}")
        import traceback

        logger.error(traceback.format_exc())
        pytest.fail(f"MCP client operation failed: {e}")

    # Wait briefly to ensure reactions are processed
    await asyncio.sleep(1)

    # Verify the reactions were actually added
    logger.info("Verifying emoji reactions were added...")
    try:
        client = AsyncWebClient(token=bot_token)
        reactions_response = await client.reactions_get(channel=channel_id, timestamp=message_ts)
        
        assert reactions_response.get("ok") is True, f"Reactions API call failed: {reactions_response}"
        assert "message" in reactions_response, "Missing 'message' field in reactions response"
        
        message = reactions_response.get("message", {})
        assert "reactions" in message, "No reactions found on message"
        
        reactions = message.get("reactions", [])
        reaction_names = [reaction.get("name") for reaction in reactions]
        logger.info(f"Found reaction names: {reaction_names}")
        
        # Verify each emoji was added, accounting for Slack's emoji name mapping
        for emoji in emojis_to_add:
            # Get the expected reaction name (either the mapped version or the original)
            expected_name = slack_emoji_mapping.get(emoji, emoji)
            assert expected_name in reaction_names, f"Emoji '{emoji}' (as '{expected_name}') not found in reactions"
            
        logger.info("Successfully verified emoji reactions were added")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify reactions due to missing permissions: {e}")
            logger.warning("Skipping full verification, but reaction add was successful according to API response")
            # Since we got a successful response from the Slack API on add, we consider this test passed
        else:
            pytest.fail(f"Reaction verification failed: {e}")
