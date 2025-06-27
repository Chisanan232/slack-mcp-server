#!/bin/bash
set -e

#
# Environment variables:
#
# MCP_TRANSPORT → --transport
# MCP_MOUNT_PATH → --mount-path
# MCP_LOG_LEVEL → --log-level
# MCP_HOST → --host
# MCP_PORT → --port
# SLACK_BOT_TOKEN → --slack-token
# MCP_ENV_FILE → --env-file
# MCP_NO_ENV_FILE → --no-env-file
# MCP_INTEGRATED → --integrated
#

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

# HOST: Host for FastAPI HTTP transports (used for sse or streamable-http)
if [ -n "${MCP_HOST}" ]; then
  CMD_ARGS+=(--host "${MCP_HOST}")
fi

# PORT: Port for FastAPI HTTP transports
if [ -n "${MCP_PORT}" ]; then
  CMD_ARGS+=(--port "${MCP_PORT}")
fi

# SLACK_BOT_TOKEN: Slack bot token
if [ -n "${SLACK_BOT_TOKEN}" ]; then
  CMD_ARGS+=(--slack-token "${SLACK_BOT_TOKEN}")
fi

# ENV_FILE: Path to .env file
if [ -n "${MCP_ENV_FILE}" ]; then
  CMD_ARGS+=(--env-file "${MCP_ENV_FILE}")
fi

# NO_ENV_FILE: Disable .env file loading
if [ -n "${MCP_NO_ENV_FILE}" ] && [ "${MCP_NO_ENV_FILE}" = "true" ]; then
  CMD_ARGS+=(--no-env-file)
fi

# INTEGRATED: Run in integrated mode with webhook server
if [ -n "${MCP_INTEGRATED}" ] && [ "${MCP_INTEGRATED}" = "true" ]; then
  CMD_ARGS+=(--integrated)
fi

# Print the command that will be executed
echo "Starting MCP server with arguments: ${CMD_ARGS[@]}"
# Only print debug command information if log level is debug (case insensitive)
if [ -n "${MCP_LOG_LEVEL}" ] && [ "$(echo ${MCP_LOG_LEVEL} | tr '[:upper:]' '[:lower:]')" == "debug" ]; then
  echo "[DEBUG] Run the MCP server with command: uv run slack-mcp-server ${CMD_ARGS[@]}"
fi

# Execute the entry point with the collected arguments
exec uv run slack-mcp-server "${CMD_ARGS[@]}"
