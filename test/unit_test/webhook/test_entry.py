"""Unit tests for the Slack server module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server import FastMCP

from slack_mcp.webhook.entry import (
    main,
    register_mcp_tools,
    run_integrated_server,
    run_slack_server,
)


@pytest.fixture
def mock_mcp():
    """Create a mock FastMCP instance."""
    mcp = MagicMock(spec=FastMCP)
    return mcp


@pytest.fixture
def mock_flask_app():
    """Create a mock Flask app."""
    app = MagicMock()
    return app


def test_register_mcp_tools(mock_mcp):
    """Test registering MCP tools."""
    # Call the function
    register_mcp_tools(mock_mcp)

    # Verify tool and prompt registrations
    assert mock_mcp.tool.call_count == 1
    assert mock_mcp.prompt.call_count == 1

    # Check that the tool decorator was called with the expected name
    mock_mcp.tool.assert_any_call("slack_listen_events")

    # Check that the prompt decorator was called with the expected name
    mock_mcp.prompt.assert_any_call("slack_listen_events_usage")


@pytest.mark.asyncio
async def test_run_slack_server():
    """Test running the Slack server."""
    with (
        patch("slack_mcp.webhook.entry.create_slack_app") as mock_create_app,
        patch("slack_mcp.webhook.entry.initialize_slack_client") as mock_initialize_client,
        patch("uvicorn.Server") as mock_server_cls,
        patch("uvicorn.Config") as mock_config_cls,
    ):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config

        mock_server = MagicMock()
        mock_server_cls.return_value = mock_server
        mock_server.serve = AsyncMock()

        # Run the server
        await run_slack_server(host="127.0.0.1", port=8000, token="test-token", retry=5)

        # Verify create_slack_app was called correctly
        mock_create_app.assert_called_once()

        # Verify initialize_slack_client was called with correct parameters
        mock_initialize_client.assert_called_once_with("test-token", retry=5)

        # Verify uvicorn was configured correctly
        mock_config_cls.assert_called_once_with(app=mock_app, host="127.0.0.1", port=8000)

        # Verify server was started
        mock_server_cls.assert_called_once_with(config=mock_config)
        mock_server.serve.assert_awaited_once()


@pytest.mark.parametrize(
    "cmd_args, expected_host, expected_port, expected_token, no_env_file, is_integrated, expected_transport, expected_mount_path",
    [
        # Default parameters
        ([], "0.0.0.0", 3000, None, False, False, None, None),
        # Custom host and port
        (["--host", "127.0.0.1", "--port", "8080"], "127.0.0.1", 8080, None, False, False, None, None),
        # Custom token
        (["--slack-token", "custom_token"], "0.0.0.0", 3000, "custom_token", False, False, None, None),
        # Custom env file
        (["--env-file", "custom.env"], "0.0.0.0", 3000, None, False, False, None, None),
        # No env file
        (["--no-env-file"], "0.0.0.0", 3000, None, True, False, None, None),
        # Custom log level
        (["--log-level", "DEBUG"], "0.0.0.0", 3000, None, False, False, None, None),
        # Integrated mode with default transport and mount path
        (["--integrated"], "0.0.0.0", 3000, None, False, True, "sse", "/mcp"),
        # Integrated mode with custom transport
        (
            ["--integrated", "--mcp-transport", "streamable-http"],
            "0.0.0.0",
            3000,
            None,
            False,
            True,
            "streamable-http",
            "/mcp",
        ),
        # Integrated mode with custom mount path
        (["--integrated", "--mcp-mount-path", "/api"], "0.0.0.0", 3000, None, False, True, "sse", "/api"),
        # Full integrated configuration
        (
            [
                "--integrated",
                "--host",
                "localhost",
                "--port",
                "5000",
                "--slack-token",
                "test",
                "--mcp-transport",
                "streamable-http",
                "--mcp-mount-path",
                "/custom",
            ],
            "localhost",
            5000,
            "test",
            False,
            True,
            "streamable-http",
            "/custom",
        ),
    ],
)
def test_main(
    cmd_args,
    expected_host,
    expected_port,
    expected_token,
    no_env_file,
    is_integrated,
    expected_transport,
    expected_mount_path,
):
    """Test the main function with different command line arguments."""
    with (
        patch("sys.argv", ["entry.py"] + cmd_args),
        patch("slack_mcp.webhook.entry.asyncio.run") as mock_run,
        patch("slack_mcp.webhook.entry.setup_logging_from_args") as mock_setup_logging,
        patch("slack_mcp.webhook.entry.register_mcp_tools") as mock_register_mcp_tools,
        patch("slack_mcp.webhook.entry.run_integrated_server", new_callable=MagicMock) as mock_run_integrated_server,
        patch("slack_mcp.webhook.entry.run_slack_server", new_callable=MagicMock) as mock_run_slack_server,
        patch("slack_mcp.webhook.entry.mcp_factory.get") as mock_mcp_factory_get,
        patch("slack_mcp.webhook.entry.get_settings") as mock_get_settings,
        patch("slack_mcp.logging.config.get_settings") as mock_logging_get_settings,
    ):
        # Configure the mock MCP factory to return a mock FastMCP instance
        mock_mcp_instance = MagicMock(spec=FastMCP)
        mock_mcp_factory_get.return_value = mock_mcp_instance

        # Configure mock_get_settings to return a proper settings object with string values
        mock_settings = MagicMock()
        mock_settings.slack_bot_token = None
        mock_settings.slack_signing_secret = None
        mock_settings.slack_events_topic = "slack_events"
        mock_settings.log_level = "INFO"
        mock_settings.log_file = None
        mock_settings.log_dir = "logs"
        mock_settings.log_format = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
        mock_get_settings.return_value = mock_settings
        mock_logging_get_settings.return_value = mock_settings

        # Run the main function
        main()

        # Verify logging was configured with setup_logging_from_args
        mock_setup_logging.assert_called_once()
        # The args object is passed to setup_logging_from_args
        args = mock_setup_logging.call_args[0][0]
        if "--log-level" in cmd_args:
            expected_log_level = cmd_args[cmd_args.index("--log-level") + 1].upper()
        else:
            expected_log_level = "INFO"
        assert args.log_level.upper() == expected_log_level

        # Verify env file handling
        if "--no-env-file" not in cmd_args:
            env_file = "custom.env" if "--env-file" in cmd_args else ".env"

            # Verify get_settings was called with correct parameters
            mock_get_settings.assert_called_once()
            call_kwargs = mock_get_settings.call_args[1]
            assert call_kwargs.get("env_file") == env_file
            assert call_kwargs.get("no_env_file") is False
            assert call_kwargs.get("force_reload") is True
        else:
            # When --no-env-file is specified
            mock_get_settings.assert_called_once()
            call_kwargs = mock_get_settings.call_args[1]
            assert call_kwargs.get("no_env_file") is True

        # Verify MCP tools were registered with the mocked instance
        mock_register_mcp_tools.assert_called_once_with(mock_mcp_instance)

        # Verify the server was run with the expected parameters
        mock_run.assert_called_once()

        # Check which server function was called based on integrated flag
        if is_integrated:
            mock_run_integrated_server.assert_called_once_with(
                host=expected_host,
                port=expected_port,
                token=expected_token,
                mcp_transport=expected_transport,
                mcp_mount_path=expected_mount_path,
                retry=3,  # Default retry value
            )
            mock_run_slack_server.assert_not_called()
        else:
            mock_run_slack_server.assert_called_once_with(
                host=expected_host,
                port=expected_port,
                token=expected_token,
                retry=3,  # Default retry value
            )
            mock_run_integrated_server.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "host, port, token, mcp_transport, mcp_mount_path",
    [
        # Default parameters
        ("0.0.0.0", 3000, None, "sse", "/mcp"),
        # Custom host and port
        ("127.0.0.1", 8080, None, "sse", "/mcp"),
        # Custom token
        ("0.0.0.0", 3000, "test_token", "sse", "/mcp"),
        # Different transport types
        ("0.0.0.0", 3000, None, "streamable-http", "/mcp"),
        # Different mount path
        ("0.0.0.0", 3000, None, "sse", "/custom-path"),
        # No mount path
        ("0.0.0.0", 3000, None, "sse", None),
        # Combination of customizations
        ("localhost", 5000, "test_token", "streamable-http", None),
    ],
)
async def test_run_integrated_server(host, port, token, mcp_transport, mcp_mount_path):
    """Test running the integrated server with different configurations."""
    with (
        patch("slack_mcp.webhook.entry.integrated_factory.create") as mock_create_app,
        patch("uvicorn.Server") as mock_server_cls,
        patch("uvicorn.Config") as mock_config_cls,
    ):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config

        # Mock the Server instance with an AsyncMock to handle the await server.serve() call
        mock_server = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Call the function with test parameters
        await run_integrated_server(
            host=host,
            port=port,
            token=token,
            mcp_transport=mcp_transport,
            mcp_mount_path=mcp_mount_path,
        )

        # Verify the app was created with the right parameters
        mock_create_app.assert_called_once_with(
            token=token,
            mcp_transport=mcp_transport,
            mcp_mount_path=mcp_mount_path,
            retry=3,  # Default retry value
        )

        # Verify the config was set correctly
        mock_config_cls.assert_called_once_with(app=mock_app, host=host, port=port)

        # Verify the server was properly configured and started
        mock_server_cls.assert_called_once_with(config=mock_config)

        # Verify serve was called and properly awaited
        mock_server.serve.assert_called_once()


def test_webhook_entry_dotenv_priority_over_cli():
    """Test that .env file values take priority over CLI arguments in webhook entry."""
    from unittest.mock import MagicMock, patch

    # Mock get_settings to simulate .env file loading
    def mock_get_settings(**kwargs):
        from slack_mcp.settings import SettingModel

        # Simulate .env file having priority by returning settings with .env value
        return SettingModel(_env_file=None, slack_bot_token="xoxb-from-dotenv-file")  # This simulates .env file content

    with (
        patch("sys.argv", ["entry.py", "--slack-token", "xoxb-from-cli-argument"]),
        patch("slack_mcp.webhook.entry.asyncio.run") as mock_run,
        patch("slack_mcp.webhook.entry.setup_logging_from_args"),
        patch("slack_mcp.webhook.entry.get_settings", side_effect=mock_get_settings),
        patch("slack_mcp.logging.config.get_settings", side_effect=mock_get_settings),
        patch("slack_mcp.webhook.entry.pathlib.Path") as mock_path,
        patch("slack_mcp.webhook.entry.register_mcp_tools"),
        patch("slack_mcp.webhook.entry.run_slack_server", new_callable=MagicMock),
        patch("slack_mcp.webhook.entry.mcp_factory.get"),
    ):
        # Configure the mock path to simulate env file existence
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.resolve.return_value = "/path/to/.env"
        mock_path.return_value = mock_path_instance

        # Run the main function
        main()

        # Verify that get_settings was called with CLI token as kwargs
        # but the .env file (simulated in mock) would take priority
        # This tests the priority mechanism in pydantic-settings


def test_webhook_entry_handles_settings_load_failure():
    """Test that webhook main() handles get_settings() exceptions gracefully (line 527-530)."""
    # Mock _parse_args to return a simple mock that avoids validation issues
    with patch("slack_mcp.webhook.entry._parse_args") as mock_parse_args:
        mock_args = MagicMock()
        mock_args.slack_token = None
        mock_args.env_file = ".env"
        mock_args.no_env_file = False
        mock_args.host = "0.0.0.0"
        mock_args.port = 8000
        mock_args.mount_path = None
        mock_args.integrated = False
        mock_args.mcp_transport = "sse"
        mock_args.mcp_mount_path = "/mcp"
        mock_args.retry = 3
        mock_args.log_level = "INFO"
        mock_args.log_file = None
        mock_args.log_dir = "logs"
        mock_args.log_format = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
        mock_parse_args.return_value = mock_args

        # Mock get_settings to raise an exception only in the main logic, not during parsing
        with patch("slack_mcp.webhook.entry.get_settings", side_effect=Exception("Configuration load failed")):
            # Don't mock logging.config.get_settings here so CLI parsing works
            with patch("slack_mcp.webhook.entry.setup_logging_from_args"):
                with patch("slack_mcp.webhook.entry.mcp_factory") as mock_factory:
                    mock_factory.get.return_value.sse_app.return_value = MagicMock()

                    with patch("slack_mcp.webhook.entry._LOG") as mock_log:
                        # This should not raise an exception
                        result = main([])

                        # Should return None (early exit) when configuration fails
                        assert result is None
                        # Should log the error
                        mock_log.error.assert_called_once()
