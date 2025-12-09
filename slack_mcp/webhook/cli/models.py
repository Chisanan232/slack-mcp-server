"""Pydantic models for Slack webhook server CLI options.

Defines a typed configuration model used by the webhook server entrypoint.
Use this model to validate parsed arguments and to ensure consistent behavior
across environments.

Examples
--------
.. code-block:: python

    from slack_mcp.webhook.cli.options import _parse_args

    opts = _parse_args(["--port", "3001", "--mcp-transport", "sse"])  # WebhookServerCliOptions
    assert opts.port == 3001
"""

from __future__ import annotations

import argparse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WebhookServerCliOptions(BaseModel):
    """Validated CLI options for the Slack webhook server entrypoint.

    Fields
    ------
    host : str
        Host to bind (default: 0.0.0.0)
    port : int
        Port to listen on (default: 3000)
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_file : str | None
        Path to log file (optional)
    log_dir : str | None
        Directory for log files (optional)
    log_format : str | None
        Log message format (optional)
    slack_token : str | None
        Slack bot token fallback (overridden by .env or environment)
    env_file : str
        Path to .env file for environment variable loading
    no_env_file : bool
        Disable loading .env file when True
    integrated : bool
        Run integrated mode with MCP server
    mcp_transport : Literal["sse", "streamable-http"]
        MCP transport to use when integrated (default: sse)
    mcp_mount_path : str
        Mount path for MCP (applies to SSE) (default: /mcp)
    retry : int
        Retry attempts for Slack client/network operations (>= 0)

    Examples
    --------
    .. code-block:: python

        from slack_mcp.webhook.cli.options import _parse_args
        opts = _parse_args(["--integrated", "--mcp-transport", "sse"])  # WebhookServerCliOptions
        print(opts.model_dump())
    """

    host: str = "0.0.0.0"
    port: int = Field(3000, ge=1, le=65535)
    log_level: str = "INFO"
    log_file: str | None = None
    log_dir: str | None = None
    log_format: str | None = None

    slack_token: str | None = None

    env_file: str = ".env"
    no_env_file: bool = False

    integrated: bool = False

    mcp_transport: Literal["sse", "streamable-http"] = "sse"
    mcp_mount_path: str = "/mcp"

    retry: int = Field(3, ge=0)

    model_config = ConfigDict(frozen=True, extra="ignore")

    @classmethod
    def deserialize(cls, ns: argparse.Namespace) -> "WebhookServerCliOptions":
        """Build a validated options object from argparse namespace."""
        data = {name: getattr(ns, name) for name in cls.model_fields.keys() if hasattr(ns, name)}
        return cls(**data)
