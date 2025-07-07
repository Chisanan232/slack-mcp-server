"""
In-memory implementation of the QueueBackend protocol.

This implementation is intended for development and testing only.
It uses an asyncio.Queue to store messages in memory, which means:
1. Messages are lost when the process restarts
2. Messages are only visible to consumers in the same process
"""

import asyncio
import logging
import warnings
from typing import Any, AsyncIterator, Dict, Optional, Tuple

from slack_mcp.backends.base.protocol import QueueBackend

# Set up logger for the memory backend
logger = logging.getLogger(__name__)


class MemoryBackend(QueueBackend):
    """In-memory implementation of QueueBackend using asyncio.Queue.

    This class is intended for development and testing only.
    Messages are stored in a class-level asyncio.Queue to simulate
    a message broker, but only work within a single process.
    """

    # Class-level queue shared by all instances
    _queue: "asyncio.Queue[Tuple[str, Dict[str, Any]]]" = asyncio.Queue()

    @classmethod
    def from_env(cls) -> "MemoryBackend":
        """Create a new MemoryBackend instance from environment variables.

        For the memory backend, no environment variables are required.
        This method also prints a warning about using this backend for development only.

        Returns:
            A new MemoryBackend instance
        """
        warnings.warn(
            "⚠️  Memory backend is for development/testing only. "
            "Messages will be lost on restart and are only visible to consumers in the same process.",
            UserWarning,
        )
        return cls()

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Publish a message to the in-memory queue.

        Args:
            key: The routing key for the message
            payload: The message payload as a dictionary
        """
        await self._queue.put((key, payload))

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Consume messages from the in-memory queue.

        The group parameter is ignored in the memory backend implementation
        as it doesn't support consumer groups.

        Args:
            group: Ignored in this implementation

        Yields:
            Message payloads in the order they were published
        """
        message_in_progress = False
        try:
            while True:
                try:
                    # Get next message but ignore the key
                    message_in_progress = True
                    _, payload = await self._queue.get()

                    # Mark the message as processed before yielding to ensure proper queue accounting
                    # even if the consumer doesn't fully process the message
                    try:
                        self._queue.task_done()
                    except ValueError:
                        # Handle "task_done() called too many times" error gracefully
                        logger.warning("task_done() called too many times - this may indicate a queue accounting issue")

                    message_in_progress = False
                    yield payload
                except asyncio.CancelledError:
                    logger.debug("Consume operation was cancelled")
                    # If we were in the middle of getting a message, mark it as done
                    # so it's not left in a "processing" state
                    if message_in_progress:
                        try:
                            self._queue.task_done()
                        except ValueError:
                            # Safely handle potential "task_done() called too many times" error
                            logger.warning("task_done() called too many times during cancellation")
                    raise  # Re-raise to allow proper asyncio cancellation handling
        except asyncio.CancelledError:
            # Catch at the outer level to properly handle cancellation during yield
            logger.debug("Consumer task was cancelled, shutting down gracefully")
            # No need to re-raise here as this is the outermost handler
        except Exception as e:
            # Log unexpected errors but don't crash
            logger.error(f"Unexpected error in memory backend consumer: {e}", exc_info=True)
            raise  # Re-raise to allow caller to handle
