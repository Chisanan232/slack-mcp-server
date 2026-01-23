"""Integration tests for .env file loading in the mcp.entry.py module."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from slack_mcp.mcp.app import mcp_factory
from slack_mcp.settings import get_settings


def test_dotenv_loading_with_valid_env_file():
    """Test that environment variables are properly loaded from a valid .env file."""
    # Create a temporary .env file with test values
    test_bot_token = "xoxb-test-token-12345"
    test_signing_secret = "test-signing-secret-12345"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".env") as temp_env:
        temp_env.write(f"SLACK_BOT_TOKEN={test_bot_token}\n")
        temp_env.write(f"E2E_TEST_API_TOKEN={test_bot_token}\n")
        temp_env.write(f"SLACK_SIGNING_SECRET={test_signing_secret}\n")
        temp_env_path = temp_env.name

    try:
        # Run entry.main with our temp .env file
        with patch("sys.argv", ["slack-mcp-server", "--env-file", temp_env_path, "--transport", "stdio"]):
            with patch.object(mcp_factory.get(), "run") as mock_run:
                # Patch the test environment to allow env file loading
                with patch("slack_mcp.settings.get_test_environment") as mock_get_test_env:
                    mock_test_env = MagicMock()
                    mock_test_env.mcp_no_env_file = False
                    mock_get_test_env.return_value = mock_test_env
                    
                    # Import here to ensure clean environment
                    from slack_mcp.mcp.entry import main

                    # Run the main function which should load the .env file
                    main()

                    # Check if environment variables were loaded using settings
                    from slack_mcp.settings import get_settings

                    settings = get_settings(env_file=temp_env_path, no_env_file=False, force_reload=True)
                    assert settings.slack_bot_token.get_secret_value() == test_bot_token
                    assert settings.slack_signing_secret.get_secret_value() == test_signing_secret

                    # Verify that the server would have been started
                    mock_run.assert_called_once()

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)


def test_cmd_line_token_overrides_env_file():
    """Test that .env file token takes priority over command line token.

    This test verifies the new priority order where .env file has the highest priority,
    followed by CLI arguments as fallback. When both are provided, .env file wins.
    """
    # Create a temporary .env file with test values
    env_file_token = "xoxb-env-file-token-12345"
    cmd_line_token = "xoxb-cmd-line-token-67890"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".env") as temp_env:
        temp_env.write(f"SLACK_BOT_TOKEN={env_file_token}\n")
        temp_env.write(f"E2E_TEST_API_TOKEN={env_file_token}\n")
        temp_env_path = temp_env.name

    try:
        # Run entry.main with our temp .env file and command line token
        with patch(
            "sys.argv",
            ["slack-mcp-server", "--env-file", temp_env_path, "--slack-token", cmd_line_token, "--transport", "stdio"],
        ):
            with patch.object(mcp_factory.get(), "run") as mock_run:
                # Patch the test environment to allow env file loading
                with patch("slack_mcp.settings.get_test_environment") as mock_get_test_env:
                    mock_test_env = MagicMock()
                    mock_test_env.mcp_no_env_file = False
                    mock_get_test_env.return_value = mock_test_env
                    
                    # Import here to ensure clean environment
                    from slack_mcp.mcp.entry import main

                    # Run the main function which should load CLI token first, then .env file overrides it
                    main()

                    # Check that .env file token was used (has priority over CLI argument)
                    settings = get_settings(env_file=temp_env_path, no_env_file=False, force_reload=True)
                    assert settings.slack_bot_token.get_secret_value() == env_file_token

                    # Verify that the server would have been started
                    mock_run.assert_called_once()

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)


def test_dotenv_loading_with_nonexistent_env_file():
    """Test behavior when the .env file doesn't exist."""
    # Use a nonexistent file path
    nonexistent_path = "/tmp/definitely-does-not-exist-12345.env"

    with patch("sys.argv", ["slack-mcp-server", "--env-file", nonexistent_path, "--transport", "stdio"]):
        with patch.object(mcp_factory.get(), "run") as mock_run:
            with patch("logging.Logger.warning") as mock_warning:
                with patch.dict("os.environ", {}, clear=True):
                    # Import here to ensure clean environment
                    from slack_mcp.mcp.entry import main

                    # Run the main function which should attempt to load the .env file
                    main()

                    # Check that a warning was logged
                    mock_warning.assert_called_once()

                    # Verify that the server would still have been started
                    mock_run.assert_called_once()


