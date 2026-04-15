"""Unit tests for the Socket Mode handler."""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest
from pydantic import SecretStr

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

        # Mock the import to raise ImportError
        with mock.patch("slack_bolt.app.async_app.AsyncApp", side_effect=ImportError("No module named 'slack_bolt'")):
            with pytest.raises(ImportError):
                await handler._initialize_websocket()

    @pytest.mark.asyncio
    async def test_websocket_initialization_success(self) -> None:
        """Test successful WebSocket initialization."""
        app_token = SecretStr("xapp-test-token-123456")
        bot_token = SecretStr("xoxb-test-token-123456")

        handler = SocketModeHandler(app_token=app_token, bot_token=bot_token)

        # Mock the Bolt library imports
        mock_app = mock.MagicMock()
        mock_handler = mock.MagicMock()

        with mock.patch("slack_bolt.app.async_app.AsyncApp", return_value=mock_app):
            with mock.patch("slack_bolt.socket_mode.async_handler.AsyncSocketModeHandler", return_value=mock_handler):
                await handler._initialize_websocket()

                assert handler._websocket == mock_handler

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

        # Mock _initialize_websocket to always fail
        with mock.patch.object(handler, "_initialize_websocket", side_effect=Exception("Connection failed")):
            # Run the retry logic
            await handler._connect_with_retry()

        # Should have reached max attempts
        assert handler._reconnect_attempts == 2
