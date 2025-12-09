"""Slack event consumer implementation.

This module provides an asynchronous consumer that reads Slack events from a
message queue backend and routes them to the appropriate event handlers.

What it does
------------
- Pulls events from a queue backend (memory, Redis, Kafka via ABE backends)
- Dispatches events to handlers implementing the `EventHandler` protocol
- Supports both OO-style and decorator-style handlers
- Handles graceful shutdown and error logging

Target audience
---------------
- Developers building background workers that process Slack events
- Integrations that need to react to Slack events outside the HTTP request path

Quick usage
-----------

.. code-block:: python

    import asyncio
    from abe.backends.message_queue.loader import load_backend
    from slack_mcp.webhook.event.consumer import SlackEventConsumer
    from slack_mcp.webhook.event.handler.decorator import DecoratorHandler

    async def main():
        backend = load_backend()  # reads QUEUE_BACKEND env var
        handler = DecoratorHandler()

        @handler.app_mention
        async def on_mention(ev):
            print("Mention received:", ev)

        consumer = SlackEventConsumer(backend, handler=handler)
        await consumer.run(handler=handler.handle_event)

    asyncio.run(main())

Alternative wiring
------------------

.. code-block:: python

    # OO-style handler
    from slack_mcp.webhook.event.handler.base import BaseSlackEventHandler

    class MyOOHandler(BaseSlackEventHandler):
        async def on_message__channels(self, ev):
            print("channel msg:", ev)

    backend = load_backend()
    consumer = SlackEventConsumer(backend, handler=MyOOHandler())
    await consumer.run(handler=consumer._slack_handler.handle_event)

.. code-block:: python

    # Wildcard handler with DecoratorHandler
    from slack_mcp.webhook.event.handler.decorator import DecoratorHandler

    handler = DecoratorHandler()

    @handler
    def on_any(ev):
        print("any:", ev.get("type"))

    consumer = SlackEventConsumer(backend, handler=handler)
    await consumer.run(handler=handler.handle_event)

Testing
-------

.. code-block:: python

    # Example: consume a single event by monkeypatching backend.consume
    import asyncio
    from types import SimpleNamespace

    async def one_event_consume(group=None):
        yield {"type": "message", "channel": "C123", "user": "U123", "text": "hi", "ts": "1"}

    backend = load_backend()
    backend.consume = one_event_consume  # type: ignore[attr-defined]

    handler = DecoratorHandler()
    events = []

    @handler.message
    def on_msg(ev):
        events.append(ev)

    consumer = SlackEventConsumer(backend, handler=handler)
    asyncio.run(consumer.run(handler=handler.handle_event))
    assert events and events[0]["type"] == "message"

Guidelines
----------
- Use `DecoratorHandler` for simple decorator-based registrations
- For complex logic, subclass `BaseSlackEventHandler`
- Call `shutdown()` to stop cleanly (e.g., in signal handler)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from abe.backends.message_queue.base.protocol import MessageQueueBackend
from abe.backends.message_queue.consumer import AsyncLoopConsumer

from .handler import EventHandler
from .handler.decorator import DecoratorHandler

__all__ = ["SlackEventConsumer"]

_LOG = logging.getLogger(__name__)


class SlackEventConsumer(AsyncLoopConsumer):
    """Consume Slack events from a queue and route to handlers.

    This class connects to a `MessageQueueBackend` to receive Slack events and
    forwards them to an event handler.

    Supported handler types
    -----------------------
    - An object following the `EventHandler` protocol (OO style)
    - A `DecoratorHandler` instance (decorator style)

    Examples
    --------
    .. code-block:: python

        consumer = SlackEventConsumer(backend, handler=my_handler)
        await consumer.run(handler=my_handler.handle_event)
    """

    def __init__(
        self, backend: MessageQueueBackend, handler: Optional[EventHandler] = None, group: Optional[str] = None
    ):
        """Initialize the consumer with a backend and optional handler.

        Parameters
        ----------
        backend : MessageQueueBackend
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

        This method runs until `shutdown()` is called. It pulls events from the
        queue backend and routes them to the handler while providing robust
        error logging and graceful cancellation handling.

        Parameters
        ----------
        handler : Callable[[Dict[str, Any]], Awaitable[None]]
            The coroutine function that processes a single Slack event payload.

        Examples
        --------
        .. code-block:: python

            await consumer.run(handler=my_handler.handle_event)
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
