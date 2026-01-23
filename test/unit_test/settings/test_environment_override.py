"""Unit tests for settings environment-based overrides.

This module tests environment-based settings overrides and
configuration loading logic.
"""

from unittest.mock import MagicMock, patch

from slack_mcp.settings import get_settings


class TestSettingsEnvironmentOverride:
    """Test environment-based settings overrides."""

    def test_test_environment_overrides_no_env_file(self):
        """Test that test environment can override no_env_file setting (line 200-201)."""
        with patch("slack_mcp.settings.get_test_environment") as mock_get_test_env:
            mock_test_env = MagicMock()
            mock_test_env.mcp_no_env_file = True
            mock_get_test_env.return_value = mock_test_env

            # Call get_settings with no_env_file=False
            with patch("slack_mcp.settings.SettingModel") as mock_model:
                mock_model.return_value = MagicMock()

                get_settings(no_env_file=False, force_reload=True)

                # Should be called with no_env_file=True due to test environment override
                call_args = mock_model.call_args
                assert call_args[1]["_env_file"] is None  # None when no_env_file is True

    def test_normal_environment_respects_no_env_file(self):
        """Test that normal environment respects no_env_file parameter."""
        with patch("slack_mcp.settings.get_test_environment") as mock_get_test_env:
            mock_test_env = MagicMock()
            mock_test_env.mcp_no_env_file = False
            mock_get_test_env.return_value = mock_test_env

            # Call get_settings with no_env_file=True
            with patch("slack_mcp.settings.SettingModel") as mock_model:
                mock_model.return_value = MagicMock()

                get_settings(no_env_file=True, force_reload=True)

                # Should be called with no_env_file=True as specified
                call_args = mock_model.call_args
                assert call_args[1]["_env_file"] is None  # None when no_env_file is True

    def test_normal_environment_respects_env_file_path(self):
        """Test that normal environment respects env_file path when no_env_file=False."""
        with patch("slack_mcp.settings.get_test_environment") as mock_get_test_env:
            mock_test_env = MagicMock()
            mock_test_env.mcp_no_env_file = False
            mock_get_test_env.return_value = mock_test_env

            # Call get_settings with custom env file
            with patch("slack_mcp.settings.SettingModel") as mock_model:
                mock_model.return_value = MagicMock()

                custom_env_file = "/path/to/custom.env"
                get_settings(env_file=custom_env_file, no_env_file=False, force_reload=True)

                # Should be called with the custom env file path
                call_args = mock_model.call_args
                assert call_args[1]["_env_file"] == custom_env_file
