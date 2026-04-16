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

from abe.backends.message_queue.base.protocol import MessageQueueBackend
from abe.backends.message_queue.loader import load_backend
from pydantic import SecretStr

from slack_mcp.settings import get_settings
from slack_mcp.webhook.event.consumer import SlackEventConsumer

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
        self._event_consumer: Optional[SlackEventConsumer] = None
        self._mcp_tools_available: bool = False
        self._queue_backend: Optional[MessageQueueBackend] = None

    async def start(self) -> None:
        """Start the Socket Mode WebSocket connection.

        This method establishes the WebSocket connection to Slack's Socket Mode API
        and begins processing events. It handles automatic reconnection on failure.
        """
        _LOG.info("Starting Socket Mode handler")
        self._is_running = True

        # Initialize queue backend for event publishing
        _LOG.info("Initializing queue backend for Socket Mode")
        self._queue_backend = load_backend()

        await self._connect_with_retry()

    async def stop(self) -> None:
        """Stop the Socket Mode WebSocket connection.

        This method gracefully closes the WebSocket connection and stops event processing.
        """
        _LOG.info("Stopping Socket Mode handler")
        self._is_running = False
        if self._websocket:
            await self._close_websocket()

    def _register_bolt_listeners(self, app: Any) -> None:
        """Register Bolt listeners to publish events to queue backend.

        This method registers a catch-all listener on the AsyncApp that will publish
        all incoming Slack events to the queue backend, allowing the existing
        SlackEventConsumer to process them regardless of event type.

        Parameters
        ----------
        app : Any
            The Slack Bolt AsyncApp instance
        """
        if not self._queue_backend:
            _LOG.warning("Queue backend not available, skipping Bolt listener registration")
            return

        # Get the topic for Slack events from settings
        slack_events_topic = get_settings().slack_events_topic
        _LOG.info(f"Registering catch-all Bolt listener for queue topic: {slack_events_topic}")

        # Use app.message to catch all message events as a catch-all approach
        @app.message
        async def handle_all_events(event: dict[str, Any]) -> None:
            """Handle all events from Socket Mode and publish to queue."""
            event_type = event.get("type", "unknown")
            _LOG.debug(f"Received event via Socket Mode: {event_type}")
            try:
                if self._queue_backend:
                    # Publish event to queue backend
                    import asyncio

                    async def publish_with_error_handling() -> None:
                        """Publish event with proper error handling."""
                        try:
                            if self._queue_backend:
                                await self._queue_backend.publish(slack_events_topic, event)
                                _LOG.debug(f"Published event to queue topic: {slack_events_topic}")
                        except Exception as e:
                            _LOG.error(f"Error publishing event to queue: {e}")

                    asyncio.create_task(publish_with_error_handling())
            except Exception as e:
                _LOG.error(f"Error publishing event to queue: {e}")

        _LOG.info("Catch-all Bolt listener registered successfully")

    def set_mcp_tools_available(self, available: bool) -> None:
        """Set whether MCP tools are available for invocation.

        This method should be called when MCP tools are registered or unregistered
        to ensure the Socket Mode handler can invoke them when processing events.

        Parameters
        ----------
        available : bool
            True if MCP tools are available, False otherwise
        """
        self._mcp_tools_available = available
        _LOG.info(f"MCP tools availability set to: {available}")

    async def invoke_mcp_tool(self, tool_name: str, tool_params: dict[str, Any]) -> dict[str, Any]:
        """Invoke an MCP tool from Socket Mode event handler.

        This method allows Socket Mode events to trigger MCP tool invocations
        for bidirectional communication between Slack and MCP clients.

        Parameters
        ----------
        tool_name : str
            Name of the MCP tool to invoke
        tool_params : dict[str, Any]
            Parameters for the MCP tool

        Returns
        -------
        dict[str, Any]
            Result from the MCP tool invocation

        Raises
        ------
        RuntimeError
            If MCP tools are not available
        """
        if not self._mcp_tools_available:
            _LOG.warning(f"MCP tool {tool_name} invoked but tools are not available")
            raise RuntimeError("MCP tools are not available")

        _LOG.debug(f"Invoking MCP tool: {tool_name} with params: {tool_params}")
        # TODO: Implement actual MCP tool invocation
        # This will connect to the MCP server's tool registry
        # For now, return a placeholder response
        return {"status": "success", "message": f"Tool {tool_name} invoked (placeholder)"}

    async def send_message(self, channel: str, text: str) -> dict[str, Any]:
        """Send a message through the WebSocket connection.

        This method enables bidirectional communication by allowing the
        Socket Mode handler to send messages back to Slack channels.

        Parameters
        ----------
        channel : str
            The channel ID to send the message to
        text : str
            The message text to send

        Returns
        -------
        dict[str, Any]
            Response from Slack API

        Raises
        ------
        RuntimeError
            If WebSocket is not connected
        """
        if not self._websocket:
            _LOG.error("Cannot send message: WebSocket not connected")
            raise RuntimeError("WebSocket not connected")

        _LOG.debug(f"Sending message to channel {channel}: {text[:50]}...")
        # TODO: Implement actual message sending via Slack Bolt app
        # This will use the AsyncApp's client to send messages
        # For now, return a placeholder response
        return {"status": "success", "channel": channel, "message": "Message sent (placeholder)"}

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
                _LOG.error(f"WebSocket connection failed: {e}", exc_info=True)
                self._reconnect_attempts += 1
                if self._is_running:
                    backoff_time = min(2**self._reconnect_attempts, 60)
                    _LOG.warning(
                        f"Reconnecting in {backoff_time} seconds (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
                    )
                    await asyncio.sleep(backoff_time)

        if self._reconnect_attempts >= self._max_reconnect_attempts:
            _LOG.error("Max reconnection attempts reached. Socket Mode handler stopped.")
            _LOG.error("Please check your network connection and token validity")

    async def _initialize_websocket(self) -> None:
        """Initialize WebSocket connection to Slack Socket Mode API.

        This method establishes the WebSocket connection using the app token
        and prepares for event processing.
        """
        _LOG.info("Initializing WebSocket connection to Slack Socket Mode API")
        try:
            from slack_bolt.app.async_app import AsyncApp
            from slack_sdk.socket_mode import SocketModeClient

            # Create AsyncApp with bot token
            _LOG.debug("Creating AsyncApp with bot token")
            app = AsyncApp(token=self._bot_token.get_secret_value())

            # Register Bolt listeners to publish events to queue backend
            if self._queue_backend:
                _LOG.info("Registering Bolt listeners for queue publishing")
                self._register_bolt_listeners(app)

            # Create Socket Mode client with app token
            _LOG.debug("Creating SocketModeClient with app token")
            self._websocket = SocketModeClient(app_token=self._app_token.get_secret_value())

            _LOG.info("WebSocket connection initialized successfully")
        except ImportError as e:
            _LOG.error(f"Failed to import Slack Bolt library: {e}")
            _LOG.error("Please ensure slack-bolt is installed: pip install slack-bolt")
            _LOG.error("Socket Mode requires slack-bolt>=1.28.0 and slack-sdk")
            raise
        except Exception as e:
            _LOG.error(f"Failed to initialize WebSocket connection: {e}", exc_info=True)
            _LOG.error("Please check your app token and bot token are valid")
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

    def _route_event_to_handler(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Route WebSocket events to appropriate handlers.

        This method determines the type of event and routes it to the
        appropriate handler for processing.

        Parameters
        ----------
        event_type : str
            The type of Slack event (e.g., "message", "reaction_added")
        event_data : dict[str, Any]
            The event payload data
        """
        _LOG.debug(f"Routing event type: {event_type}")

        # Integrate with SlackEventConsumer if available
        if self._event_consumer:
            try:
                self._event_consumer.consume(event_data)
                _LOG.debug(f"Event routed to consumer: {event_type}")
            except Exception as e:
                _LOG.error(f"Failed to process event through consumer: {e}")
        else:
            # Fallback to direct routing if consumer not available
            if event_type == "message":
                self._handle_message_event(event_data)
            elif event_type in ["reaction_added", "reaction_removed"]:
                self._handle_reaction_event(event_data)
            else:
                _LOG.warning(f"Unhandled event type: {event_type}")

    def _handle_message_event(self, event_data: dict[str, Any]) -> None:
        """Handle message events from WebSocket.

        Parameters
        ----------
        event_data : dict[str, Any]
            The message event payload
        """
        _LOG.debug(f"Handling message event: {event_data.get('event', {}).get('type')}")
        # Extract message event details
        event = event_data.get("event", {})
        message_type = event.get("type")
        subtype = event.get("subtype")

        # Handle different message types
        if message_type == "message":
            if subtype == "message_changed":
                _LOG.debug("Message edited event detected")
            elif subtype == "message_deleted":
                _LOG.debug("Message deleted event detected")
            elif subtype == "bot_message":
                _LOG.debug("Bot message event detected")
            else:
                _LOG.debug("New message event detected")
        else:
            _LOG.warning(f"Unknown message event type: {message_type}")

    def _handle_reaction_event(self, event_data: dict[str, Any]) -> None:
        """Handle reaction events from WebSocket.

        Parameters
        ----------
        event_data : dict[str, Any]
            The reaction event payload
        """
        _LOG.debug(f"Handling reaction event: {event_data.get('event', {}).get('type')}")
        # Extract reaction event details
        event = event_data.get("event", {})
        reaction_type = event.get("type")
        reaction = event.get("reaction")
        user = event.get("user")
        item = event.get("item")

        # Handle different reaction types
        if reaction_type == "reaction_added":
            _LOG.debug(f"Reaction added: {reaction} by user {user} to item {item}")
        elif reaction_type == "reaction_removed":
            _LOG.debug(f"Reaction removed: {reaction} by user {user} from item {item}")
        else:
            _LOG.warning(f"Unknown reaction event type: {reaction_type}")

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
