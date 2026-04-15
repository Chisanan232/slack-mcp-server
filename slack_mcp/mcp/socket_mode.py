"""Socket Mode transport implementation for Slack MCP server.

This module provides WebSocket-based Socket Mode transport for the Slack MCP server,
enabling real-time event processing without requiring public HTTP endpoints.

Socket Mode allows Slack apps to communicate with Slack via WebSocket connections,
which is particularly useful for:
- Applications behind firewalls
- Environments without public HTTP endpoints
- Enhanced security through WebSocket tunneling
"""

import asyncio
import logging
from typing import Any, Optional

from pydantic import SecretStr

_LOG = logging.getLogger(__name__)


class SocketModeHandler:
    """Handler for Slack Socket Mode WebSocket connections.

    This class manages WebSocket connections to Slack's Socket Mode API,
    handling connection lifecycle, event processing, and error recovery.

    Parameters
    ----------
    app_token : SecretStr
        Slack app-level token for Socket Mode authentication (xapp-***)
    bot_token : SecretStr
        Slack bot token for API operations (xoxb-***)
    """

    def __init__(self, app_token: SecretStr, bot_token: SecretStr) -> None:
        """Initialize Socket Mode handler.

        Parameters
        ----------
        app_token : SecretStr
            Slack app-level token for Socket Mode authentication
        bot_token : SecretStr
            Slack bot token for API operations
        """
        self._app_token = app_token
        self._bot_token = bot_token
        self._websocket: Optional[Any] = None
        self._is_running: bool = False
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 5

    async def start(self) -> None:
        """Start the Socket Mode WebSocket connection.

        This method establishes the WebSocket connection to Slack's Socket Mode API
        and begins processing events. It handles automatic reconnection on failure.
        """
        _LOG.info("Starting Socket Mode handler")
        self._is_running = True
        await self._connect_with_retry()

    async def stop(self) -> None:
        """Stop the Socket Mode WebSocket connection.

        This method gracefully closes the WebSocket connection and stops event processing.
        """
        _LOG.info("Stopping Socket Mode handler")
        self._is_running = False
        if self._websocket:
            await self._close_websocket()

    async def _connect_with_retry(self) -> None:
        """Establish WebSocket connection with automatic retry logic.

        This method implements exponential backoff for reconnection attempts
        to handle temporary network issues and WebSocket disconnections.
        """
        while self._is_running and self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                await self._initialize_websocket()
                self._reconnect_attempts = 0
                await self._process_events()
            except Exception as e:
                _LOG.error(f"WebSocket connection failed: {e}")
                self._reconnect_attempts += 1
                if self._is_running:
                    backoff_time = min(2**self._reconnect_attempts, 60)
                    _LOG.info(
                        f"Reconnecting in {backoff_time} seconds (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
                    )
                    await asyncio.sleep(backoff_time)

        if self._reconnect_attempts >= self._max_reconnect_attempts:
            _LOG.error("Max reconnection attempts reached. Socket Mode handler stopped.")

    async def _initialize_websocket(self) -> None:
        """Initialize WebSocket connection to Slack Socket Mode API.

        This method establishes the WebSocket connection using the app token
        and prepares for event processing.
        """
        _LOG.info("Initializing WebSocket connection")
        try:
            from slack_bolt.app.async_app import AsyncApp
            from slack_bolt.socket_mode.async_handler import AsyncSocketModeHandler

            # Create AsyncApp with bot token
            app = AsyncApp(token=self._bot_token.get_secret_value())

            # Create Socket Mode handler with app token
            self._websocket = AsyncSocketModeHandler(app, self._app_token.get_secret_value())

            _LOG.info("WebSocket connection initialized successfully")
        except ImportError as e:
            _LOG.error(f"Failed to import Slack Bolt library: {e}")
            _LOG.error("Please ensure slack-bolt is installed: pip install slack-bolt")
            raise
        except Exception as e:
            _LOG.error(f"Failed to initialize WebSocket connection: {e}")
            raise

    async def _process_events(self) -> None:
        """Process incoming Slack events from WebSocket connection.

        This method continuously processes events received through the WebSocket
        connection and routes them to appropriate handlers.
        """
        _LOG.info("Processing WebSocket events")
        try:
            # Start the Socket Mode handler
            if self._websocket:
                await self._websocket.start_async()
                _LOG.info("WebSocket event processing started successfully")
            else:
                _LOG.error("WebSocket handler not initialized")
                raise RuntimeError("WebSocket handler not initialized")
        except Exception as e:
            _LOG.error(f"Error processing WebSocket events: {e}")
            raise

    async def _close_websocket(self) -> None:
        """Close the WebSocket connection gracefully.

        This method ensures proper cleanup of WebSocket resources.
        """
        _LOG.info("Closing WebSocket connection")
        try:
            if self._websocket:
                # Stop the Socket Mode handler
                await self._websocket.close_async()
                _LOG.info("WebSocket connection closed successfully")
            else:
                _LOG.warning("WebSocket handler not initialized, nothing to close")
        except Exception as e:
            _LOG.error(f"Error closing WebSocket connection: {e}")
            raise
