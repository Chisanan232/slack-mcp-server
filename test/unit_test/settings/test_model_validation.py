"""Unit tests for settings model validation scenarios.

This module tests comprehensive settings model validation scenarios,
including field validation and model instantiation.
"""

import os
from unittest.mock import patch
import pytest

from slack_mcp.settings import SettingModel


class TestSettingsModelValidation:
    """Test comprehensive settings model validation scenarios."""

    def test_model_with_all_cors_fields_as_empty_strings(self):
        """Test model creation with all CORS fields as empty strings."""
        with patch.dict(os.environ, {
            "CORS_ALLOW_ORIGINS": "",
            "CORS_ALLOW_METHODS": "",
            "CORS_ALLOW_HEADERS": "",
        }):
            model = SettingModel(_env_file=None)
            
            # All should default to "*" when empty strings are provided
            assert model.cors_allow_origins == "*"
            assert model.cors_allow_methods == "*"
            assert model.cors_allow_headers == "*"

    def test_model_with_mixed_cors_field_types(self):
        """Test model creation with mixed types for CORS fields."""
        # Test with direct model instantiation to avoid environment variable issues
        model = SettingModel(
            cors_allow_origins="https://example.com",
            cors_allow_methods="GET,POST",  # String instead of list for consistency
            cors_allow_headers=None,
            _env_file=None
        )
        
        # Should handle different types appropriately
        assert model.cors_allow_origins == "https://example.com"
        assert model.cors_allow_methods == "GET,POST"
        assert model.cors_allow_headers == "*"

    def test_model_with_whitespace_padded_cors_values(self):
        """Test model creation with whitespace-padded CORS values."""
        with patch.dict(os.environ, {
            "CORS_ALLOW_ORIGINS": "  https://example.com,https://test.com  ",
            "CORS_ALLOW_METHODS": "  GET,POST,PUT  ",
            "CORS_ALLOW_HEADERS": "  Content-Type,Authorization  ",
        }, clear=True):
            model = SettingModel(_env_file=None)
            
            # Should strip whitespace from string values
            assert model.cors_allow_origins == "https://example.com,https://test.com"
            assert model.cors_allow_methods == "GET,POST,PUT"
            assert model.cors_allow_headers == "Content-Type,Authorization"
