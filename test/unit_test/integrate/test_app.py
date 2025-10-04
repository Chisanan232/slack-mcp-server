"""Unit tests for the integrated server app module."""

from __future__ import annotations

from unittest.mock import Mock, call, patch

import pytest
from fastapi import FastAPI

from slack_mcp.integrate.app import IntegratedServerFactory
from slack_mcp.mcp.cli.models import MCPTransportType


class TestIntegratedServerFactory:
    """Test cases for IntegratedServerFactory class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        IntegratedServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        IntegratedServerFactory.reset()

    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app.health_check_router")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_create_success_with_defaults(
        self,
        mock_web_factory: Mock,
        mock_mcp_factory: Mock,
        mock_health_router: Mock,
        mock_init_client: Mock,
        mock_create_app: Mock,
    ) -> None:
        """Test successful creation with default parameters."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app
        mock_health_router.return_value = Mock()
        mock_web_factory.get.return_value = mock_app
        mock_mcp_factory.get.return_value = Mock()

        # Create server with defaults
        result = IntegratedServerFactory.create()

        # Verify result
        assert result is mock_app
        assert IntegratedServerFactory.get() is mock_app

        # Verify method calls
        mock_create_app.assert_called_once()
        mock_init_client.assert_not_called()  # No token provided

    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app.health_check_router")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_create_success_with_token(
        self,
        mock_web_factory: Mock,
        mock_mcp_factory: Mock,
        mock_health_router: Mock,
        mock_init_client: Mock,
        mock_create_app: Mock,
    ) -> None:
        """Test successful creation with token provided."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app
        mock_health_router.return_value = Mock()
        mock_web_factory.get.return_value = mock_app
        mock_mcp_factory.get.return_value = Mock()

        # Create server with token
        result = IntegratedServerFactory.create(token="test-token", retry=5)

        # Verify result
        assert result is mock_app

        # Verify Slack client initialization was called
        mock_init_client.assert_called_once_with("test-token", retry=5)

    @patch("slack_mcp.integrate.app.create_slack_app")
    def test_create_invalid_transport_type(self, mock_create_app: Mock) -> None:
        """Test creation with invalid transport type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid transport type for integrated server: invalid"):
            IntegratedServerFactory.create(mcp_transport="invalid")

        # Verify create_slack_app was not called
        mock_create_app.assert_not_called()

    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app.health_check_router")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_create_with_custom_parameters(
        self,
        mock_web_factory: Mock,
        mock_mcp_factory: Mock,
        mock_health_router: Mock,
        mock_init_client: Mock,
        mock_create_app: Mock,
    ) -> None:
        """Test creation with custom parameters."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app
        mock_health_router.return_value = Mock()
        mock_web_factory.get.return_value = mock_app
        mock_mcp_factory.get.return_value = Mock()

        # Create server with custom parameters
        result = IntegratedServerFactory.create(
            token="custom-token", mcp_transport="streamable-http", mcp_mount_path="/custom-mcp", retry=10
        )

        # Verify result
        assert result is mock_app

        # Verify Slack client initialization with custom retry
        mock_init_client.assert_called_once_with("custom-token", retry=10)

    def test_get_success(self) -> None:
        """Test successful get after creation."""
        with (
            patch("slack_mcp.integrate.app.create_slack_app") as mock_create_app,
            patch("slack_mcp.integrate.app.initialize_slack_client"),
            patch("slack_mcp.integrate.app.health_check_router"),
            patch("slack_mcp.integrate.app.mcp_factory"),
            patch("slack_mcp.integrate.app.web_factory") as mock_web_factory,
        ):
            mock_app = Mock(spec=FastAPI)
            mock_create_app.return_value = mock_app
            mock_web_factory.get.return_value = mock_app

            # Create first, then get
            IntegratedServerFactory.create()
            result = IntegratedServerFactory.get()

            assert result is mock_app

    def test_get_without_create_raises_error(self) -> None:
        """Test that get() raises error when no instance has been created."""
        with pytest.raises(AssertionError, match="It must be created web server first"):
            IntegratedServerFactory.get()

    def test_reset_clears_instance(self) -> None:
        """Test that reset() properly clears the singleton instance."""
        with (
            patch("slack_mcp.integrate.app.create_slack_app") as mock_create_app,
            patch("slack_mcp.integrate.app.initialize_slack_client"),
            patch("slack_mcp.integrate.app.health_check_router"),
            patch("slack_mcp.integrate.app.mcp_factory"),
            patch("slack_mcp.integrate.app.web_factory") as mock_web_factory,
        ):
            mock_app = Mock(spec=FastAPI)
            mock_create_app.return_value = mock_app
            mock_web_factory.get.return_value = mock_app

            # Create, verify exists, reset, verify cleared
            IntegratedServerFactory.create()
            assert IntegratedServerFactory.get() is mock_app

            IntegratedServerFactory.reset()

            with pytest.raises(AssertionError, match="It must be created web server first"):
                IntegratedServerFactory.get()

    @patch("slack_mcp.integrate.app.initialize_slack_client")
    def test_prepare_with_token(self, mock_init_client: Mock) -> None:
        """Test _prepare method with token provided."""
        IntegratedServerFactory._prepare(token="test-token", retry=7)
        mock_init_client.assert_called_once_with("test-token", retry=7)

    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app._LOG")
    def test_prepare_without_token(self, mock_log: Mock, mock_init_client: Mock) -> None:
        """Test _prepare method without token (deferred initialization)."""
        IntegratedServerFactory._prepare(token=None, retry=3)

        # Verify no client initialization
        mock_init_client.assert_not_called()

        # Verify logging message
        mock_log.info.assert_called_once_with("Deferring Slack client initialization - token will be set later")

    @patch("slack_mcp.integrate.app.health_check_router")
    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_includes_health_check_router(
        self,
        mock_web_factory: Mock,
        mock_mcp_factory: Mock,
        mock_init_client: Mock,
        mock_create_app: Mock,
        mock_health_router: Mock,
    ) -> None:
        """Test _mount method includes health check router."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app
        mock_router = Mock()
        mock_health_router.return_value = mock_router
        mock_web_factory.get.return_value = mock_app
        mock_mcp_factory.get.return_value = Mock()

        # Create server (which calls _mount internally)
        IntegratedServerFactory.create(mcp_transport="sse")

        # Global instance should be set first
        global_instance = IntegratedServerFactory.get()

        # Verify health check router was created with correct transport
        mock_health_router.assert_called_once_with(mcp_transport="sse")

        # Verify router was included in the app
        global_instance.include_router.assert_called_once_with(mock_router)

    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app.health_check_router")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_multiple_create_calls_recreate_instance(
        self,
        mock_web_factory: Mock,
        mock_mcp_factory: Mock,
        mock_health_router: Mock,
        mock_init_client: Mock,
        mock_create_app: Mock,
    ) -> None:
        """Test that multiple create calls recreate the global instance."""
        # Mock dependencies
        mock_app1 = Mock(spec=FastAPI)
        mock_app2 = Mock(spec=FastAPI)
        mock_create_app.side_effect = [mock_app1, mock_app2]
        mock_health_router.return_value = Mock()
        mock_web_factory.get.side_effect = [mock_app1, mock_app2]  # Return different apps for each call
        mock_mcp_factory.get.return_value = Mock()

        # Create first instance
        result1 = IntegratedServerFactory.create()
        assert result1 is mock_app1

        # Create second instance - should recreate and return new instance
        result2 = IntegratedServerFactory.create()
        assert result2 is mock_app2  # Should be the new instance

        # Verify create_slack_app was called twice
        assert mock_create_app.call_count == 2

    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    @patch("slack_mcp.integrate.app.health_check_router")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_create_multiple_calls_with_different_parameters(
        self,
        mock_web_factory: Mock,
        mock_mcp_factory: Mock,
        mock_health_router: Mock,
        mock_init_client: Mock,
        mock_create_app: Mock,
    ) -> None:
        """Test multiple create calls with different parameters."""
        # Mock dependencies
        mock_app1 = Mock(spec=FastAPI)
        mock_app2 = Mock(spec=FastAPI)
        mock_create_app.side_effect = [mock_app1, mock_app2]
        mock_health_router.return_value = Mock()
        mock_web_factory.get.side_effect = [mock_app1, mock_app2]
        mock_mcp_factory.get.return_value = Mock()

        # First create with specific parameters
        result1 = IntegratedServerFactory.create(token="token1", mcp_transport="sse")

        # Second create with different parameters - creates new instance
        result2 = IntegratedServerFactory.create(token="token2", mcp_transport="streamable-http")

        assert result1 is mock_app1
        assert result2 is mock_app2

        # Verify initialization was called twice with different parameters
        assert mock_init_client.call_count == 2
        mock_init_client.assert_has_calls([call("token1", retry=3), call("token2", retry=3)])

    def test_parameter_extraction_and_defaults(self) -> None:
        """Test parameter extraction and default value handling."""
        with (
            patch("slack_mcp.integrate.app.create_slack_app") as mock_create_app,
            patch("slack_mcp.integrate.app.initialize_slack_client") as mock_init_client,
            patch("slack_mcp.integrate.app.health_check_router"),
            patch("slack_mcp.integrate.app.mcp_factory"),
            patch("slack_mcp.integrate.app.web_factory") as mock_web_factory,
        ):
            mock_app = Mock(spec=FastAPI)
            mock_create_app.return_value = mock_app
            mock_web_factory.get.return_value = mock_app

            # Test with no parameters (all defaults)
            IntegratedServerFactory.reset()
            IntegratedServerFactory.create()

            # Should not initialize client (no token)
            mock_init_client.assert_not_called()

            # Test with partial parameters
            IntegratedServerFactory.reset()
            mock_init_client.reset_mock()
            IntegratedServerFactory.create(retry=8)

            # Should still not initialize client (no token), but retry default should be overridden
            mock_init_client.assert_not_called()


