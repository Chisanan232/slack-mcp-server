# tests/test_config_integration.py
from __future__ import annotations

from slack_mcp.mcp.cli.models import MCPServerCliOptions
from slack_mcp.mcp.cli import _parse_args  # 假設該函式路徑

def test_parse_args_to_dataclass(tmp_path) -> None:
    argv = [
        "--host", "0.0.0.0",
        "--port", "9001",
        "--transport", "sse",
        "--mount-path", "/mcp",
        "--log-level", "DEBUG",
        "--env-file", str(tmp_path / ".env.local"),
        "--no-env-file",
        "--slack-token", "xoxb-123",
        "--integrated",
        "--retry", "7",
    ]

    ns = _parse_args(argv)
    cfg = MCPServerCliOptions.deserialize(ns)

    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9001
    assert cfg.transport == "sse"
    assert cfg.mount_path == "/mcp"
    assert cfg.log_level == "DEBUG"
    assert cfg.env_file.endswith(".env.local")
    assert cfg.no_env_file is True
    assert cfg.slack_token == "xoxb-123"
    assert cfg.integrated is True
    assert cfg.retry == 7
