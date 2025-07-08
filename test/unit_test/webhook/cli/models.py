from __future__ import annotations

import argparse

from slack_mcp.webhook.cli.models import WebhookServerCliOptions


def test_deserialize_basic() -> None:
    ns = argparse.Namespace(
        host="127.0.0.1",
        port=4000,
        log_level="DEBUG",
        slack_token="xoxb-999",
        env_file="/tmp/.env",
        no_env_file=True,
        integrated=True,
        mcp_transport="streamable-http",
        mcp_mount_path="/events",
        retry=5,
        ignored="SHOULD_BE_IGNORED",
    )

    cfg = WebhookServerCliOptions.deserialize(ns)

    assert cfg.host == "127.0.0.1"
    assert cfg.port == 4000
    assert cfg.log_level == "DEBUG"
    assert cfg.slack_token == "xoxb-999"
    assert cfg.env_file == "/tmp/.env"
    assert cfg.no_env_file is True
    assert cfg.integrated is True
    assert cfg.mcp_transport == "streamable-http"
    assert cfg.mcp_mount_path == "/events"
    assert cfg.retry == 5