class TestModuleLevelConstants:
    """Test cases for module-level constants and initialization."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        IntegratedServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        IntegratedServerFactory.reset()

    def test_integrated_factory_constant(self) -> None:
        """Test that integrated_factory constant is properly assigned."""
        from slack_mcp.integrate.app import integrated_factory

        assert integrated_factory is IntegratedServerFactory

    def test_module_initialization_constants_available(self) -> None:
        """Test that module initialization properly sets up constants and no automatic instance creation."""
        # Import the integrated_factory constant - this should work without any dependencies
        from slack_mcp.integrate.app import integrated_factory

        # The integrated_factory should be the IntegratedServerFactory class
        assert integrated_factory is IntegratedServerFactory

        # Verify no global instance exists automatically - should require explicit creation
        with pytest.raises(AssertionError, match="It must be created web server first"):
            IntegratedServerFactory.get()


class TestEdgeCasesAndErrorScenarios:
    """Test cases for edge cases and error scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        IntegratedServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        IntegratedServerFactory.reset()

    def test_create_with_empty_string_transport(self) -> None:
        """Test creation with empty string transport raises ValueError."""
        with pytest.raises(ValueError, match="Invalid transport type for integrated server: "):
            IntegratedServerFactory.create(mcp_transport="")

    def test_create_with_none_transport(self) -> None:
        """Test creation with None transport raises ValueError."""
        with pytest.raises(ValueError, match="Invalid transport type for integrated server: None"):
            IntegratedServerFactory.create(mcp_transport=None)

    @patch("slack_mcp.integrate.app.create_slack_app")
    def test_create_with_exception_during_creation(self, mock_create_app: Mock) -> None:
        """Test handling of exceptions during app creation."""
        # Mock create_slack_app to raise an exception
        mock_create_app.side_effect = RuntimeError("Failed to create Slack app")

        with pytest.raises(RuntimeError, match="Failed to create Slack app"):
            IntegratedServerFactory.create()

        # Verify the global instance is not set when creation fails
        with pytest.raises(AssertionError, match="It must be created web server first"):
            IntegratedServerFactory.get()

    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    def test_create_with_client_initialization_failure(self, mock_init_client: Mock, mock_create_app: Mock) -> None:
        """Test handling of Slack client initialization failure."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app
        mock_init_client.side_effect = ValueError("Invalid token")

        with (
            patch("slack_mcp.integrate.app.health_check_router"),
            patch("slack_mcp.integrate.app.mcp_factory"),
            patch("slack_mcp.integrate.app.web_factory") as mock_web_factory,
        ):
            mock_web_factory.get.return_value = mock_app

            # Should raise the client initialization error
            with pytest.raises(ValueError, match="Invalid token"):
                IntegratedServerFactory.create(token="invalid-token")

    def test_prepare_with_negative_retry(self) -> None:
        """Test _prepare method with negative retry value."""
        with patch("slack_mcp.integrate.app.initialize_slack_client") as mock_init_client:
            # This should not raise an error - the validation is in initialize_slack_client
            IntegratedServerFactory._prepare(token="test-token", retry=-1)
            mock_init_client.assert_called_once_with("test-token", retry=-1)

    def test_prepare_with_zero_retry(self) -> None:
        """Test _prepare method with zero retry value."""
        with patch("slack_mcp.integrate.app.initialize_slack_client") as mock_init_client:
            IntegratedServerFactory._prepare(token="test-token", retry=0)
            mock_init_client.assert_called_once_with("test-token", retry=0)


class TestMountService:
    """Test cases for mount_service function."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        # Reset the factory before each test
        IntegratedServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # Reset the factory after each test
        IntegratedServerFactory.reset()

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_sse_transport(self, mock_web_factory: Mock, mock_mcp_factory: Mock) -> None:
        """Test mounting service with SSE transport."""
        # Mock the web server instance
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service with SSE transport
        IntegratedServerFactory._mount_mcp_service(
            transport=MCPTransportType.SSE, mount_path="/custom", sse_mount_path="/sse-path"
        )

        # Verify the correct methods were called
        mock_web_factory.get.assert_called_once()
        mock_mcp_factory.get.assert_called_once()
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path="/sse-path")
        mock_app.mount.assert_called_once_with(path="/custom", app=mock_mcp_app)

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_sse_default_path(self, mock_web_factory: Mock, mock_mcp_factory: Mock) -> None:
        """Test mounting service with SSE transport using default path."""
        # Mock the web server instance
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service with empty mount_path (should default to /mcp)
        IntegratedServerFactory._mount_mcp_service(
            transport=MCPTransportType.SSE, mount_path="", sse_mount_path="/sse-path"
        )

        # Verify default mount path was used
        mock_app.mount.assert_called_once_with(path="/mcp", app=mock_mcp_app)
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path="/sse-path")

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_streamable_http_transport(self, mock_web_factory: Mock, mock_mcp_factory: Mock) -> None:
        """Test mounting service with streamable-HTTP transport."""
        # Mock the web server instance
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.streamable_http_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service with streamable-HTTP transport
        IntegratedServerFactory._mount_mcp_service(
            transport=MCPTransportType.STREAMABLE_HTTP, mount_path="/api", sse_mount_path="/unused"
        )

        # Verify the correct methods were called
        mock_web_factory.get.assert_called_once()
        mock_mcp_factory.get.assert_called_once()
        mock_mcp_instance.streamable_http_app.assert_called_once_with()
        mock_app.mount.assert_called_once_with(path="/api", app=mock_mcp_app)

        # Verify sse_app was not called for streamable-HTTP
        mock_mcp_instance.sse_app.assert_not_called()

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_streamable_http_default_path(self, mock_web_factory: Mock, mock_mcp_factory: Mock) -> None:
        """Test mounting service with streamable-HTTP transport using default path."""
        # Mock the web server instance
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.streamable_http_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service with empty mount_path (should default to /mcp)
        IntegratedServerFactory._mount_mcp_service(transport=MCPTransportType.STREAMABLE_HTTP, mount_path="")

        # Verify default mount path was used
        mock_app.mount.assert_called_once_with(path="/mcp", app=mock_mcp_app)

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_default_parameters(self, mock_web_factory: Mock, mock_mcp_factory: Mock) -> None:
        """Test mounting service with all default parameters."""
        # Mock the web server instance
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service with no parameters (should use defaults)
        IntegratedServerFactory._mount_mcp_service()

        # Verify defaults: SSE transport, /mcp mount path, None sse_mount_path (default behavior)
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path=None)
        mock_app.mount.assert_called_once_with(path="/mcp", app=mock_mcp_app)

    def test_mount_service_invalid_transport(self) -> None:
        """Test that mount_service raises ValueError for invalid transport."""
        with pytest.raises(ValueError, match="Unknown transport protocol: invalid-transport"):
            IntegratedServerFactory._mount_mcp_service(transport="invalid-transport")

    @patch("slack_mcp.integrate.app._LOG")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_logging_sse(self, mock_web_factory: Mock, mock_mcp_factory: Mock, mock_log: Mock) -> None:
        """Test that mount_service logs correctly for SSE transport."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = Mock()
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service
        IntegratedServerFactory._mount_mcp_service(transport=MCPTransportType.SSE, sse_mount_path="/test-sse")

        # Verify logging
        mock_log.info.assert_called_with("Mounting MCP server with SSE transport at path: /test-sse")

    @patch("slack_mcp.integrate.app._LOG")
    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.web_factory")
    def test_mount_service_logging_streamable_http(
        self, mock_web_factory: Mock, mock_mcp_factory: Mock, mock_log: Mock
    ) -> None:
        """Test that mount_service logs correctly for streamable-HTTP transport."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app
        mock_mcp_instance = Mock()
        mock_mcp_instance.streamable_http_app.return_value = Mock()
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Call mount_service
        IntegratedServerFactory._mount_mcp_service(transport=MCPTransportType.STREAMABLE_HTTP)

        # Verify logging
        mock_log.info.assert_called_with("Integrating MCP server with streamable-http transport")


