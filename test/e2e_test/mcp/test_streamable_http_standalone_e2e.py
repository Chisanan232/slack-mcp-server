"""End-to-end tests for Streamable-HTTP transport in standalone mode."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from test.e2e_test.common_utils import get_e2e_credentials, should_run_e2e_tests
from test.e2e_test.mcp.http_test_utils import (
    get_free_port,
    http_mcp_client_session,
    http_mcp_server,
    initialize_and_test_tools,
    safe_call_tool,
)
from test.e2e_test.slack_retry_utils import retry_slack_api_call
from typing import Any, Dict

import pytest

from slack_mcp.client.factory import RetryableSlackClientFactory

pytestmark = pytest.mark.asyncio

# Set up logging for better diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


@retry_slack_api_call
async def _add_reaction(client, channel, name, timestamp):
    return await client.reactions_add(channel=channel, name=name, timestamp=timestamp)


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_standalone_post_message_e2e() -> None:  # noqa: D401 – E2E
    """Test posting a message via Streamable-HTTP transport in standalone mode."""
    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()

    unique_text = f"mcp-e2e-streamable-http-standalone-{uuid.uuid4()}"

    logger.info(f"Testing Streamable-HTTP standalone with channel ID: {channel_id}")
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

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP standalone server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="streamable-http",
        integrated=False,
        port=port,
        mount_path=None,  # streamable-http doesn't use mount_path
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=None, integrated=False
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
                f"Message successfully sent via Streamable-HTTP standalone with timestamp: {slack_response.get('ts')}"
            )

    # Verify message was delivered
    await asyncio.sleep(1)
    try:
        client = client_factory.create_async_client(token=bot_token)
        history = await _get_conversation_history(client, channel=channel_id, limit=10)
        messages = history.get("messages", [])
        found = any(msg.get("text") == unique_text for msg in messages)
        assert found, "Message not found in channel history"
        logger.info("Streamable-HTTP standalone message successfully verified in channel history")
    except Exception as e:
        if "missing_scope" in str(e):
            logger.warning(f"Cannot verify message due to missing permissions: {e}")
        else:
            pytest.fail(f"Message verification failed: {e}")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_standalone_add_reactions_e2e() -> None:  # noqa: D401 – E2E
    """Test adding emoji reactions via Streamable-HTTP transport in standalone mode."""
    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()

    unique_text = f"mcp-e2e-streamable-http-standalone-reaction-{uuid.uuid4()}"

    logger.info(f"Testing Streamable-HTTP standalone reactions with channel ID: {channel_id}")

    # Create a test message to react to
    message_ts = None
    try:
        test_client = client_factory.create_async_client(token=bot_token)
        message_response = await _post_message(test_client, channel=channel_id, text=unique_text)
        assert message_response["ok"] is True, "Failed to send test message"
        message_ts = message_response["ts"]
        logger.info(f"Created test message with timestamp: {message_ts}")
    except Exception as e:
        pytest.fail(f"Slack API setup failed: {e}")

    # Get a free port for testing
    port = get_free_port()

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP standalone server on port {port}")

    # Define emojis to add as reactions
    emojis_to_add = ["thumbsup", "heart"]

    # Start server and run test
    async with http_mcp_server(
        transport="streamable-http",
        integrated=False,
        port=port,
        mount_path=None,  # streamable-http doesn't use mount_path
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=None, integrated=False
        ) as session:
            # Initialize session and verify tools
            expected_tools = ["slack_add_reactions"]
            await initialize_and_test_tools(session, expected_tools)

            # Call slack_add_reactions tool with timeout protection
            logger.info(f"Calling slack_add_reactions tool with channel: {channel_id} and message ts: {message_ts}")
            result = await safe_call_tool(
                session,
                "slack_add_reactions",
                {
                    "input_params": {
                        "channel": channel_id,
                        "timestamp": message_ts,
                        "emojis": emojis_to_add,
                    }
                },
            )

            # Verify the result is successful
            assert result.isError is False, f"Tool execution failed: {result.content}"
            assert len(result.content) > 0, "Expected non-empty content in response"

            # Extract and parse response
            text_content = result.content[0]
            slack_response = json.loads(text_content.text)

            # Verify the result has expected structure
            assert "responses" in slack_response, "Missing 'responses' field in Slack response"
            assert isinstance(slack_response["responses"], list), "'responses' should be a list"
            assert len(slack_response["responses"]) == len(emojis_to_add), f"Expected {len(emojis_to_add)} responses"

            # Check each response for the emoji reactions
            for i, emoji in enumerate(emojis_to_add):
                response = slack_response["responses"][i]
                assert response.get("ok") is True, f"Slack API returned error for emoji {emoji}: {response}"

            logger.info("Successfully added emoji reactions via Streamable-HTTP standalone")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_standalone_read_emojis_e2e() -> None:  # noqa: D401 – E2E
    """Test reading emoji list via Streamable-HTTP transport in standalone mode."""
    # Get required values from settings
    from test.settings import get_test_environment

    from slack_mcp.settings import get_settings

    test_env = get_test_environment()
    settings = get_settings()
    bot_token = test_env.e2e_test_api_token.get_secret_value() if test_env.e2e_test_api_token else None

    if not bot_token:
        pytest.fail("E2E_TEST_API_TOKEN not set")

    logger.info("Testing Streamable-HTTP standalone read emojis")

    # Get a free port for testing
    port = get_free_port()

    # Prepare server environment
    server_env: Dict[str, Any] = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP standalone server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="streamable-http",
        integrated=False,
        port=port,
        mount_path=None,  # streamable-http doesn't use mount_path
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=None, integrated=False
        ) as session:
            # Initialize session and verify tools
            expected_tools = ["slack_read_emojis"]
            await initialize_and_test_tools(session, expected_tools)

            # Call slack_read_emojis tool with timeout protection
            logger.info("Calling slack_read_emojis tool")
            result = await safe_call_tool(session, "slack_read_emojis", {"input_params": {}})

            # Verify the result is successful
            assert result.isError is False, f"Tool execution failed: {result.content}"
            assert len(result.content) > 0, "Expected non-empty content in response"

            # Extract and parse response
            text_content = result.content[0]
            slack_response = json.loads(text_content.text)

            # Verify Slack API response
            assert slack_response.get("ok") is True, f"Slack API returned error: {slack_response}"
            assert "emoji" in slack_response, "Missing emoji data in Slack response"

            emoji_data = slack_response.get("emoji", {})
            logger.info(f"Successfully read {len(emoji_data)} emojis via Streamable-HTTP standalone")


@pytest.mark.skipif(
    not should_run_e2e_tests(),
    reason="Real Slack credentials (E2E_TEST_API_TOKEN, SLACK_TEST_CHANNEL_ID) not provided – skipping E2E test.",
)
async def test_streamable_http_standalone_thread_operations_e2e() -> None:  # noqa: D401 – E2E
    """Test thread operations via Streamable-HTTP transport in standalone mode."""
    # Get required values from settings
    bot_token, channel_id = get_e2e_credentials()

    unique_parent_text = f"mcp-e2e-streamable-http-standalone-parent-{uuid.uuid4()}"
    unique_reply_texts = [f"mcp-e2e-streamable-http-standalone-reply1-{uuid.uuid4()}"]

    logger.info(f"Testing Streamable-HTTP standalone thread operations with channel ID: {channel_id}")

    # First, post a parent message and add replies to create a thread
    try:
        client = client_factory.create_async_client(token=bot_token)
        parent_response = await _post_message(client, channel=channel_id, text=unique_parent_text)
        assert parent_response["ok"] is True, "Failed to send parent message"
        parent_ts = parent_response["ts"]

        # Add a reply to create the thread
        reply_response = await _post_message(
            client, channel=channel_id, text=unique_reply_texts[0], thread_ts=parent_ts
        )
        assert reply_response["ok"] is True, "Failed to send reply message"

        logger.info(f"Created thread with parent timestamp: {parent_ts}")
    except Exception as e:
        pytest.fail(f"Failed to create test thread: {e}")

    # Get a free port for testing
    port = get_free_port()

    # Prepare server environment
    server_env = {"E2E_TEST_API_TOKEN": bot_token}

    logger.info(f"Starting Streamable-HTTP standalone server on port {port}")

    # Start server and run test
    async with http_mcp_server(
        transport="streamable-http",
        integrated=False,
        port=port,
        mount_path=None,  # streamable-http doesn't use mount_path
        env=server_env,
    ) as server:
        async with http_mcp_client_session(
            transport="streamable-http", base_url=server.base_url, mount_path=None, integrated=False
        ) as session:
            # Initialize session and verify tools
            expected_tools = ["slack_read_thread_messages"]
            await initialize_and_test_tools(session, expected_tools)

            # Call slack_read_thread_messages tool with timeout protection
            logger.info(
                f"Calling slack_read_thread_messages tool with channel: {channel_id} and thread_ts: {parent_ts}"
            )
            result = await safe_call_tool(
                session,
                "slack_read_thread_messages",
                {
                    "input_params": {
                        "channel": channel_id,
                        "thread_ts": parent_ts,
                    }
                },
            )

            # Verify the result is successful
            assert result.isError is False, f"Tool execution failed: {result.content}"
            assert len(result.content) > 0, "Expected non-empty content in response"

            # Extract and parse response
            text_content = result.content[0]
            slack_response = json.loads(text_content.text)

            # Verify the result is successful
            assert slack_response.get("ok") is True, f"Slack API returned error: {slack_response}"
            assert "messages" in slack_response, "Missing messages in Slack response"

            # Verify we got at least 2 messages (parent + 1 reply)
            messages = slack_response["messages"]
            assert len(messages) >= 2, f"Expected at least 2 messages, got {len(messages)}"

            # Verify message content
            assert messages[0]["ts"] == parent_ts, "First message should be the parent message"

            # Check for our unique messages in the thread
            found_parent = any(msg["text"] == unique_parent_text for msg in messages)
            found_reply = any(msg["text"] == unique_reply_texts[0] for msg in messages)

            assert found_parent, "Parent message not found in thread"
            assert found_reply, "Reply message not found in thread"

            logger.info("Thread messages successfully read via Streamable-HTTP standalone")
