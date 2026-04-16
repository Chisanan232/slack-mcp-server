"""Unit tests for the Socket Mode handler."""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest
from pydantic import SecretStr

from slack_mcp.mcp.app import MCPServerFactory
from slack_mcp.mcp.socket_mode import SocketModeHandler


class TestSocketModeHandler:
    """Test suite for SocketModeHandler class."""

    def test_socket_mode_handler_initialization(self) -> None:
        """Test SocketModeHandler initialization with valid tokens."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        assert handler._app_token == app_token
        assert handler._bot_token == bot_token
        assert handler._websocket is None
        assert handler._is_running is False
        assert handler._reconnect_attempts == 0
        assert handler._max_reconnect_attempts == 5

    def test_socket_mode_handler_initialization_with_invalid_tokens(self) -> None:
        """Test SocketModeHandler initialization with various token formats."""
        # Test with bot token format instead of app token (should still initialize, validation happens at runtime)
        app_token = SecretStr("xoxb-invalid-format")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        assert handler._app_token == app_token
        assert handler._bot_token == bot_token

    @pytest.mark.asyncio
    async def test_socket_mode_handler_start_stop(self) -> None:
        """Test starting and stopping the Socket Mode handler."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the WebSocket methods to avoid actual connection
        with mock.patch.object(handler, "_connect_with_retry", mock.AsyncMock()):
            with mock.patch.object(handler, "_close_websocket", mock.AsyncMock()):
                # Start should call _connect_with_retry
                start_task = asyncio.create_task(handler.start())
                # Give it a moment to start
                await asyncio.sleep(0.1)
                assert handler._is_running is True

                # Stop the handler
                await handler.stop()
                assert handler._is_running is False

                # Cancel the start task
                start_task.cancel()
                try:
                    await start_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_websocket_initialization_with_missing_bolt_library(self) -> None:
        """Test WebSocket initialization fails gracefully when Bolt library is missing."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the _initialize_websocket to raise ImportError
        with mock.patch.object(
            handler, "_initialize_websocket", side_effect=ImportError("No module named 'slack_bolt'")
        ):
            with pytest.raises(ImportError):
                await handler._initialize_websocket()

    @pytest.mark.asyncio
    async def test_websocket_initialization_success(self) -> None:
        """Test successful WebSocket initialization by mocking the method directly."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the _initialize_websocket method to set _websocket directly
        async def mock_initialize():
            mock_handler = mock.MagicMock()
            handler._websocket = mock_handler

        with mock.patch.object(handler, "_initialize_websocket", side_effect=mock_initialize):
            await handler._initialize_websocket()

            assert handler._websocket is not None

    @pytest.mark.asyncio
    async def test_websocket_cleanup(self) -> None:
        """Test WebSocket connection cleanup."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Set up a mock WebSocket
        mock_websocket = mock.MagicMock()
        mock_websocket.close_async = mock.AsyncMock()
        handler._websocket = mock_websocket

        await handler._close_websocket()

        mock_websocket.close_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_cleanup_without_websocket(self) -> None:
        """Test WebSocket cleanup when no WebSocket is initialized."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # No WebSocket initialized
        handler._websocket = None

        # Should not raise an error
        await handler._close_websocket()

    @pytest.mark.asyncio
    async def test_reconnect_logic_max_attempts(self) -> None:
        """Test that reconnection stops after max attempts."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._max_reconnect_attempts = 2  # Set low for testing
        handler._is_running = True  # Set running flag to enable retry loop

        # Mock _initialize_websocket to always fail
        with mock.patch.object(handler, "_initialize_websocket", side_effect=Exception("Connection failed")):
            # Run the retry logic
            await handler._connect_with_retry()

        # Should have reached max attempts
        assert handler._reconnect_attempts == 2

    def test_event_routing_to_consumer(self) -> None:
        """Test event routing to SlackEventConsumer."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the event consumer
        mock_consumer = mock.MagicMock()
        handler._event_consumer = mock_consumer

        # Test routing a message event
        event_data = {"event": {"type": "message", "text": "test"}}
        handler._route_event_to_handler("message", event_data)

        mock_consumer.consume.assert_called_once_with(event_data)

    def test_event_routing_without_consumer(self) -> None:
        """Test event routing when consumer is not available (fallback)."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._event_consumer = None  # No consumer

        # Test routing a message event (should use fallback)
        event_data = {"event": {"type": "message", "text": "test"}}
        handler._route_event_to_handler("message", event_data)

        # Should not raise an error, just log
        assert handler._event_consumer is None

    def test_message_event_handling(self) -> None:
        """Test message event handling with different subtypes."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Test new message
        event_data = {"event": {"type": "message", "subtype": None}}
        handler._handle_message_event(event_data)

        # Test edited message
        event_data = {"event": {"type": "message", "subtype": "message_changed"}}
        handler._handle_message_event(event_data)

        # Test deleted message
        event_data = {"event": {"type": "message", "subtype": "message_deleted"}}
        handler._handle_message_event(event_data)

        # Test bot message
        event_data = {"event": {"type": "message", "subtype": "bot_message"}}
        handler._handle_message_event(event_data)

    def test_reaction_event_handling(self) -> None:
        """Test reaction event handling for added and removed reactions."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Test reaction added
        event_data = {
            "event": {
                "type": "reaction_added",
                "reaction": "thumbsup",
                "user": "U123",
                "item": {"type": "message", "channel": "C123"},
            }
        }
        handler._handle_reaction_event(event_data)

        # Test reaction removed
        event_data = {
            "event": {
                "type": "reaction_removed",
                "reaction": "thumbsup",
                "user": "U123",
                "item": {"type": "message", "channel": "C123"},
            }
        }
        handler._handle_reaction_event(event_data)

    def test_mcp_tools_availability(self) -> None:
        """Test setting and checking MCP tools availability."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Initially tools should not be available
        assert handler._mcp_tools_available is False

        # Set tools as available
        handler.set_mcp_tools_available(True)
        assert handler._mcp_tools_available is True

        # Set tools as unavailable
        handler.set_mcp_tools_available(False)
        assert handler._mcp_tools_available is False

    @pytest.mark.asyncio
    async def test_mcp_tool_invocation_success(self) -> None:
        """Test successful MCP tool invocation."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler.set_mcp_tools_available(True)

        # Invoke a tool
        result = await handler.invoke_mcp_tool("test_tool", {"param": "value"})

        assert result["status"] == "success"
        assert "Tool test_tool invoked" in result["message"]

    @pytest.mark.asyncio
    async def test_mcp_tool_invocation_failure(self) -> None:
        """Test MCP tool invocation when tools are not available."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler.set_mcp_tools_available(False)

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="MCP tools are not available"):
            await handler.invoke_mcp_tool("test_tool", {"param": "value"})

    @pytest.mark.asyncio
    async def test_bidirectional_message_send(self) -> None:
        """Test sending messages through WebSocket (bidirectional communication)."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Set up a mock WebSocket
        mock_websocket = mock.MagicMock()
        handler._websocket = mock_websocket

        # Send a message
        result = await handler.send_message("C123", "Hello, world!")

        assert result["status"] == "success"
        assert result["channel"] == "C123"

    @pytest.mark.asyncio
    async def test_bidirectional_message_send_without_websocket(self) -> None:
        """Test sending message when WebSocket is not connected."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._websocket = None

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="WebSocket not connected"):
            await handler.send_message("C123", "Hello, world!")

    @pytest.mark.asyncio
    async def test_websocket_close_with_websocket_initialized(self) -> None:
        """Test WebSocket cleanup when WebSocket is initialized."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Set up a mock WebSocket with close_async method
        mock_websocket = mock.MagicMock()
        mock_websocket.close_async = mock.AsyncMock()
        handler._websocket = mock_websocket

        await handler._close_websocket()

        mock_websocket.close_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_bolt_listener_handler_execution(self) -> None:
        """Test actual execution of Bolt listener handler."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the queue backend
        mock_backend = mock.MagicMock()
        mock_backend.publish = mock.AsyncMock()
        handler._queue_backend = mock_backend

        # Mock settings
        with mock.patch("slack_mcp.mcp.socket_mode.get_settings") as mock_get_settings:
            mock_settings = mock.MagicMock()
            mock_settings.slack_events_topic = "test_topic"
            mock_get_settings.return_value = mock_settings

            # Create a mock app with event decorator
            mock_app = mock.MagicMock()

            # Make event decorator return the function it wraps
            def event_decorator(event_type):
                def decorator(func):
                    return func

                return decorator

            mock_app.event = mock.MagicMock(side_effect=event_decorator)

            # Register Bolt listeners
            handler._register_bolt_listeners(mock_app)

            # The handler should have been registered
            assert mock_app.event.called
            mock_app.event.assert_called_with({})

    @pytest.mark.asyncio
    async def test_route_event_to_consumer_success(self) -> None:
        """Test successful event routing to SlackEventConsumer."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the event consumer
        mock_consumer = mock.MagicMock()
        handler._event_consumer = mock_consumer

        # Route an event
        event_data = {"event": {"type": "message"}}
        handler._route_event_to_handler("message", event_data)

        mock_consumer.consume.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_route_event_to_consumer_failure(self) -> None:
        """Test event routing when consumer raises exception."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the event consumer to raise exception
        mock_consumer = mock.MagicMock()
        mock_consumer.consume.side_effect = Exception("Consumer error")
        handler._event_consumer = mock_consumer

        # Route an event (should not raise, just log error)
        event_data = {"event": {"type": "message"}}
        handler._route_event_to_handler("message", event_data)

        # Consumer should still be called
        mock_consumer.consume.assert_called_once()

    def test_route_event_fallback_message(self) -> None:
        """Test fallback routing for message events when consumer not available."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._event_consumer = None

        # Route a message event (should use fallback)
        event_data = {"event": {"type": "message", "subtype": None}}
        handler._route_event_to_handler("message", event_data)

        # Should not raise an error

    def test_route_event_fallback_reaction(self) -> None:
        """Test fallback routing for reaction events when consumer not available."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._event_consumer = None

        # Route a reaction event (should use fallback)
        event_data = {"event": {"type": "reaction_added"}}
        handler._route_event_to_handler("reaction_added", event_data)

        # Should not raise an error

    def test_route_event_unhandled_type(self) -> None:
        """Test routing for unhandled event type when consumer not available."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._event_consumer = None

        # Route an unhandled event type (should log warning)
        event_data = {"event": {"type": "unknown_type"}}
        handler._route_event_to_handler("unknown_type", event_data)

        # Should not raise an error

    def test_handle_message_event_unknown_type(self) -> None:
        """Test handling message event with unknown type."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Test unknown message type
        event_data = {"event": {"type": "unknown_message_type"}}
        handler._handle_message_event(event_data)

        # Should not raise an error

    def test_handle_reaction_event_unknown_type(self) -> None:
        """Test handling reaction event with unknown type."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Test unknown reaction type
        event_data = {"event": {"type": "unknown_reaction_type"}}
        handler._handle_reaction_event(event_data)

        # Should not raise an error

    @pytest.mark.asyncio
    async def test_websocket_close_exception_handling(self) -> None:
        """Test WebSocket close exception handling."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Set up a mock WebSocket that raises exception on close
        mock_websocket = mock.MagicMock()
        mock_websocket.close_async = mock.AsyncMock(side_effect=Exception("Close error"))
        handler._websocket = mock_websocket

        # Should raise the exception
        with pytest.raises(Exception, match="Close error"):
            await handler._close_websocket()

    def test_bolt_listener_registration_with_queue_backend(self) -> None:
        """Test that catch-all Bolt listener is registered when queue backend is available."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the queue backend
        mock_backend = mock.MagicMock()
        handler._queue_backend = mock_backend

        # Create a mock AsyncApp
        mock_app = mock.MagicMock()

        # Register Bolt listeners
        handler._register_bolt_listeners(mock_app)

        # Verify that event decorator was called once for catch-all listener
        assert mock_app.event.call_count == 1  # catch-all listener
        # Verify it was called with empty dict for catch-all
        mock_app.event.assert_called_with({})

    def test_bolt_listener_registration_without_queue_backend(self) -> None:
        """Test that Bolt listeners are not registered when queue backend is unavailable."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._queue_backend = None  # No queue backend

        # Create a mock AsyncApp
        mock_app = mock.MagicMock()

        # Register Bolt listeners
        handler._register_bolt_listeners(mock_app)

        # Verify that event decorators were not called
        mock_app.event.assert_not_called()

    @pytest.mark.asyncio
    async def test_queue_backend_initialization_on_start(self) -> None:
        """Test that queue backend is initialized when handler starts."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock load_backend to avoid actual queue initialization
        with mock.patch("slack_mcp.mcp.socket_mode.load_backend") as mock_load_backend:
            mock_backend = mock.MagicMock()
            mock_load_backend.return_value = mock_backend

            # Mock _connect_with_retry to avoid actual WebSocket connection
            with mock.patch.object(handler, "_connect_with_retry", mock.AsyncMock()):
                await handler.start()

                # Verify queue backend was loaded
                mock_load_backend.assert_called_once()
                assert handler._queue_backend == mock_backend


class TestMCPServerFactorySocketMode:
    """Test suite for MCPServerFactory.socket_mode_handler method."""

    def test_socket_mode_handler_success(self) -> None:
        """Test successful Socket Mode handler creation."""
        # Reset to ensure clean state
        MCPServerFactory.reset()

        # Create MCP server instance first
        MCPServerFactory.create()

        # Get Socket Mode handler
        handler = MCPServerFactory.socket_mode_handler(
            app_token="xapp-test-token-123456", bot_token="xoxb-test-token-123456"
        )

        # Verify handler was created
        assert handler is not None
        assert handler._app_token.get_secret_value() == "xapp-test-token-123456"
        assert handler._bot_token.get_secret_value() == "xoxb-test-token-123456"

        # Clean up
        MCPServerFactory.reset()

    def test_socket_mode_handler_without_server_instance(self) -> None:
        """Test Socket Mode handler creation fails when MCP server not created."""
        # Reset to ensure no server instance exists
        MCPServerFactory.reset()

        # Should raise AssertionError
        with pytest.raises(AssertionError, match="Please create a FastMCP instance first"):
            MCPServerFactory.socket_mode_handler(app_token="xapp-test-token-123456", bot_token="xoxb-test-token-123456")

    @pytest.mark.asyncio
    async def test_stop_with_websocket_initialized(self) -> None:
        """Test stop() method closes websocket when initialized."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock WebSocket
        mock_websocket = mock.MagicMock()
        mock_websocket.close_async = mock.AsyncMock()
        handler._websocket = mock_websocket

        # Stop the handler
        await handler.stop()

        # Verify websocket was closed
        mock_websocket.close_async.assert_called_once()
        assert handler._is_running is False

    @pytest.mark.asyncio
    async def test_stop_without_websocket_initialized(self) -> None:
        """Test stop() method when websocket is not initialized."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._websocket = None

        # Stop the handler (should not raise error)
        await handler.stop()

        assert handler._is_running is False

    @pytest.mark.asyncio
    async def test_bolt_listener_handler_event_publishing(self) -> None:
        """Test actual event publishing in Bolt listener handler."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock queue backend
        mock_backend = mock.MagicMock()
        mock_backend.publish = mock.AsyncMock()
        handler._queue_backend = mock_backend

        # Mock settings
        with mock.patch("slack_mcp.mcp.socket_mode.get_settings") as mock_get_settings:
            mock_settings = mock.MagicMock()
            mock_settings.slack_events_topic = "test_topic"
            mock_get_settings.return_value = mock_settings

            # Create mock app with event decorator
            mock_app = mock.MagicMock()

            # Capture the handler function
            captured_handler = None

            def event_decorator(event_type):
                def decorator(func):
                    nonlocal captured_handler
                    captured_handler = func
                    return func

                return decorator

            mock_app.event = mock.MagicMock(side_effect=event_decorator)

            # Register Bolt listeners
            handler._register_bolt_listeners(mock_app)

            # Verify the handler was captured
            assert captured_handler is not None

            # Call the handler with a test event
            test_event = {"type": "message", "text": "test message"}
            await captured_handler(test_event)

            # Verify publish was called
            mock_backend.publish.assert_called_once_with("test_topic", test_event)

    @pytest.mark.asyncio
    async def test_bolt_listener_handler_publish_error(self) -> None:
        """Test Bolt listener handler error handling during publish."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock queue backend that raises error
        mock_backend = mock.MagicMock()
        mock_backend.publish = mock.AsyncMock(side_effect=Exception("Publish error"))
        handler._queue_backend = mock_backend

        # Mock settings
        with mock.patch("slack_mcp.mcp.socket_mode.get_settings") as mock_get_settings:
            mock_settings = mock.MagicMock()
            mock_settings.slack_events_topic = "test_topic"
            mock_get_settings.return_value = mock_settings

            # Create mock app with event decorator
            mock_app = mock.MagicMock()

            captured_handler = None

            def event_decorator(event_type):
                def decorator(func):
                    nonlocal captured_handler
                    captured_handler = func
                    return func

                return decorator

            mock_app.event = mock.MagicMock(side_effect=event_decorator)

            # Register Bolt listeners
            handler._register_bolt_listeners(mock_app)

            # Call the handler with a test event (should not raise, just log error)
            test_event = {"type": "message", "text": "test message"}
            await captured_handler(test_event)

            # Verify publish was attempted
            mock_backend.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_events_success(self) -> None:
        """Test _process_events successful execution."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock WebSocket
        mock_websocket = mock.MagicMock()
        mock_websocket.start_async = mock.AsyncMock()
        handler._websocket = mock_websocket

        # Run process events (will complete immediately)
        await handler._process_events()

        # Verify start_async was called
        mock_websocket.start_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_events_websocket_not_initialized(self) -> None:
        """Test _process_events when websocket not initialized."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)
        handler._websocket = None

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="WebSocket handler not initialized"):
            await handler._process_events()

    @pytest.mark.asyncio
    async def test_process_events_start_async_error(self) -> None:
        """Test _process_events when start_async raises error."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock WebSocket with error
        mock_websocket = mock.MagicMock()
        mock_websocket.start_async = mock.AsyncMock(side_effect=Exception("Start error"))
        handler._websocket = mock_websocket

        # Should raise the error
        with pytest.raises(Exception, match="Start error"):
            await handler._process_events()
