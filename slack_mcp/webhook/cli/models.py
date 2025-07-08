from __future__ import annotations

import argparse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WebhookServerCliOptions(BaseModel):

    host: str = "0.0.0.0"
    port: int = Field(3000, ge=1, le=65535)
    log_level: str = "INFO"

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
        data = {name: getattr(ns, name) for name in cls.model_fields.keys() if hasattr(ns, name)}
        return cls(**data)
