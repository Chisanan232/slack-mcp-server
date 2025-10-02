"""Unit tests for the webhook app module."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import Mock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slack_mcp.mcp.cli.models import MCPTransportType
from slack_mcp.webhook.app import WebServerFactory, mount_service, web_factory, web


class TestWebServerFactory:
    """Test cases for WebServerFactory class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        # Reset the factory before each test to ensure clean state
        WebServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # Reset the factory after each test to prevent side effects
        WebServerFactory.reset()

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_create_web_server_success(self, mock_mcp_factory: Mock) -> None:
        """Test successful creation of web server instance."""
        # Mock the lifespan function
        mock_lifespan = Mock()
        mock_mcp_factory.lifespan.return_value = mock_lifespan

        # Create the web server
        app = WebServerFactory.create()

        # Verify the app was created with correct configuration
        assert isinstance(app, FastAPI)
        assert app.title == "Slack MCP Server"
        assert app.description == "A FastAPI web server that hosts a Slack MCP server for interacting with Slack API"
        assert app.version == "0.1.0"
        
        # Verify lifespan was configured
        mock_mcp_factory.lifespan.assert_called_once()
        
        # Verify CORS middleware was added
        cors_middleware_found = False
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                cors_middleware_found = True
                break
        assert cors_middleware_found, "CORS middleware should be added to the FastAPI app"

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_create_web_server_singleton_behavior(self, mock_mcp_factory: Mock) -> None:
        """Test that WebServerFactory enforces singleton pattern."""
        # Mock the lifespan function
        mock_mcp_factory.lifespan.return_value = Mock()

        # Create the first instance
        app1 = WebServerFactory.create()
        
        # Attempting to create a second instance should raise an assertion error
        with pytest.raises(AssertionError, match="It is not allowed to create more than one instance of web server"):
            WebServerFactory.create()

        # Verify first instance is still accessible
        assert WebServerFactory.get() is app1

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_get_web_server_success(self, mock_mcp_factory: Mock) -> None:
        """Test successful retrieval of web server instance."""
        # Mock the lifespan function
        mock_mcp_factory.lifespan.return_value = Mock()

        # Create the web server first
        app = WebServerFactory.create()
        
        # Get the instance
        retrieved_app = WebServerFactory.get()
        
        # Verify it's the same instance
        assert retrieved_app is app

    def test_get_web_server_without_create_raises_error(self) -> None:
        """Test that get() raises error when no instance has been created."""
        with pytest.raises(AssertionError, match="It must be created web server first"):
            WebServerFactory.get()

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_reset_web_server(self, mock_mcp_factory: Mock) -> None:
        """Test that reset() properly clears the singleton instance."""
        # Mock the lifespan function
        mock_mcp_factory.lifespan.return_value = Mock()

        # Create the web server
        WebServerFactory.create()
        
        # Verify it exists
        app = WebServerFactory.get()
        assert isinstance(app, FastAPI)
        
        # Reset the factory
        WebServerFactory.reset()
        
        # Verify we can't get the instance anymore
        with pytest.raises(AssertionError, match="It must be created web server first"):
            WebServerFactory.get()
        
        # Verify we can create a new instance after reset
        new_app = WebServerFactory.create()
        assert isinstance(new_app, FastAPI)
        assert new_app is not app  # Should be a different instance

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_create_with_kwargs(self, mock_mcp_factory: Mock) -> None:
        """Test that create() accepts kwargs for base class compatibility."""
        # Mock the lifespan function
        mock_mcp_factory.lifespan.return_value = Mock()

        # Create with additional kwargs (should be ignored)
        app = WebServerFactory.create(some_param="test", another_param=123)
        
        # Verify the app was created successfully despite extra kwargs
        assert isinstance(app, FastAPI)
        assert app.title == "Slack MCP Server"


