# tests/test_config_unit.py
from __future__ import annotations

import argparse

from slack_mcp.mcp.cli.models import MCPServerCliOptions


def test_deserialize_minimal() -> None:
    ns = argparse.Namespace(
        host="0.0.0.0",
        port=9000,
        transport="stdio",
        mount_path=None,
        log_level="DEBUG",
        env_file=".env.test",
        no_env_file=False,
        slack_token=None,
        integrated=False,
        retry=5,
        extra="IGNORED",           # 不在模型中的欄位將被捨棄
    )
    cfg = MCPServerCliOptions.deserialize(ns)

    assert cfg == MCPServerCliOptions(
        host="0.0.0.0",
        port=9000,
        transport="stdio",
        mount_path=None,
        log_level="DEBUG",
        env_file=".env.test",
        no_env_file=False,
        slack_token=None,
        integrated=False,
        retry=5,
    )