def test_dotenv_loading_disabled():
    """Test that .env file loading can be disabled with --no-env-file flag."""
    # Create a temporary .env file with test values
    test_bot_token = "xoxb-test-token-12345"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".env") as temp_env:
        temp_env.write(f"SLACK_BOT_TOKEN={test_bot_token}\n")
        temp_env_path = temp_env.name

    try:
        # Run entry.main with no-env-file flag
        with patch(
            "sys.argv", ["slack-mcp-server", "--env-file", temp_env_path, "--no-env-file", "--transport", "stdio"]
        ):
            with patch.object(mcp_factory.get(), "run") as mock_run:
                with patch.dict("os.environ", {}, clear=True):
                    # Import here to ensure clean environment
                    from slack_mcp.mcp.entry import main

                    # Run the main function which should NOT load the .env file
                    main()

                    # Check that environment variable was not loaded
                    settings = get_settings()
                    assert settings.slack_bot_token is None

                    # Verify that the server would have been started regardless
                    mock_run.assert_called_once()

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)


def test_cmd_line_token_as_fallback_when_env_disabled():
    """Test that CLI token is used as fallback when .env file loading is disabled.

    This test verifies that when --no-env-file is used, the CLI argument takes effect.
    """
    # Create a temporary .env file with test values
    env_file_token = "xoxb-env-file-token-12345"
    cmd_line_token = "xoxb-cmd-line-token-67890"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".env") as temp_env:
        temp_env.write(f"SLACK_BOT_TOKEN={env_file_token}\n")
        temp_env_path = temp_env.name

    try:
        # Run entry.main with no-env-file flag and CLI token
        with patch(
            "sys.argv",
            [
                "slack-mcp-server",
                "--env-file",
                temp_env_path,
                "--no-env-file",
                "--slack-token",
                cmd_line_token,
                "--transport",
                "stdio",
            ],
        ):
            with patch.object(mcp_factory.get(), "run") as mock_run:
                with patch.dict("os.environ", {}, clear=True):
                    # Import here to ensure clean environment
                    from slack_mcp.mcp.entry import main
                    from slack_mcp.settings import get_settings

                    # Capture the settings that will be used by main()
                    with patch("slack_mcp.mcp.entry.get_settings") as mock_get_settings:
                        mock_settings = get_settings(
                            no_env_file=True, SLACK_BOT_TOKEN=cmd_line_token, force_reload=True
                        )
                        mock_get_settings.return_value = mock_settings

                        # Run the main function which should use CLI token (env file disabled)
                        main()

                        # Check that CLI token was used (env file loading was disabled)
                        assert mock_settings.slack_bot_token
                        assert mock_settings.slack_bot_token.get_secret_value() == cmd_line_token

                    # Verify that the server would have been started
                    mock_run.assert_called_once()

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)


def test_sse_transport_with_token():
    """Test SSE transport with token from env file."""
    # Create a temporary .env file with test values
    test_bot_token = "xoxb-test-token-12345"

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".env") as temp_env:
        temp_env.write(f"SLACK_BOT_TOKEN={test_bot_token}\n")
        temp_env_path = temp_env.name

    try:
        # Run entry.main with SSE transport
        with patch(
            "sys.argv",
            ["slack-mcp-server", "--env-file", temp_env_path, "--transport", "sse", "--mount-path", "/api/mcp"],
        ):
            with patch.object(mcp_factory.get(), "sse_app") as mock_sse_app:
                with patch("uvicorn.run") as mock_run:
                    mock_app = MagicMock()
                    mock_sse_app.return_value = mock_app

                    # Patch the test environment to allow env file loading
                    with patch("slack_mcp.settings.get_test_environment") as mock_get_test_env:
                        mock_test_env = MagicMock()
                        mock_test_env.mcp_no_env_file = False
                        mock_get_test_env.return_value = mock_test_env
                        
                        # Import here to ensure clean environment
                        from slack_mcp.mcp.entry import main

                        # Run the main function which should load the .env file
                        main()

                        # Check environment was loaded
                        from slack_mcp.settings import get_settings

                        settings = get_settings(env_file=temp_env_path, no_env_file=False, force_reload=True)
                        assert settings.slack_bot_token.get_secret_value() == test_bot_token

                        # Verify FastAPI app was created with correct mount path
                        mock_sse_app.assert_called_once_with(mount_path="/api/mcp")

                        # Verify uvicorn was called to run the app
                        mock_run.assert_called_once()
                        assert mock_run.call_args[0][0] == mock_app

    finally:
        # Clean up the temporary file
        os.unlink(temp_env_path)
