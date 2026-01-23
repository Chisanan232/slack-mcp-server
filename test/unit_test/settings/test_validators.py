"""Unit tests for settings field validators.

This module tests the field validators in the settings models,
including CORS field validation logic.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from slack_mcp.settings import SettingModel


class TestSettingsValidators:
    """Test field validators in settings."""

    def test_parse_cors_origins_empty_string(self):
        """Test CORS origins validator with empty string (line 127-128)."""
        result = SettingModel.parse_cors_origins("")
        assert result == "*"

    def test_parse_cors_origins_whitespace_only(self):
        """Test CORS origins validator with whitespace only (line 127-128)."""
        result = SettingModel.parse_cors_origins("   ")
        assert result == "*"

    def test_parse_cors_origins_normal_string(self):
        """Test CORS origins validator with normal string (line 129)."""
        result = SettingModel.parse_cors_origins("https://example.com")
        assert result == "https://example.com"

    def test_parse_cors_origins_string_with_whitespace(self):
        """Test CORS origins validator with string containing whitespace (line 129)."""
        result = SettingModel.parse_cors_origins("  https://example.com  ")
        assert result == "https://example.com"

    def test_parse_cors_origins_none_value(self):
        """Test CORS origins validator with None value (line 130)."""
        result = SettingModel.parse_cors_origins(None)
        assert result == "*"

    def test_parse_cors_origins_non_string_value(self):
        """Test CORS origins validator with non-string value."""
        result = SettingModel.parse_cors_origins(["https://example.com"])
        assert result == ["https://example.com"]

    def test_parse_cors_methods_empty_string(self):
        """Test CORS methods validator with empty string (line 138-139)."""
        result = SettingModel.parse_cors_methods("")
        assert result == "*"

    def test_parse_cors_methods_whitespace_only(self):
        """Test CORS methods validator with whitespace only (line 138-139)."""
        result = SettingModel.parse_cors_methods("   ")
        assert result == "*"

    def test_parse_cors_methods_normal_string(self):
        """Test CORS methods validator with normal string (line 140)."""
        result = SettingModel.parse_cors_methods("GET,POST,PUT")
        assert result == "GET,POST,PUT"

    def test_parse_cors_methods_string_with_whitespace(self):
        """Test CORS methods validator with string containing whitespace (line 140)."""
        result = SettingModel.parse_cors_methods("  GET,POST,PUT  ")
        assert result == "GET,POST,PUT"

    def test_parse_cors_methods_none_value(self):
        """Test CORS methods validator with None value (line 141)."""
        result = SettingModel.parse_cors_methods(None)
        assert result == "*"

    def test_parse_cors_methods_non_string_value(self):
        """Test CORS methods validator with non-string value."""
        result = SettingModel.parse_cors_methods(["GET", "POST"])
        assert result == ["GET", "POST"]

    def test_parse_cors_headers_empty_string(self):
        """Test CORS headers validator with empty string (line 149-150)."""
        result = SettingModel.parse_cors_headers("")
        assert result == "*"

    def test_parse_cors_headers_whitespace_only(self):
        """Test CORS headers validator with whitespace only (line 149-150)."""
        result = SettingModel.parse_cors_headers("   ")
        assert result == "*"

    def test_parse_cors_headers_normal_string(self):
        """Test CORS headers validator with normal string (line 151)."""
        result = SettingModel.parse_cors_headers("Content-Type,Authorization")
        assert result == "Content-Type,Authorization"

    def test_parse_cors_headers_string_with_whitespace(self):
        """Test CORS headers validator with string containing whitespace (line 151)."""
        result = SettingModel.parse_cors_headers("  Content-Type,Authorization  ")
        assert result == "Content-Type,Authorization"

    def test_parse_cors_headers_none_value(self):
        """Test CORS headers validator with None value (line 152)."""
        result = SettingModel.parse_cors_headers(None)
        assert result == "*"

    def test_parse_cors_headers_non_string_value(self):
        """Test CORS headers validator with non-string value."""
        result = SettingModel.parse_cors_headers(["Content-Type", "Authorization"])
        assert result == ["Content-Type", "Authorization"]
