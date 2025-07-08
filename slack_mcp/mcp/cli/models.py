from __future__ import annotations

import argparse
from dataclasses import dataclass, fields


@dataclass(slots=True, frozen=True)
class MCPServerCliOptions:

    host: str = "127.0.0.1"
    port: int = 8000
    transport: str = "stdio"
    mount_path: str | None = None
    log_level: str = "INFO"
    env_file: str = ".env"
    no_env_file: bool = False
    slack_token: str | None = None
    integrated: bool = False
    retry: int = 3

    @classmethod
    def deserialize(cls, ns: argparse.Namespace) -> "MCPServerCliOptions":
        field_names: set[str] = {f.name for f in fields(cls) if f.init}
        kwargs = {name: getattr(ns, name) for name in field_names if hasattr(ns, name)}
        return cls(**kwargs)
