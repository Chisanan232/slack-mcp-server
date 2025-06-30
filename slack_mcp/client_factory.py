"""Factory pattern implementation for creating Slack clients.

This module provides an abstract base class for client factories and concrete implementations
for different types of Slack clients. It allows for dependency injection and easier testing
by abstracting the client creation process.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.client import WebClient

from slack_mcp.model import _BaseInput


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
            Input object containing an optional token parameter.

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
            Input object containing an optional token parameter.

        Returns
        -------
        AsyncWebClient
            Initialized Slack AsyncWebClient instance
        """
        return self.create_async_client(input_params.token)


# Default global instance for easy access
default_factory = DefaultSlackClientFactory()
