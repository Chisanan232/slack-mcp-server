"""
Consumer implementations for processing queue messages.

This module defines the EventConsumer protocol and provides concrete implementations.
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

from slack_mcp.backends.protocol import QueueBackend


class EventConsumer(Protocol):
    """Protocol defining the interface for event consumers.

    An event consumer is responsible for processing messages from a queue backend
    and passing them to a handler function.
    """

    async def run(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Run the consumer, processing messages with the given handler.

        Args:
            handler: An async function that will be called with each message payload
        """
        ...

    async def shutdown(self) -> None:
        """Gracefully stop the consumer.

        This method should ensure that any in-flight messages are processed
        before the consumer stops.
        """
        ...


class AsyncLoopConsumer:
    """Simple consumer that processes messages in an asyncio loop.

    This implementation is suitable for light, single-instance deployments.
    It simply wraps the queue backend's consume() method in a loop and
    calls the handler with each message.
    """

    def __init__(self, backend: QueueBackend, group: Optional[str] = None):
        """Initialize the consumer with a queue backend.

        Args:
            backend: The queue backend to consume messages from
            group: Optional consumer group name
        """
        self.backend = backend
        self.group = group
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Start consuming messages and processing them with the handler.

        Args:
            handler: An async function that will be called with each message payload
        """
        if self._running:
            return

        self._running = True

        async def _consume():
            async for message in self.backend.consume(group=self.group):
                try:
                    await handler(message)
                except Exception as e:
                    # In a real implementation, this would include better error handling
                    # such as dead-letter queues, retries, etc.
                    print(f"Error processing message: {e}")

        self._task = asyncio.create_task(_consume())
        await self._task

    async def shutdown(self) -> None:
        """Stop consuming messages.

        This method cancels the consumer task if it's running.
        """
        if self._running and self._task:
            self._running = False
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Normal cancellation
            self._task = None
