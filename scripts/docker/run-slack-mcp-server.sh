#!/bin/bash
set -e

#
# Environment variables:
#
# MCP_TRANSPORT → --transport
# MCP_MOUNT_PATH → --mount-path
# MCP_LOG_LEVEL → --log-level
# MCP_LOG_FILE → --log-file
# MCP_LOG_DIR → --log-dir
# MCP_LOG_FORMAT → --log-format
# MCP_HOST → --host
# MCP_PORT → --port
# SLACK_BOT_TOKEN → --slack-token
# MCP_ENV_FILE → --env-file
# MCP_NO_ENV_FILE → --no-env-file
# MCP_INTEGRATED → --integrated
# MCP_RETRY → --retry
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

# LOG_LEVEL: Python logging level (case-insensitive)
if [ -n "${MCP_LOG_LEVEL}" ]; then
  # Note: CLI now accepts case-insensitive values, but we keep lowercase for consistency
  LOG_LEVEL_LOWER=$(echo "${MCP_LOG_LEVEL}" | tr '[:upper:]' '[:lower:]')
  CMD_ARGS+=(--log-level "${LOG_LEVEL_LOWER}")
fi

# LOG_FILE: Path to log file (enables file logging with automatic rotation)
if [ -n "${MCP_LOG_FILE}" ]; then
  CMD_ARGS+=(--log-file "${MCP_LOG_FILE}")
fi

# LOG_DIR: Directory for log files
if [ -n "${MCP_LOG_DIR}" ]; then
  CMD_ARGS+=(--log-dir "${MCP_LOG_DIR}")
fi

# LOG_FORMAT: Custom log format string
if [ -n "${MCP_LOG_FORMAT}" ]; then
  CMD_ARGS+=(--log-format "${MCP_LOG_FORMAT}")
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

# RETRY: Number of retry attempts for network operations
if [ -n "${MCP_RETRY}" ]; then
  CMD_ARGS+=(--retry "${MCP_RETRY}")
fi

# Print the command that will be executed
echo "Starting MCP server with arguments: ${CMD_ARGS[@]}"
# Only print debug command information if log level is debug (case insensitive)
if [ -n "${MCP_LOG_LEVEL}" ] && [ "$(echo ${MCP_LOG_LEVEL} | tr '[:upper:]' '[:lower:]')" == "debug" ]; then
  echo "[DEBUG] Run the MCP server with command: uv run slack-mcp-server ${CMD_ARGS[@]}"
fi

# Execute the entry point with the collected arguments
exec uv run slack-mcp-server "${CMD_ARGS[@]}"
