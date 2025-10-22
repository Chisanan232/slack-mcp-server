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
    "cmd_args, expected_host, expected_port, expected_token, env_file_exists, is_integrated, expected_transport, expected_mount_path",
    [
        # Default parameters
        ([], "0.0.0.0", 3000, None, True, False, None, None),
        # Custom host and port
        (["--host", "127.0.0.1", "--port", "8080"], "127.0.0.1", 8080, None, True, False, None, None),
        # Custom token
        (["--slack-token", "custom_token"], "0.0.0.0", 3000, "custom_token", True, False, None, None),
        # Custom env file
        (["--env-file", "custom.env"], "0.0.0.0", 3000, None, True, False, None, None),
        # No env file
        (["--no-env-file"], "0.0.0.0", 3000, None, False, False, None, None),
        # Custom log level
        (["--log-level", "DEBUG"], "0.0.0.0", 3000, None, True, False, None, None),
        # Integrated mode with default transport and mount path
        (["--integrated"], "0.0.0.0", 3000, None, True, True, "sse", "/mcp"),
        # Integrated mode with custom transport
        (
            ["--integrated", "--mcp-transport", "streamable-http"],
            "0.0.0.0",
            3000,
            None,
            True,
            True,
            "streamable-http",
            "/mcp",
        ),
        # Integrated mode with custom mount path
        (["--integrated", "--mcp-mount-path", "/api"], "0.0.0.0", 3000, None, True, True, "sse", "/api"),
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
            True,
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
    env_file_exists,
    is_integrated,
    expected_transport,
    expected_mount_path,
):
    """Test the main function with different command line arguments."""
    with (
        patch("sys.argv", ["entry.py"] + cmd_args),
        patch("slack_mcp.webhook.entry.asyncio.run") as mock_run,
        patch("slack_mcp.webhook.entry.setup_logging_from_args") as mock_setup_logging,
        patch("slack_mcp.webhook.entry.load_dotenv") as mock_load_dotenv,
        patch("slack_mcp.webhook.entry.pathlib.Path") as mock_path,
        patch("slack_mcp.webhook.entry.register_mcp_tools") as mock_register_mcp_tools,
        patch("slack_mcp.webhook.entry.run_integrated_server", new_callable=MagicMock) as mock_run_integrated_server,
        patch("slack_mcp.webhook.entry.run_slack_server", new_callable=MagicMock) as mock_run_slack_server,
        patch("slack_mcp.webhook.entry.mcp_factory.get") as mock_mcp_factory_get,
    ):
        # Configure the mock path to simulate env file existence
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = env_file_exists
        mock_path_instance.resolve.return_value = "/path/to/env"
        mock_path.return_value = mock_path_instance

        # Configure the mock MCP factory to return a mock FastMCP instance
        mock_mcp_instance = MagicMock(spec=FastMCP)
        mock_mcp_factory_get.return_value = mock_mcp_instance

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
            mock_path.assert_called_with(env_file)

            if env_file_exists:
                mock_load_dotenv.assert_called_once()
                # Verify override=True is passed to prioritize .env file
                call_kwargs = mock_load_dotenv.call_args[1]
                assert call_kwargs.get("override") is True
            else:
                mock_load_dotenv.assert_not_called()
        else:
            mock_load_dotenv.assert_not_called()

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
    import os
    from unittest.mock import patch, MagicMock

    # Mock environment to track token setting
    mock_environ = {}

    # Mock load_dotenv to simulate loading from .env file
    def mock_load_dotenv(dotenv_path=None, override=False):
        # Simulate .env file setting SLACK_BOT_TOKEN
        if override:
            mock_environ["SLACK_BOT_TOKEN"] = "xoxb-from-dotenv-file"

    with (
        patch("sys.argv", ["entry.py", "--slack-token", "xoxb-from-cli-argument"]),
        patch("slack_mcp.webhook.entry.asyncio.run") as mock_run,
        patch("slack_mcp.webhook.entry.setup_logging_from_args"),
        patch("slack_mcp.webhook.entry.load_dotenv", side_effect=mock_load_dotenv),
        patch("slack_mcp.webhook.entry.pathlib.Path") as mock_path,
        patch("slack_mcp.webhook.entry.register_mcp_tools"),
        patch("slack_mcp.webhook.entry.run_slack_server", new_callable=MagicMock),
        patch("slack_mcp.webhook.entry.mcp_factory.get"),
        patch.dict(os.environ, mock_environ, clear=True),
    ):
        # Configure the mock path to simulate env file existence
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.resolve.return_value = "/path/to/.env"
        mock_path.return_value = mock_path_instance

        # Run the main function
        main()

        # Verify that the .env file token took priority over CLI argument
        assert "SLACK_BOT_TOKEN" in mock_environ
        assert mock_environ["SLACK_BOT_TOKEN"] == "xoxb-from-dotenv-file"
