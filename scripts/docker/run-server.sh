#!/bin/bash
set -e

#
# This script is a router that runs either the MCP server or Slack webhook server
# based on the SERVICE_TYPE environment variable.
#
# Environment variables:
#
# SERVICE_TYPE → Determines which service to run
#    - "mcp": Runs the MCP server (run-mcp-server.sh)
#    - "webhook": Runs the Slack webhook server (run-slack-webhook-server.sh)
#    - "integrated": Runs either server in integrated mode
#
# For all other environment variables, see the respective server scripts:
# - run-mcp-server.sh
# - run-slack-webhook-server.sh
#

# Default to MCP server if SERVICE_TYPE is not set
SERVICE_TYPE=${SERVICE_TYPE:-mcp}

# Directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Print informational message
echo "SERVICE_TYPE is set to: ${SERVICE_TYPE}"

# Determine which server to run based on SERVICE_TYPE
case "${SERVICE_TYPE}" in
  mcp)
    echo "Starting MCP server..."
    exec "${SCRIPT_DIR}/run-mcp-server.sh"
    ;;
    
  webhook)
    echo "Starting Slack webhook server..."
    exec "${SCRIPT_DIR}/run-slack-webhook-server.sh"
    ;;
    
  integrated)
    # For integrated mode, we can use either entry point with the --integrated flag
    # Default to MCP server with integrated flag
    echo "Starting integrated server via MCP entry point..."
    
    # Force integrated mode
    export MCP_INTEGRATED=true
    
    # If specific options for integrated mode are provided, use them
    # otherwise use defaults
    
    # Execute the MCP server with integrated flag
    exec "${SCRIPT_DIR}/run-mcp-server.sh"
    ;;
    
  integrated-webhook)
    # Alternative way to run integrated mode via webhook entry point
    echo "Starting integrated server via webhook entry point..."
    
    # Force integrated mode
    export SLACK_WEBHOOK_INTEGRATED=true
    
    # Execute the webhook server with integrated flag
    exec "${SCRIPT_DIR}/run-slack-webhook-server.sh"
    ;;
    
  *)
    # Invalid SERVICE_TYPE
    echo "ERROR: Invalid SERVICE_TYPE: ${SERVICE_TYPE}"
    echo "Valid values are: mcp, webhook, integrated, integrated-webhook"
    exit 1
    ;;
esac