class TestIntegration:
    """Integration tests for the webhook app module."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        IntegratedServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        IntegratedServerFactory.reset()

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    def test_full_workflow_sse_transport(
        self, mock_init_client: Mock, mock_create_app: Mock, mock_mcp_factory: Mock
    ) -> None:
        """Test the complete workflow: create server -> mount SSE service."""
        # Mock the create_slack_app to return a mock FastAPI app
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app

        # Mock the initialize_slack_client to do nothing
        mock_init_client.return_value = None

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Create integrated server (this will call _mount internally)
        app = IntegratedServerFactory.create(mcp_transport="sse", mcp_mount_path="/mcp")

        # Verify the MCP instance sse_app was called during creation (mount_path is always None for SSE)
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path=None)

        # Verify the create_slack_app was called
        mock_create_app.assert_called_once()

    @patch("slack_mcp.integrate.app.mcp_factory")
    @patch("slack_mcp.integrate.app.create_slack_app")
    @patch("slack_mcp.integrate.app.initialize_slack_client")
    def test_full_workflow_streamable_http_transport(
        self, mock_init_client: Mock, mock_create_app: Mock, mock_mcp_factory: Mock
    ) -> None:
        """Test the complete workflow: create server -> mount streamable-HTTP service."""
        # Mock the create_slack_app to return a mock FastAPI app
        mock_app = Mock(spec=FastAPI)
        mock_create_app.return_value = mock_app

        # Mock the initialize_slack_client to do nothing
        mock_init_client.return_value = None

        # Mock the MCP factory
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.streamable_http_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance

        # Create integrated server (this will call _mount internally)
        app = IntegratedServerFactory.create(mcp_transport="streamable-http", mcp_mount_path="/api")

        # Verify the MCP instance streamable_http_app was called during creation
        mock_mcp_instance.streamable_http_app.assert_called_once_with()

        # Verify the create_slack_app was called
        mock_create_app.assert_called_once()

    @patch("slack_mcp.integrate.app.web_factory")
    @patch("slack_mcp.integrate.app.mcp_factory")
    def test_error_handling_mount_without_server(self, mock_mcp_factory: Mock, mock_web_factory: Mock) -> None:
        """Test error handling when trying to mount service without creating server first."""
        # Mock web_factory.get() to raise an error (simulating no web server created)
        mock_web_factory.get.side_effect = AssertionError("It must be created web server first.")

        # Don't create the web server instance - just call the mount method directly
        # Attempting to mount service should fail when trying to get the server
        with pytest.raises(AssertionError, match="It must be created web server first"):
            IntegratedServerFactory._mount_mcp_service(transport=MCPTransportType.SSE)
