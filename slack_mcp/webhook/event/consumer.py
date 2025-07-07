"""
Slack event consumer implementation.

This module provides a consumer that reads events from a queue backend
and routes them to the appropriate event handlers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from slack_mcp.backends.base.consumer import AsyncLoopConsumer
from slack_mcp.backends.base.protocol import QueueBackend

from .handler import EventHandler
from .handler.decorator import DecoratorHandler

__all__ = ["SlackEventConsumer"]

_LOG = logging.getLogger("slack_mcp.webhook.event.consumer")


class SlackEventConsumer(AsyncLoopConsumer):
    """Consumer that pulls events from a queue and routes them to handlers.

    This class connects to a QueueBackend to receive Slack events and passes
    them to the appropriate handler, which can be either:
    1. An object following the EventHandler protocol (OO style)
    2. A DecoratorHandler instance (decorator style)
    """

    def __init__(self, backend: QueueBackend, handler: Optional[EventHandler] = None, group: Optional[str] = None):
        """Initialize the consumer with a backend and optional handler.

        Parameters
        ----------
        backend : QueueBackend
            The queue backend to consume events from
        handler : Optional[EventHandler], optional
            An event handler object (following the EventHandler protocol)
            If not provided, uses a default DecoratorHandler instance
        group : Optional[str], optional
            Consumer group name for queue backends that support consumer groups
        """
        # Initialize the base class
        super().__init__(backend=backend, group=group)
        # Store the Slack-specific handler
        self._slack_handler = handler if handler is not None else DecoratorHandler()
        self._stop = asyncio.Event()

    async def run(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Start consuming events from the queue.

        This method will run indefinitely until shutdown() is called.
        It pulls events from the queue backend and routes them to the handler.
        """
        _LOG.info("Starting Slack event consumer")
        try:
            # Override the base class run method to maintain our original error handling
            async for event in self.backend.consume(group=self.group):
                try:
                    await self._process_event(event)
                except Exception as e:
                    _LOG.exception(f"Error processing Slack event: {e}")

                if self._stop.is_set():
                    _LOG.info("Received stop signal, shutting down")
                    break
        except asyncio.CancelledError:
            _LOG.info("Consumer task was cancelled")
        except Exception as e:
            _LOG.exception(f"Unexpected error in consumer: {e}")
        finally:
            _LOG.info("Slack event consumer stopped")

    async def shutdown(self) -> None:
        """Signal the consumer to gracefully shut down.

        This will cause the run() method to exit after processing any
        current event.
        """
        _LOG.info("Shutting down Slack event consumer")
        self._stop.set()

        # We're handling shutdown ourselves, so we don't need to call the base class method
        # which would cancel the task. Instead, we'll let the run() method exit gracefully
        # when it sees the stop event.

    async def _process_event(self, event: Dict[str, Any]) -> None:
        """Process a single event by routing it to the appropriate handler.

        Parameters
        ----------
        event : Dict[str, Any]
            The Slack event payload
        """
        _LOG.debug(f"Processing event type={event.get('type')}, subtype={event.get('subtype')}")

        # Always use the handler (which is now guaranteed to exist)
        await self._slack_handler.handle_event(event)
