"""Factory pattern implementation for creating Slack clients.

This module provides an abstract base class for client factories and concrete implementations
for different types of Slack clients. It allows for dependency injection and easier testing
by abstracting the client creation process.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import List, Optional

from slack_sdk.http_retry.async_handler import AsyncRetryHandler
from slack_sdk.http_retry.builtin_async_handlers import (
    AsyncConnectionErrorRetryHandler,
    AsyncRateLimitErrorRetryHandler,
    AsyncServerErrorRetryHandler,
)
from slack_sdk.http_retry.builtin_handlers import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler,
    ServerErrorRetryHandler,
)
from slack_sdk.http_retry.handler import RetryHandler
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp.mcp.model.input import _BaseInput


class SlackClientFactory(ABC):
    """Abstract base class for Slack client factories.

    This class defines the interface that all Slack client factories must implement.
    Concrete factories should extend this class and implement the creation methods.
    """

    @abstractmethod
    def create_async_client(self, token: Optional[str] = None) -> AsyncWebClient:
        """Create and return an AsyncWebClient instance.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use for authentication. If not provided, will try to
            resolve from environment variables.

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance.

        Raises
        ------
        ValueError
            If no token is supplied and none can be resolved from environment.
        """

    @abstractmethod
    def create_sync_client(self, token: Optional[str] = None) -> WebClient:
        """Create and return a synchronous WebClient instance.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use for authentication. If not provided, will try to
            resolve from environment variables.

        Returns
        -------
        WebClient
            Initialized Slack WebClient instance.

        Raises
        ------
        ValueError
            If no token is supplied and none can be resolved from environment.
        """

    @abstractmethod
    def create_async_client_from_input(self, input_params: _BaseInput) -> AsyncWebClient:
        """Create an AsyncWebClient from MCP input parameters.

        Parameters
        ----------
        input_params : _BaseInput
            Input object containing parameters for the Slack API call.

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance.

        Raises
        ------
        ValueError
            If no token is resolved from input or environment.
        """


class DefaultSlackClientFactory(SlackClientFactory):
    """Default implementation of the SlackClientFactory.

    This class provides standard implementations for creating Slack clients
    using token resolution from input parameters or environment variables.
    """

    def _resolve_token(self, token: Optional[str] = None) -> str:
        """Resolve the Slack token from provided value or environment variables.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use if provided, by default None

        Returns
        -------
        str
            Resolved token value

        Raises
        ------
        ValueError
            If no token can be resolved
        """
        resolved_token = token or os.getenv("SLACK_BOT_TOKEN") or os.getenv("SLACK_TOKEN")
        if resolved_token is None:
            raise ValueError(
                "Slack token not found. Provide one via the 'token' argument or set "
                "the SLACK_BOT_TOKEN/SLACK_TOKEN environment variable."
            )
        return resolved_token

    def create_async_client(self, token: Optional[str] = None) -> AsyncWebClient:
        """Create an AsyncWebClient using the provided token or environment variables.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use if provided, by default None

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance
        """
        resolved_token = self._resolve_token(token)
        return AsyncWebClient(token=resolved_token)

    def create_sync_client(self, token: Optional[str] = None) -> WebClient:
        """Create a synchronous WebClient using the provided token or environment variables.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use if provided, by default None

        Returns
        -------
        WebClient
            Initialized Slack WebClient instance
        """
        resolved_token = self._resolve_token(token)
        return WebClient(token=resolved_token)

    def create_async_client_from_input(self, input_params: _BaseInput) -> AsyncWebClient:
        """Create an AsyncWebClient from MCP input parameters.

        Parameters
        ----------
        input_params : _BaseInput
            Input object containing parameters for the Slack API call.

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance
        """
        from slack_mcp.client.manager import get_client_manager

        manager = get_client_manager()
        return self.create_async_client(manager._default_token)


class RetryableSlackClientFactory(DefaultSlackClientFactory):
    """Implementation of SlackClientFactory with built-in retry capabilities.

    This class extends DefaultSlackClientFactory to provide Slack clients
    configured with retry handlers for common error scenarios:
    - Rate limit errors (HTTP 429)
    - Server errors (HTTP 5xx)
    - Connection errors

    The retry behavior follows exponential backoff with jitter for optimal
    handling of transient issues when interacting with Slack API.
    """

    def __init__(
        self,
        max_retry_count: int = 3,
        include_rate_limit_retries: bool = True,
        include_server_error_retries: bool = True,
        include_connection_error_retries: bool = True,
    ):
        """Initialize the factory with retry configuration.

        Parameters
        ----------
        max_retry_count : int, optional
            Maximum number of retry attempts, by default 3
        include_rate_limit_retries : bool, optional
            Whether to retry on rate limit errors (HTTP 429), by default True
        include_server_error_retries : bool, optional
            Whether to retry on server errors (HTTP 5xx), by default True
        include_connection_error_retries : bool, optional
            Whether to retry on connection errors, by default True
        """
        self.max_retry_count = max_retry_count
        self.include_rate_limit_retries = include_rate_limit_retries
        self.include_server_error_retries = include_server_error_retries
        self.include_connection_error_retries = include_connection_error_retries

    def _get_async_retry_handlers(self) -> List[AsyncRetryHandler]:
        """Get the list of async retry handlers based on configuration.

        Returns
        -------
        List[AsyncRetryHandler]
            List of configured retry handlers
        """
        handlers = []
        if self.include_rate_limit_retries:
            handlers.append(AsyncRateLimitErrorRetryHandler(max_retry_count=self.max_retry_count))
        if self.include_server_error_retries:
            handlers.append(AsyncServerErrorRetryHandler(max_retry_count=self.max_retry_count))
        if self.include_connection_error_retries:
            handlers.append(AsyncConnectionErrorRetryHandler(max_retry_count=self.max_retry_count))
        return handlers

    def _get_sync_retry_handlers(self) -> List[RetryHandler]:
        """Get the list of sync retry handlers based on configuration.

        Returns
        -------
        List[RetryHandler]
            List of configured retry handlers
        """
        handlers = []
        if self.include_rate_limit_retries:
            handlers.append(RateLimitErrorRetryHandler(max_retry_count=self.max_retry_count))
        if self.include_server_error_retries:
            handlers.append(ServerErrorRetryHandler(max_retry_count=self.max_retry_count))
        if self.include_connection_error_retries:
            handlers.append(ConnectionErrorRetryHandler(max_retry_count=self.max_retry_count))
        return handlers

    def create_async_client(self, token: Optional[str] = None) -> AsyncWebClient:
        """Create an AsyncWebClient with retry capabilities.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use if provided, by default None

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance with retry handlers
        """
        client = super().create_async_client(token)
        # Add retry handlers to the client
        for handler in self._get_async_retry_handlers():
            client.retry_handlers.append(handler)
        return client

    def create_sync_client(self, token: Optional[str] = None) -> WebClient:
        """Create a synchronous WebClient with retry capabilities.

        Parameters
        ----------
        token : Optional[str], optional
            Slack token to use if provided, by default None

        Returns
        -------
        WebClient
            Initialized Slack WebClient instance with retry handlers
        """
        client = super().create_sync_client(token)
        # Add retry handlers to the client
        for handler in self._get_sync_retry_handlers():
            client.retry_handlers.append(handler)
        return client

    def create_async_client_from_input(self, input_params: _BaseInput) -> AsyncWebClient:
        """Create an AsyncWebClient with retry capabilities from MCP input parameters.

        Parameters
        ----------
        input_params : _BaseInput
            Input object containing parameters for the Slack API call.

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance with retry handlers
        """
        # Use parent implementation which now uses default token
        return super().create_async_client_from_input(input_params)


# Default global instances for easy access
default_factory = DefaultSlackClientFactory()
retryable_factory = RetryableSlackClientFactory()
