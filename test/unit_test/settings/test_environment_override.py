"""Unit tests for settings environment-based overrides.

This module tests environment-based settings overrides and
configuration loading logic.
"""

from unittest.mock import MagicMock, patch

from slack_mcp.settings import get_settings


class TestSettingsEnvironmentOverride:
    """Test environment-based settings overrides."""

    def test_normal_environment_respects_no_env_file_parameter(self):
        """Test that get_settings respects the no_env_file parameter directly."""
        # Call get_settings with no_env_file=True
        with patch("slack_mcp.settings.SettingModel") as mock_model:
            mock_model.return_value = MagicMock()

            get_settings(no_env_file=True, force_reload=True)

            # Should be called with no_env_file=True as specified
            call_args = mock_model.call_args
            assert call_args[1]["_env_file"] is None  # None when no_env_file is True

    def test_normal_environment_respects_env_file_path(self):
        """Test that normal environment respects env_file path when no_env_file=False."""
        # Call get_settings with custom env file
        with patch("slack_mcp.settings.SettingModel") as mock_model:
            mock_model.return_value = MagicMock()

            custom_env_file = "/path/to/custom.env"
            get_settings(env_file=custom_env_file, no_env_file=False, force_reload=True)

            # Should be called with the custom env file path
            call_args = mock_model.call_args
            assert call_args[1]["_env_file"] == custom_env_file
