"""Client manager for Slack web clients.

This module provides a centralized way to manage Slack web client instances
created by factory objects. It implements a singleton pattern to ensure
that only one client is created per token, improving resource utilization
and consistency across the application.
"""

from __future__ import annotations

import logging
import os
from typing import ClassVar, Dict, Final, Optional

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp.client.factory import (
    DefaultSlackClientFactory,
    RetryableSlackClientFactory,
    SlackClientFactory,
)

__all__: list[str] = [
    "SlackClientManager",
    "get_client_manager",
]

# Logger for this module
_LOG: Final[logging.Logger] = logging.getLogger("slack_mcp.client.manager")


class SlackClientManager:
    """Manages Slack web client instances.

    This class provides a centralized way to create, retrieve, and manage
    Slack web client instances. It uses a singleton pattern to ensure that
    only one client is created per token, improving resource utilization.
    """

    # Class variable for the singleton instance
    _instance: ClassVar[Optional[SlackClientManager]] = None

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of SlackClientManager exists."""
        if cls._instance is None:
            cls._instance = super(SlackClientManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, retry_count: int = 3):
        """Initialize the SlackClientManager.

        Parameters
        ----------
        retry_count : int, optional
            The default retry count to use for retryable clients, by default 3.
        """
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        self._default_retry_count = retry_count

        # Client caches - keyed by token
        self._async_clients: Dict[str, AsyncWebClient] = {}
        self._sync_clients: Dict[str, WebClient] = {}

        self._initialized = True
        _LOG.debug("SlackClientManager singleton initialized")

    @property
    def _default_token(self) -> Optional[str]:
        """Get the default token from environment variables.

        Returns
        -------
        Optional[str]
            The default token from environment variables, or None if not found.
        """
        return os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_TOKEN")

    def get_async_client(self, token: Optional[str] = None, use_retries: bool = True) -> AsyncWebClient:
        """Get or create an AsyncWebClient with the specified token.

        Uses a singleton pattern to avoid creating multiple clients for the same token.

        Parameters
        ----------
        token : Optional[str], optional
            The Slack token to use. If None, will use environment variables.
        use_retries : bool, optional
            Whether to use a retryable client, by default True.

        Returns
        -------
        AsyncWebClient
            The Slack client

        Raises
        ------
        ValueError
            If no token is found or provided
        """
        # Resolve token
        resolved_token = token or self._default_token
        if not resolved_token:
            raise ValueError(
                "Slack token not found. Provide one via the parameter or set "
                "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
            )

        # Create cache key - combine token and retry flag
        cache_key = f"{resolved_token}:{use_retries}"

        # Return cached client if exists
        if cache_key in self._async_clients:
            _LOG.debug(f"Returning cached async client for token ending with ...{resolved_token[-4:]}")
            return self._async_clients[cache_key]

        # Create new client based on retry setting
        factory: SlackClientFactory
        if use_retries:
            factory = RetryableSlackClientFactory(max_retry_count=self._default_retry_count)
            client = factory.create_async_client(resolved_token)
        else:
            factory = DefaultSlackClientFactory()
            client = factory.create_async_client(resolved_token)

        # Cache the client
        self._async_clients[cache_key] = client
        _LOG.debug(f"Created new async Slack client for token ending with ...{resolved_token[-4:]}")

        return client

    def get_sync_client(self, token: Optional[str] = None, use_retries: bool = True) -> WebClient:
        """Get or create a synchronous WebClient with the specified token.

        Uses a singleton pattern to avoid creating multiple clients for the same token.

        Parameters
        ----------
        token : Optional[str], optional
            The Slack token to use. If None, will use environment variables.
        use_retries : bool, optional
            Whether to use a retryable client, by default True.

        Returns
        -------
        WebClient
            The Slack client

        Raises
        ------
        ValueError
            If no token is found or provided
        """
        # Resolve token
        resolved_token = token or self._default_token
        if not resolved_token:
            raise ValueError(
                "Slack token not found. Provide one via the parameter or set "
                "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
            )

        # Create cache key - combine token and retry flag
        cache_key = f"{resolved_token}:{use_retries}"

        # Return cached client if exists
        if cache_key in self._sync_clients:
            _LOG.debug(f"Returning cached sync client for token ending with ...{resolved_token[-4:]}")
            return self._sync_clients[cache_key]

        # Create new client based on retry setting
        factory: SlackClientFactory
        if use_retries:
            factory = RetryableSlackClientFactory(max_retry_count=self._default_retry_count)
            client = factory.create_sync_client(resolved_token)
        else:
            factory = DefaultSlackClientFactory()
            client = factory.create_sync_client(resolved_token)

        # Cache the client
        self._sync_clients[cache_key] = client
        _LOG.debug(f"Created new sync Slack client for token ending with ...{resolved_token[-4:]}")

        return client

    def update_retry_count(self, retry_count: int) -> None:
        """Update the retry count for retryable clients.

        This will update the default retry count and clear all cached clients
        to ensure they use the new settings.

        Parameters
        ----------
        retry_count : int
            The new retry count to use.

        Raises
        ------
        ValueError
            If retry_count is negative.
        """
        if retry_count < 0:
            raise ValueError("Retry count must be non-negative")

        self._default_retry_count = retry_count

        # Clear client caches to ensure all future clients use the new retry settings
        self.clear_clients()
        _LOG.info(f"Updated retry count to {retry_count} and cleared client caches")

    def clear_clients(self) -> None:
        """Clear all cached clients.

        This forces new clients to be created on the next request.
        """
        self._async_clients.clear()
        self._sync_clients.clear()
        _LOG.info("All client caches cleared")

    def update_client(self, token: str, client: AsyncWebClient | WebClient, is_async: bool = True) -> None:
        """Update or add a client in the cache.

        This allows replacing an existing client with a custom-configured one
        or adding a new client with specific configurations.

        Parameters
        ----------
        token : str
            The token associated with this client
        client : AsyncWebClient | WebClient
            The client instance to cache
        is_async : bool, optional
            Whether the client is async or sync, by default True

        Raises
        ------
        ValueError
            If the token is empty or None
        TypeError
            If the client type doesn't match the is_async parameter
        """
        if not token:
            raise ValueError("Token cannot be empty or None")

        # Determine if this is a retryable client by checking for retry handlers
        use_retries = len(getattr(client, "retry_handlers", [])) > 0
        cache_key = f"{token}:{use_retries}"

        # Validate client type
        if is_async and not isinstance(client, AsyncWebClient):
            raise TypeError("Client must be an AsyncWebClient when is_async is True")
        if not is_async and not isinstance(client, WebClient):
            raise TypeError("Client must be a WebClient when is_async is False")

        # Update the appropriate cache
        if is_async:
            self._async_clients[cache_key] = client
        else:
            self._sync_clients[cache_key] = client

        _LOG.info(f"Updated {'async' if is_async else 'sync'} client for token ending with ...{token[-4:]}")


def get_client_manager() -> SlackClientManager:
    """Get the global SlackClientManager singleton instance.

    Returns
    -------
    SlackClientManager
        The global SlackClientManager instance
    """
    return SlackClientManager()
