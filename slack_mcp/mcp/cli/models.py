"""Pydantic models and enums for MCP server CLI options.

This module defines typed CLI configuration models and enums for the Slack MCP
server entrypoint. Use these models to validate parsed arguments and to
consolidate configuration in a structured, type-safe way.

Examples
--------
.. code-block:: python

    from slack_mcp.mcp.cli.options import _parse_args

    opts = _parse_args(["--transport", "sse", "--port", "8080"])  # MCPServerCliOptions
    assert opts.transport.value == "sse"
"""

from __future__ import annotations

import argparse
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LogLevel(str, Enum):
    """Log levels enumeration for type safety."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MCPTransportType(str, Enum):
    """MCP transport type enumeration for type safety.

    Values
    ------
    - ``stdio``: Standard input/output transport
    - ``sse``: Server-Sent Events HTTP transport
    - ``streamable-http``: Streaming HTTP transport
    """

    STUDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


class MCPServerCliOptions(BaseModel):
    """Validated CLI options for the MCP server entrypoint.

    Fields
    ------
    host : str
        Host to bind when using HTTP transports (default: 127.0.0.1)
    port : int
        Port to bind when using HTTP transports (default: 8000)
    transport : MCPTransportType
        MCP transport type (``stdio``, ``sse``, or ``streamable-http``)
    mount_path : str | None
        Mount path for HTTP transports (applies to SSE)
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_file : str | None
        Path to the log file (optional)
    log_dir : str | None
        Directory for log files (optional)
    log_format : str | None
        Log message format (optional)
    env_file : str
        Path to .env file for environment variable loading
    no_env_file : bool
        Disable loading .env file when True
    slack_token : str | None
        Slack bot token fallback (overridden by .env or environment)
    integrated : bool
        Run in integrated mode with webhook server
    retry : int
        Retry attempts for Slack API and network operations (>= 0)

    Examples
    --------
    .. code-block:: python

        from slack_mcp.mcp.cli.options import _parse_args

        opts = _parse_args(["--transport", "sse", "--port", "8080"])  # MCPServerCliOptions
        print(opts.model_dump())
    """

    host: str = "127.0.0.1"
    port: int = Field(8000, ge=1, le=65535)
    transport: MCPTransportType = Field(
        default=MCPTransportType.SSE, description="Type of server to run (stdio, sse or streamable-http)"
    )
    mount_path: str | None = None
    log_level: str = "INFO"
    log_file: str | None = None
    log_dir: str | None = None
    log_format: str | None = None
    env_file: str = ".env"
    no_env_file: bool = False
    slack_token: str | None = None
    integrated: bool = False
    retry: int = Field(3, ge=0)

    model_config = ConfigDict(frozen=True)

    @classmethod
    def deserialize(cls, ns: argparse.Namespace) -> "MCPServerCliOptions":
        """Build a validated options object from argparse namespace.

        Parameters
        ----------
        ns : argparse.Namespace
            Parsed arguments from `argparse.ArgumentParser.parse_args()`

        Returns
        -------
        MCPServerCliOptions
            Validated and immutable CLI options object
        """
        data = {name: getattr(ns, name) for name in cls.model_fields.keys() if hasattr(ns, name)}
        return cls(**data)
