#!/bin/bash
set -e

#
# Environment variables:
#
# SLACK_WEBHOOK_HOST → --host
# SLACK_WEBHOOK_PORT → --port
# SLACK_WEBHOOK_LOG_LEVEL → --log-level
# SLACK_WEBHOOK_LOG_FILE → --log-file
# SLACK_WEBHOOK_LOG_DIR → --log-dir
# SLACK_WEBHOOK_LOG_FORMAT → --log-format
# SLACK_BOT_TOKEN → --slack-token
# SLACK_WEBHOOK_ENV_FILE → --env-file
# SLACK_WEBHOOK_NO_ENV_FILE → --no-env-file
# SLACK_WEBHOOK_INTEGRATED → --integrated
# SLACK_WEBHOOK_MCP_TRANSPORT → --mcp-transport
# SLACK_WEBHOOK_MCP_MOUNT_PATH → --mcp-mount-path
# SLACK_WEBHOOK_RETRY → --retry
#

# Initialize command line arguments array
CMD_ARGS=()

# Map environment variables to command line options

# HOST: Host to listen on
if [ -n "${SLACK_WEBHOOK_HOST}" ]; then
  CMD_ARGS+=(--host "${SLACK_WEBHOOK_HOST}")
fi

# PORT: Port to listen on
if [ -n "${SLACK_WEBHOOK_PORT}" ]; then
  CMD_ARGS+=(--port "${SLACK_WEBHOOK_PORT}")
fi

# LOG_LEVEL: Python logging level (case-insensitive)
if [ -n "${SLACK_WEBHOOK_LOG_LEVEL}" ]; then
  # Note: CLI now accepts case-insensitive values
  CMD_ARGS+=(--log-level "${SLACK_WEBHOOK_LOG_LEVEL}")
fi

# LOG_FILE: Path to log file (enables file logging with automatic rotation)
if [ -n "${SLACK_WEBHOOK_LOG_FILE}" ]; then
  CMD_ARGS+=(--log-file "${SLACK_WEBHOOK_LOG_FILE}")
fi

# LOG_DIR: Directory for log files
if [ -n "${SLACK_WEBHOOK_LOG_DIR}" ]; then
  CMD_ARGS+=(--log-dir "${SLACK_WEBHOOK_LOG_DIR}")
fi

# LOG_FORMAT: Custom log format string
if [ -n "${SLACK_WEBHOOK_LOG_FORMAT}" ]; then
  CMD_ARGS+=(--log-format "${SLACK_WEBHOOK_LOG_FORMAT}")
fi

# SLACK_BOT_TOKEN: Slack bot token
if [ -n "${SLACK_BOT_TOKEN}" ]; then
  CMD_ARGS+=(--slack-token "${SLACK_BOT_TOKEN}")
fi

# ENV_FILE: Path to .env file
if [ -n "${SLACK_WEBHOOK_ENV_FILE}" ]; then
  CMD_ARGS+=(--env-file "${SLACK_WEBHOOK_ENV_FILE}")
fi

# NO_ENV_FILE: Disable .env file loading
if [ -n "${SLACK_WEBHOOK_NO_ENV_FILE}" ] && [ "${SLACK_WEBHOOK_NO_ENV_FILE}" = "true" ]; then
  CMD_ARGS+=(--no-env-file)
fi

# INTEGRATED: Run in integrated mode with MCP server
if [ -n "${SLACK_WEBHOOK_INTEGRATED}" ] && [ "${SLACK_WEBHOOK_INTEGRATED}" = "true" ]; then
  CMD_ARGS+=(--integrated)

  # MCP_TRANSPORT: Transport type for MCP in integrated mode
  if [ -n "${SLACK_WEBHOOK_MCP_TRANSPORT}" ]; then
    CMD_ARGS+=(--mcp-transport "${SLACK_WEBHOOK_MCP_TRANSPORT}")
  fi

  # MCP_MOUNT_PATH: Mount path for MCP in integrated mode (when using sse transport)
  if [ -n "${SLACK_WEBHOOK_MCP_MOUNT_PATH}" ]; then
    CMD_ARGS+=(--mcp-mount-path "${SLACK_WEBHOOK_MCP_MOUNT_PATH}")
  fi
fi

# RETRY: Number of retry attempts for network operations
if [ -n "${SLACK_WEBHOOK_RETRY}" ]; then
  CMD_ARGS+=(--retry "${SLACK_WEBHOOK_RETRY}")
fi

# Print the command that will be executed
echo "Starting Slack webhook server with arguments: ${CMD_ARGS[@]}"
# Only print debug command information if log level is debug (case insensitive)
if [ -n "${SLACK_WEBHOOK_LOG_LEVEL}" ] && [ "$(echo ${SLACK_WEBHOOK_LOG_LEVEL} | tr '[:upper:]' '[:lower:]')" == "debug" ]; then
  echo "[DEBUG] Run the Slack webhook server with command: uv run slack-events-server ${CMD_ARGS[@]}"
fi

# Execute the entry point with the collected arguments
exec uv run slack-events-server "${CMD_ARGS[@]}"
