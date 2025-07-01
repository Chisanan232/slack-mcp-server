"""
Protocol definitions for queue backends in the MCP server.

This module defines the interface that all queue backends must implement.
"""

from typing import Any, AsyncIterator, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class QueueBackend(Protocol):
    """Protocol defining the interface for queue backends.

    A queue backend is responsible for publishing messages to a queue and consuming
    messages from a queue. The backend can be any implementation that satisfies
    this protocol, such as in-memory queues, Redis, Kafka, RabbitMQ, etc.
    """

    async def publish(self, key: str, payload: Dict[str, Any]) -> None:
        """Publish a message to the queue.

        Args:
            key: The routing key or topic for the message
            payload: The message payload as a dictionary
        """
        ...

    async def consume(self, *, group: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Consume messages from the queue.

        Args:
            group: Optional consumer group name for group-based consumption
                  patterns such as those in Kafka or Redis Streams

        Returns:
            An async iterator that yields message payloads
        """
        yield {}  # Placeholder for protocol definition

    @classmethod
    def from_env(cls) -> "QueueBackend":
        """Create a backend instance from environment variables.

        This method should read any required configuration from environment
        variables and create a properly configured backend instance.

        Returns:
            A configured instance of the backend
        """
        ...
