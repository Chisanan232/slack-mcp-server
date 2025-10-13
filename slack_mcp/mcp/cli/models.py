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
    """Server type enumeration for type safety."""

    STUDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


class MCPServerCliOptions(BaseModel):

    host: str = "127.0.0.1"
    port: int = Field(8000, ge=1, le=65535)
    transport: MCPTransportType = Field(
        default=MCPTransportType.SSE, description="Type of server to run (studio, sse or http-streaming)"
    )
    mount_path: str | None = None
    log_level: str = "INFO"  # Changed to str to accept from add_logging_arguments
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
        data = {
            name: getattr(ns, name)
            for name in cls.model_fields.keys()  # v2 API；v1 改用 __fields__
            if hasattr(ns, name)
        }
        return cls(**data)
