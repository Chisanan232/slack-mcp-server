"""Integration tests for .env file loading in the entry.py module."""

import os
import tempfile
from unittest.mock import MagicMock, patch


def test_webhook_dotenv_loading_with_valid_env_file():
    """Test that environment variables are properly loaded from a valid .env file in webhook server."""
    # Create a temporary .env file with test values
    test_bot_token = "xoxb-webhook-test-token-12345"
    test_signing_secret = "webhook-test-signing-secret-12345"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".env") as temp_env:
        temp_env.write(f"SLACK_BOT_TOKEN={test_bot_token}\n")
        temp_env.write(f"SLACK_SIGNING_SECRET={test_signing_secret}\n")
        temp_env_path = temp_env.name

    try:
        # Run webhook.entry.main with our temp .env file
        with patch("sys.argv", ["slack-events-server", "--env-file", temp_env_path]):
            with patch("asyncio.run") as mock_run:
                with patch("slack_mcp.webhook.entry.run_slack_server", new_callable=MagicMock) as mock_server_run:
                    mock_run.side_effect = lambda coro: None  # Don't actually run the coroutine

                    with patch.dict("os.environ", {}, clear=True):
                        # Import here to ensure clean environment
                        from slack_mcp.webhook.entry import main

                        # Run the main function which should load the .env file
                        main()

                        # Check if environment variables were loaded using settings
                        from slack_mcp.settings import get_settings
                        settings = get_settings()
                        assert settings.slack_bot_token.get_secret_value() == test_bot_token
                        assert settings.slack_signing_secret.get_secret_value() == test_signing_secret

                        # Verify that run_slack_server was called with the default host/port
                        mock_run.assert_called_once()
                        mock_server_run.assert_called_once_with(host="0.0.0.0", port=3000, token=None, retry=3)

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)


def test_webhook_cmd_line_token_passed_to_server():
    """Test that command line token is passed to run_slack_server function."""
    cmd_line_token = "xoxb-webhook-cmd-line-token-67890"

    # Run webhook.entry.main with command line token
    with patch("sys.argv", ["slack-events-server", "--slack-token", cmd_line_token]):
        with patch("asyncio.run") as mock_run:
            with patch("slack_mcp.webhook.entry.run_slack_server", new_callable=MagicMock) as mock_server_run:
                mock_run.side_effect = lambda coro: None  # Don't actually run the coroutine

                with patch.dict("os.environ", {}, clear=True):
                    # Import here to ensure clean environment
                    from slack_mcp.webhook.entry import main

                    # Run the main function which should pass the token
                    main()

                    # Verify that run_slack_server was called with the token
                    mock_run.assert_called_once()
                    mock_server_run.assert_called_once_with(host="0.0.0.0", port=3000, token=cmd_line_token, retry=3)


def test_webhook_create_slack_app_with_initialize_client():
    """Test that create_slack_app doesn't initialize client and initialize_slack_client does."""
    # Set environment variable
    test_bot_token = "xoxb-slack-app-env-token"

    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": test_bot_token}):
        # Create mock client and manager
        mock_client = MagicMock()
        mock_client.token = test_bot_token

        mock_manager = MagicMock()
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        # We need to patch get_client_manager before importing the modules
        with patch("slack_mcp.client.manager.SlackClientManager._instance", None):
            with patch("slack_mcp.webhook.server.get_client_manager", return_value=mock_manager):
                # Import here to use the patched environment
                from slack_mcp.mcp.app import mcp_factory
                from slack_mcp.webhook.app import web_factory
                from slack_mcp.webhook.server import (
                    create_slack_app,
                    initialize_slack_client,
                )

                # Reset and initialize factories first
                mcp_factory.reset()
                web_factory.reset()
                mcp_factory.create()
                web_factory.create()

                # Create app which should NOT initialize client
                app = create_slack_app()

                # Verify client was NOT created yet
                mock_manager.get_async_client.assert_not_called()

                # Now initialize the client
                client = initialize_slack_client()

                # Verify client was created with correct token
                mock_manager.get_async_client.assert_called_once_with(None, False)
                assert client is mock_client


def test_webhook_initialize_client_with_param_token():
    """Test that initialize_slack_client uses token from parameter over env var."""
    # Set environment variable
    env_token = "xoxb-slack-app-env-token"
    param_token = "xoxb-slack-app-param-token"

    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": env_token}):
        # Create a mock client and manager
        mock_client = MagicMock()
        mock_client.token = param_token

        mock_manager = MagicMock()
        mock_manager._default_retry_count = 0
        mock_manager.get_async_client.return_value = mock_client

        # We need to patch get_client_manager before importing the modules
        with patch("slack_mcp.client.manager.SlackClientManager._instance", None):
            with patch("slack_mcp.webhook.server.get_client_manager", return_value=mock_manager):
                # Import here to use the patched environment
                from slack_mcp.webhook.server import initialize_slack_client

                # Initialize client with explicit token parameter
                client = initialize_slack_client(token=param_token)

                # Verify client was created with parameter token, not env var
                mock_manager.get_async_client.assert_called_once_with(param_token, False)
                assert client is mock_client
