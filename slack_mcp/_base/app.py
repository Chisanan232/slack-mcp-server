"""
Base server factory classes.

This module provides abstract base classes for server factories
that follow the singleton pattern.
"""

from abc import ABCMeta, abstractmethod


class BaseServerFactory[T](metaclass=ABCMeta):
    """Abstract base class for server factories using a singleton pattern.

    Concrete factories should subclass this and implement the static methods to
    create, retrieve, and reset a server instance. Implementations in this
    repository include MCP, webhook, and integrated app factories.

    Examples
    --------
    .. code-block:: python

        from slack_mcp.mcp.app import mcp_factory

        # Create once
        server = mcp_factory.create()

        # Retrieve later
        server = mcp_factory.get()

        # Reset for tests
        mcp_factory.reset()
    """

    @staticmethod
    @abstractmethod
    def create(**kwargs) -> T:
        """Create and configure a server instance.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments for server configuration

        Returns
        -------
        T
            Configured server instance
        """

    @staticmethod
    @abstractmethod
    def get() -> T:
        """Get the existing server instance.

        Returns
        -------
        T
            The configured server instance

        Raises
        ------
        AssertionError
            If the instance has not been created yet in implementations that
            enforce strict singleton creation order.
        """

    @staticmethod
    @abstractmethod
    def reset() -> None:
        """Reset the singleton instance (primarily for testing)."""
