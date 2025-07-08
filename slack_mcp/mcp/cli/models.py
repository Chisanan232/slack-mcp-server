from __future__ import annotations

import argparse
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MCPServerCliOptions(BaseModel):

    host: str = "127.0.0.1"
    port: int = Field(8000, ge=1, le=65535)
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    mount_path: str | None = None
    log_level: str = "INFO"
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
