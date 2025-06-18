#!/bin/bash
set -e

# Initialize command line arguments array
CMD_ARGS=()

# Map environment variables to command line options

# TRANSPORT: Transport mode for FastMCP server (stdio, sse, streamable-http)
if [ -n "${MCP_TRANSPORT}" ]; then
  CMD_ARGS+=(--transport "${MCP_TRANSPORT}")
fi

# MOUNT_PATH: Mount path for HTTP transports
if [ -n "${MCP_MOUNT_PATH}" ]; then
  CMD_ARGS+=(--mount-path "${MCP_MOUNT_PATH}")
fi

# LOG_LEVEL: Python logging level
if [ -n "${MCP_LOG_LEVEL}" ]; then
  CMD_ARGS+=(--log-level "${MCP_LOG_LEVEL}")
fi

# Print the command that will be executed
echo "Starting MCP server with arguments: ${CMD_ARGS[@]}"
# Only print debug command information if log level is debug (case insensitive)
if [ -n "${MCP_LOG_LEVEL}" ] && [ "$(echo ${MCP_LOG_LEVEL} | tr '[:upper:]' '[:lower:]')" == "debug" ]; then
  echo "[DEBUG] Run the MCP server with command: uv run slack-mcp-server ${CMD_ARGS[@]}"
fi

# Execute the entry point with the collected arguments
exec uv run slack-mcp-server "${CMD_ARGS[@]}"
