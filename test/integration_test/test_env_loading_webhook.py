"""Integration tests for .env file loading in the slack_server.py module."""

import os
import tempfile
from unittest.mock import patch


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
        # Run slack_server.main with our temp .env file
        with patch("sys.argv", ["slack-events-server", "--env-file", temp_env_path]):
            with patch("asyncio.run") as mock_run:
                with patch("slack_mcp.slack_server.run_slack_server") as mock_server_run:
                    mock_run.side_effect = lambda coro: None  # Don't actually run the coroutine

                    with patch.dict("os.environ", {}, clear=True):
                        # Import here to ensure clean environment
                        from slack_mcp.slack_server import main

                        # Run the main function which should load the .env file
                        main()

                        # Check if environment variables were loaded
                        assert os.environ.get("SLACK_BOT_TOKEN") == test_bot_token
                        assert os.environ.get("SLACK_SIGNING_SECRET") == test_signing_secret

                        # Verify that run_slack_server was called with the default host/port
                        mock_run.assert_called_once()
                        mock_server_run.assert_called_once_with(host="0.0.0.0", port=3000, token=None)

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)


def test_webhook_cmd_line_token_passed_to_server():
    """Test that command line token is passed to run_slack_server function."""
    cmd_line_token = "xoxb-webhook-cmd-line-token-67890"

    # Run slack_server.main with command line token
    with patch("sys.argv", ["slack-events-server", "--slack-token", cmd_line_token]):
        with patch("asyncio.run") as mock_run:
            with patch("slack_mcp.slack_server.run_slack_server") as mock_server_run:
                mock_run.side_effect = lambda coro: None  # Don't actually run the coroutine

                with patch.dict("os.environ", {}, clear=True):
                    # Import here to ensure clean environment
                    from slack_mcp.slack_server import main

                    # Run the main function which should pass the token
                    main()

                    # Verify that run_slack_server was called with the token
                    mock_run.assert_called_once()
                    mock_server_run.assert_called_once_with(host="0.0.0.0", port=3000, token=cmd_line_token)


def test_webhook_create_slack_app_with_env_token():
    """Test that create_slack_app uses token from environment variables."""
    # Set environment variable
    test_bot_token = "xoxb-slack-app-env-token"

    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": test_bot_token}):
        with patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls:
            # Import here to use the patched environment
            from slack_mcp.slack_app import create_slack_app

            # Create app which should use env var token
            app = create_slack_app()

            # Verify client was created with correct token
            mock_client_cls.assert_called_once_with(token=test_bot_token)


def test_webhook_create_slack_app_with_param_token():
    """Test that create_slack_app uses token from parameter over env var."""
    # Set environment variable
    env_token = "xoxb-slack-app-env-token"
    param_token = "xoxb-slack-app-param-token"

    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": env_token}):
        with patch("slack_mcp.slack_app.AsyncWebClient") as mock_client_cls:
            # Import here to use the patched environment
            from slack_mcp.slack_app import create_slack_app

            # Create app with explicit token parameter
            app = create_slack_app(token=param_token)

            # Verify client was created with parameter token, not env var
            mock_client_cls.assert_called_once_with(token=param_token)
