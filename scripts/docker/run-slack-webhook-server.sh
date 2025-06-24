#!/bin/bash
set -e

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

# LOG_LEVEL: Python logging level
if [ -n "${SLACK_WEBHOOK_LOG_LEVEL}" ]; then
  CMD_ARGS+=(--log-level "${SLACK_WEBHOOK_LOG_LEVEL}")
fi

# Print the command that will be executed
echo "Starting Slack webhook server with arguments: ${CMD_ARGS[@]}"
# Only print debug command information if log level is debug (case insensitive)
if [ -n "${SLACK_WEBHOOK_LOG_LEVEL}" ] && [ "$(echo ${SLACK_WEBHOOK_LOG_LEVEL} | tr '[:upper:]' '[:lower:]')" == "debug" ]; then
  echo "[DEBUG] Run the Slack webhook server with command: python -m slack_mcp.slack_server ${CMD_ARGS[@]}"
fi

# Execute the entry point with the collected arguments
exec uv run slack-events-server "${CMD_ARGS[@]}"
