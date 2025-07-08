from __future__ import annotations

import sys

from slack_mcp.webhook.cli.options import _parse_args


def test_cli_to_config(tmp_path) -> None:
    argv = [
        "--host", "127.0.0.1",
        "--port", "4100",
        "--log-level", "WARNING",
        "--slack-token", "xoxb-abc",
        "--env-file", str(tmp_path / ".env.local"),
        "--no-env-file",
        "--integrated",
        "--mcp-transport", "sse",
        "--mcp-mount-path", "/mcp",
        "--retry", "9",
    ]

    cfg = _parse_args(argv)

    assert cfg.host == "127.0.0.1"
    assert cfg.port == 4100
    assert cfg.slack_token == "xoxb-abc"
    assert cfg.no_env_file is True
    assert cfg.integrated is True
    assert cfg.retry == 9