class TestMountService:
    """Test cases for mount_service function."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        # Reset the factory before each test
        WebServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # Reset the factory after each test
        WebServerFactory.reset()

    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
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
        mount_service(transport=MCPTransportType.SSE, mount_path="/custom", sse_mount_path="/sse-path")
        
        # Verify the correct methods were called
        mock_web_factory.get.assert_called_once()
        mock_mcp_factory.get.assert_called_once()
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path="/sse-path")
        mock_app.mount.assert_called_once_with(path="/custom", app=mock_mcp_app)

    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
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
        mount_service(transport=MCPTransportType.SSE, mount_path="", sse_mount_path="/sse-path")
        
        # Verify default mount path was used
        mock_app.mount.assert_called_once_with(path="/mcp", app=mock_mcp_app)
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path="/sse-path")

    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
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
        mount_service(transport=MCPTransportType.STREAMABLE_HTTP, mount_path="/api", sse_mount_path="/unused")
        
        # Verify the correct methods were called
        mock_web_factory.get.assert_called_once()
        mock_mcp_factory.get.assert_called_once()
        mock_mcp_instance.streamable_http_app.assert_called_once_with()
        mock_app.mount.assert_called_once_with(path="/api", app=mock_mcp_app)
        
        # Verify sse_app was not called for streamable-HTTP
        mock_mcp_instance.sse_app.assert_not_called()

    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
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
        mount_service(transport=MCPTransportType.STREAMABLE_HTTP, mount_path="")
        
        # Verify default mount path was used
        mock_app.mount.assert_called_once_with(path="/mcp", app=mock_mcp_app)

    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
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
        mount_service()
        
        # Verify defaults: SSE transport, /mcp mount path, empty sse_mount_path
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path="")
        mock_app.mount.assert_called_once_with(path="/mcp", app=mock_mcp_app)

    def test_mount_service_invalid_transport(self) -> None:
        """Test that mount_service raises ValueError for invalid transport."""
        with pytest.raises(ValueError, match="Unknown transport protocol: invalid-transport"):
            mount_service(transport="invalid-transport")

    @patch("slack_mcp.webhook.app._LOG")
    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
    def test_mount_service_logging_sse(self, mock_web_factory: Mock, mock_mcp_factory: Mock, mock_log: Mock) -> None:
        """Test that mount_service logs correctly for SSE transport."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = Mock()
        mock_mcp_factory.get.return_value = mock_mcp_instance
        
        # Call mount_service
        mount_service(transport=MCPTransportType.SSE, sse_mount_path="/test-sse")
        
        # Verify logging
        mock_log.info.assert_called_with("Mounting MCP server with SSE transport at path: /test-sse")

    @patch("slack_mcp.webhook.app._LOG")
    @patch("slack_mcp.webhook.app.mcp_factory")
    @patch("slack_mcp.webhook.app.web_factory")
    def test_mount_service_logging_streamable_http(self, mock_web_factory: Mock, mock_mcp_factory: Mock, mock_log: Mock) -> None:
        """Test that mount_service logs correctly for streamable-HTTP transport."""
        # Mock dependencies
        mock_app = Mock(spec=FastAPI)
        mock_web_factory.get.return_value = mock_app
        mock_mcp_instance = Mock()
        mock_mcp_instance.streamable_http_app.return_value = Mock()
        mock_mcp_factory.get.return_value = mock_mcp_instance
        
        # Call mount_service
        mount_service(transport=MCPTransportType.STREAMABLE_HTTP)
        
        # Verify logging
        mock_log.info.assert_called_with("Integrating MCP server with streamable-http transport")


class TestGlobalInstances:
    """Test cases for global instances and module-level behavior."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        WebServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        WebServerFactory.reset()

    def test_web_factory_instance(self) -> None:
        """Test that web_factory is correctly assigned to WebServerFactory."""
        from slack_mcp.webhook.app import web_factory
        assert web_factory is WebServerFactory

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_web_global_instance_creation(self, mock_mcp_factory: Mock) -> None:
        """Test that the global 'web' instance is created correctly."""
        # Mock the lifespan function
        mock_mcp_factory.lifespan.return_value = Mock()

        # Import the module to trigger global instance creation
        from slack_mcp.webhook.app import web
        
        # Verify the global web instance is a FastAPI app
        assert isinstance(web, FastAPI)
        assert web.title == "Slack MCP Server"

    def test_module_constants(self) -> None:
        """Test that module-level constants are correctly defined."""
        from slack_mcp.webhook.app import _LOG, _WEB_SERVER_INSTANCE
        
        # Verify logger is set up
        import logging
        assert isinstance(_LOG, logging.Logger)
        assert _LOG.name == "slack_mcp.webhook.app"
        
        # Verify initial state of global instance
        # Note: _WEB_SERVER_INSTANCE should be None initially if we reset properly


class TestIntegration:
    """Integration tests for the webhook app module."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        WebServerFactory.reset()

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        WebServerFactory.reset()

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_full_workflow_sse_transport(self, mock_mcp_factory: Mock) -> None:
        """Test the complete workflow: create server -> mount SSE service."""
        # Mock the lifespan and MCP components
        mock_mcp_factory.lifespan.return_value = Mock()
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.sse_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance
        
        # Create web server
        app = WebServerFactory.create()
        
        # Mount SSE service
        mount_service(transport=MCPTransportType.SSE, mount_path="/mcp", sse_mount_path="/sse")
        
        # Verify the service was mounted on the created app
        mock_mcp_instance.sse_app.assert_called_once_with(mount_path="/sse")
        
        # Verify the app has the mounted service
        # Note: In real FastAPI, this would be visible in app.routes, but our mock doesn't track this

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_full_workflow_streamable_http_transport(self, mock_mcp_factory: Mock) -> None:
        """Test the complete workflow: create server -> mount streamable-HTTP service."""
        # Mock the lifespan and MCP components
        mock_mcp_factory.lifespan.return_value = Mock()
        mock_mcp_app = Mock(spec=FastAPI)
        mock_mcp_instance = Mock()
        mock_mcp_instance.streamable_http_app.return_value = mock_mcp_app
        mock_mcp_factory.get.return_value = mock_mcp_instance
        
        # Create web server
        app = WebServerFactory.create()
        
        # Mount streamable-HTTP service
        mount_service(transport=MCPTransportType.STREAMABLE_HTTP, mount_path="/api")
        
        # Verify the service was mounted
        mock_mcp_instance.streamable_http_app.assert_called_once_with()

    @patch("slack_mcp.webhook.app.mcp_factory")
    def test_error_handling_mount_without_server(self, mock_mcp_factory: Mock) -> None:
        """Test error handling when trying to mount service without creating server first."""
        # Don't create the web server instance
        
        # Attempting to mount service should fail when trying to get the server
        with pytest.raises(AssertionError, match="It must be created web server first"):
            mount_service(transport=MCPTransportType.SSE)
