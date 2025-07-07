"""
Consumer implementations for processing queue messages.

This module defines the EventConsumer protocol and provides concrete implementations.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol

from slack_mcp.backends.base.protocol import QueueBackend

# Set up logger for this module
logger = logging.getLogger(__name__)


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


class AsyncLoopConsumer(EventConsumer):
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
                    logger.error(f"Error processing message: {e}", exc_info=True)

        self._task = asyncio.create_task(_consume())
        await self._task

    async def shutdown(self) -> None:
        """Stop consuming messages.

        This method cancels the consumer task if it's running.
        It handles various exception scenarios gracefully with appropriate logging.

        Raises:
            RuntimeError: If the shutdown process encounters unexpected errors that
                         aren't related to normal task cancellation.
        """
        if not self._running or not self._task:
            logger.debug("Shutdown called on consumer that is not running")
            return

        logger.debug("Shutting down AsyncLoopConsumer")
        self._running = False

        if not self._task.done():
            logger.debug("Cancelling consumer task")
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                logger.debug("Consumer task cancelled successfully")
            except Exception as e:
                # Log unexpected exceptions but don't re-raise them to ensure cleanup happens
                logger.warning(f"Unexpected error during consumer shutdown: {e}", exc_info=True)
        else:
            logger.debug("Consumer task was already completed")

        # Clean up regardless of how we got here
        self._task = None
        logger.debug("Consumer shutdown complete")
