# 🦾 Slack MCP Server

[![Docker Pulls](https://img.shields.io/docker/pulls/chisanan232/slack-mcp-server)](https://hub.docker.com/r/chisanan232/slack-mcp-server)
[![Docker Image Size](https://img.shields.io/docker/image-size/chisanan232/slack-mcp-server/latest)](https://hub.docker.com/r/chisanan232/slack-mcp-server)
[![Docker Stars](https://img.shields.io/docker/stars/chisanan232/slack-mcp-server)](https://hub.docker.com/r/chisanan232/slack-mcp-server)
[![Docker Automated build](https://img.shields.io/docker/automated/chisanan232/slack-mcp-server)](https://hub.docker.com/r/chisanan232/slack-mcp-server)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)

## 🔍 Overview

🦾 **A powerful MCP (Model Context Protocol) server for Slack integration**, providing standardized access to Slack's API features through both MCP tools and webhook processing.

**Key Features:**
- 🤖 **MCP Server**: Provides 6 essential Slack tools for AI assistants and clients
- 🪝 **Webhook Server**: Processes real-time Slack events with secure verification
- 🔗 **Integrated Mode**: Combined MCP + webhook server for complete Slack platform integration
- 🚀 **Multiple Transports**: Supports stdio, SSE, and HTTP streaming protocols
- 📦 **Easy Deployment**: Docker, Kubernetes, and cloud platform ready

## 🐳 Docker Usage

### 🚀 Quick Start

Pull the Docker image:

```bash
docker pull chisanan232/slack-mcp-server:latest
```

Run the container with minimal configuration (defaults to MCP server):

```bash
docker run -d -p 8000:8000 -e SLACK_BOT_TOKEN=xoxb-your-bot-token-here chisanan232/slack-mcp-server
```

Access the health check endpoint at `http://localhost:8000/health` (when using HTTP transports)

### 🔧 Configuration Options

The Docker container supports **2 entry points** controlled by the `SERVICE_TYPE` environment variable:

#### 🎯 Main Control Variable

| Environment Variable | Description                                                                          | Default |
|----------------------|--------------------------------------------------------------------------------------|---------|
| `SERVICE_TYPE`       | Determines which server to run: `mcp`, `webhook`, `integrated`, `integrated-webhook` | `mcp`   |

#### 🤖 MCP Server Variables (when `SERVICE_TYPE=mcp` or `integrated`)

**Core Configuration:**

| Environment Variable | Description                                                                       | Default |
|----------------------|-----------------------------------------------------------------------------------|---------|
| `SLACK_BOT_TOKEN`    | Your Slack bot token (required) - format: xoxb-...                                | -       |
| `MCP_TRANSPORT`      | Transport mode: `stdio`, `sse`, `streamable-http`                                 | `stdio` |
| `MCP_HOST`           | Host for HTTP transports                                                          | -       |
| `MCP_PORT`           | Port for HTTP transports                                                          | -       |
| `MCP_MOUNT_PATH`     | Mount path for HTTP transports                                                    | -       |
| `MCP_LOG_LEVEL`      | Logging level (case-insensitive): `debug`, `info`, `warning`, `error`, `critical` | `info`  |
| `MCP_LOG_FILE`       | Path to log file (enables file logging with auto-rotation)                        | -       |
| `MCP_LOG_DIR`        | Directory for log files                                                           | `logs`  |
| `MCP_LOG_FORMAT`     | Custom log format string                                                          | -       |
| `MCP_ENV_FILE`       | Path to custom .env file                                                          | -       |
| `MCP_NO_ENV_FILE`    | Disable .env file loading (set to `true`)                                         | -       |
| `MCP_INTEGRATED`     | Enable integrated mode (set to `true`)                                            | -       |
| `MCP_RETRY`          | Number of retry attempts for network operations                                   | -       |

#### 🪝 Webhook Server Variables (when `SERVICE_TYPE=webhook` or `integrated-webhook`)

**Core Configuration:**

| Environment Variable           | Description                                                                       | Default |
|--------------------------------|-----------------------------------------------------------------------------------|---------|
| `SLACK_BOT_TOKEN`              | Your Slack bot token (required) - format: xoxb-...                                | -       |
| `SLACK_WEBHOOK_HOST`           | Host to listen on                                                                 | -       |
| `SLACK_WEBHOOK_PORT`           | Port to listen on                                                                 | -       |
| `SLACK_WEBHOOK_LOG_LEVEL`      | Logging level (case-insensitive): `debug`, `info`, `warning`, `error`, `critical` | `info`  |
| `SLACK_WEBHOOK_LOG_FILE`       | Path to log file (enables file logging with auto-rotation)                        | -       |
| `SLACK_WEBHOOK_LOG_DIR`        | Directory for log files                                                           | `logs`  |
| `SLACK_WEBHOOK_LOG_FORMAT`     | Custom log format string                                                          | -       |
| `SLACK_WEBHOOK_ENV_FILE`       | Path to custom .env file                                                          | -       |
| `SLACK_WEBHOOK_NO_ENV_FILE`    | Disable .env file loading (set to `true`)                                         | -       |
| `SLACK_WEBHOOK_INTEGRATED`     | Enable integrated mode (set to `true`)                                            | -       |
| `SLACK_WEBHOOK_MCP_TRANSPORT`  | MCP transport for integrated mode                                                 | -       |
| `SLACK_WEBHOOK_MCP_MOUNT_PATH` | MCP mount path for integrated mode                                                | -       |
| `SLACK_WEBHOOK_RETRY`          | Number of retry attempts for network operations                                   | -       |

#### 📦 Additional Variables (via .env file)

These are loaded from `.env` file and used by both servers:

| Environment Variable    | Description                                        |
|-------------------------|----------------------------------------------------|
| `SLACK_BOT_ID`          | Your Slack bot ID (optional)                       |
| `SLACK_USER_TOKEN`      | Your Slack user token (optional)                   |
| `SLACK_SIGNING_SECRET`  | Slack signing secret for webhook verification      |
| `SLACK_TEST_CHANNEL`    | Test channel name (optional)                       |
| `SLACK_TEST_CHANNEL_ID` | Test channel ID (optional)                         |
| `QUEUE_BACKEND`         | Message queue backend: `memory`, `redis`, `kafka`  |
| `REDIS_URL`             | Redis connection URL (when using redis backend)    |
| `KAFKA_BOOTSTRAP`       | Kafka bootstrap servers (when using kafka backend) |

### 📝 Using Environment Files

You can use a `.env` file for configuration instead of passing environment variables directly:

1. Create a `.env` file with your configuration:

```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_SIGNING_SECRET=your-slack-signing-secret
QUEUE_BACKEND=memory
```

2. Mount the file when running the container:

```bash
docker run -d -p 8000:8000 -v $(pwd)/.env:/app/.env chisanan232/slack-mcp-server
```

### 🔄 Server Mode Examples

#### 🤖 MCP Server (Default - `SERVICE_TYPE=mcp`)

**MCP Server with stdio transport (default):**
```bash
docker run -d \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  chisanan232/slack-mcp-server
```

**MCP Server with SSE transport:**
```bash
docker run -d -p 8000:8000 \
  -e SERVICE_TYPE=mcp \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  chisanan232/slack-mcp-server
```

**MCP Server with file logging:**
```bash
docker run -d -p 8000:8000 \
  -e SERVICE_TYPE=mcp \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MCP_LOG_LEVEL=debug \
  -e MCP_LOG_FILE=/app/logs/mcp.log \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -v $(pwd)/logs:/app/logs \
  chisanan232/slack-mcp-server
```

#### 🪝 Webhook Server (`SERVICE_TYPE=webhook`)

**Standalone webhook server:**
```bash
docker run -d -p 3000:3000 \
  -e SERVICE_TYPE=webhook \
  -e SLACK_WEBHOOK_HOST=0.0.0.0 \
  -e SLACK_WEBHOOK_PORT=3000 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  chisanan232/slack-mcp-server
```

**Webhook server with file logging:**
```bash
docker run -d -p 3000:3000 \
  -e SERVICE_TYPE=webhook \
  -e SLACK_WEBHOOK_HOST=0.0.0.0 \
  -e SLACK_WEBHOOK_PORT=3000 \
  -e SLACK_WEBHOOK_LOG_LEVEL=debug \
  -e SLACK_WEBHOOK_LOG_FILE=/app/logs/webhook.log \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -v $(pwd)/logs:/app/logs \
  chisanan232/slack-mcp-server
```

#### 🔗 Integrated Server (`SERVICE_TYPE=integrated`)

**Integrated via MCP entry point:**
```bash
docker run -d -p 8000:8000 \
  -e SERVICE_TYPE=integrated \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  chisanan232/slack-mcp-server
```

**Integrated via webhook entry point:**
```bash
docker run -d -p 3000:3000 \
  -e SERVICE_TYPE=integrated-webhook \
  -e SLACK_WEBHOOK_HOST=0.0.0.0 \
  -e SLACK_WEBHOOK_PORT=3000 \
  -e SLACK_WEBHOOK_MCP_TRANSPORT=sse \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  chisanan232/slack-mcp-server
```

### 📋 Logging Configuration

The server provides comprehensive logging features:

**Features:**
- ✅ **Case-Insensitive Log Levels**: Use `debug`, `DEBUG`, or `Debug` - all work!
- ✅ **File Logging**: Automatic log rotation at 10MB with 5 backup files
- ✅ **Custom Formats**: Customize log output format for your needs
- ✅ **Directory Management**: Organize logs in custom directories

**Example with all logging options:**

```bash
# MCP Server with complete logging setup
docker run -d -p 8000:8000 \
  -e SERVICE_TYPE=mcp \
  -e MCP_TRANSPORT=sse \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MCP_LOG_LEVEL=debug \
  -e MCP_LOG_FILE=/app/logs/mcp-server.log \
  -e MCP_LOG_DIR=/app/logs \
  -e MCP_LOG_FORMAT="%(asctime)s [%(levelname)s] %(name)s: %(message)s" \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -v $(pwd)/logs:/app/logs \
  chisanan232/slack-mcp-server
```

**Log Rotation:**
- Automatically rotates when log file reaches 10MB
- Keeps 5 backup files (e.g., `mcp.log.1`, `mcp.log.2`, ...)
- Oldest backup is deleted on next rotation

**Log Levels:**
- `DEBUG`: Detailed diagnostic information (verbose)
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical error messages for fatal issues

### 🛡️ Securing Your Tokens

For production environments, consider using Docker secrets or a secure environment management solution rather than passing tokens directly via command line.

### 🔍 Health Check

The container includes a health check endpoint at `/health` that can be used to verify the server is running correctly.

## 📚 Python Usage

### Installation

Choose your preferred installation method:

#### Using pip
```bash
# Minimal base (protocol only)
pip install slack-mcp

# MCP server feature set
pip install "slack-mcp[mcp]"

# Webhook server feature set
pip install "slack-mcp[webhook]"

# Everything
pip install "slack-mcp[all]"
```

#### Using uv (recommended)
```bash
# Minimal base
uv add slack-mcp

# MCP server / Webhook / All
uv add "slack-mcp[mcp]"
uv add "slack-mcp[webhook]"
uv add "slack-mcp[all]"
```

#### Using poetry
```bash
# Minimal base
poetry add slack-mcp

# MCP server / Webhook / All
poetry add slack-mcp -E mcp
poetry add slack-mcp -E webhook
poetry add slack-mcp -E all
```

> Note: Installation extras
> - [mcp]: Installs the MCP server feature set (SSE/Streamable transports; not the integrated webhook mode)
> - [webhook]: Installs FastAPI/Uvicorn and related parts for Slack webhook handling (not the integrated mode)
> - [all]: Installs everything in this project
> - Base (no extra): Minimal install with only the base protocol rules of this project

### Configuration

Configure your Slack API tokens using environment variables or `.env` file:

1. **Environment variables**: Set the required Slack tokens
```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token-here"
export SLACK_SIGNING_SECRET="your-signing-secret"  # Optional for webhooks
```

2. **Environment file**: Create a `.env` file with your configuration:
```
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_SIGNING_SECRET=your-slack-signing-secret
QUEUE_BACKEND=memory
```

See the `.env.example` file for a complete example configuration.

### Starting the servers

**MCP Server (Standalone):**
```bash
# Start with stdio transport (default)
slack-mcp-server

# Start with SSE transport for web clients
slack-mcp-server --transport sse --host 0.0.0.0 --port 3001
```

**Webhook Server (Standalone):**
```bash
slack-webhook-server --host 0.0.0.0 --port 3000
```

**Integrated Server (MCP + Webhook):**
```bash
slack-mcp-server --integrated --transport sse --port 8000
```

### Available MCP Tools

The Slack MCP Server provides 6 essential tools for AI assistants:

| Tool                          | Description                  | Usage                       |
|-------------------------------|------------------------------|-----------------------------|
| `slack_post_message`          | Send messages to channels    | Post notifications, updates |
| `slack_read_channel_messages` | Read channel message history | Analyze conversations       |
| `slack_read_thread_messages`  | Read thread replies          | Follow discussions          |
| `slack_thread_reply`          | Reply to message threads     | Engage in conversations     |
| `slack_read_emojis`           | Get workspace emojis         | Access custom reactions     |
| `slack_add_reactions`         | Add emoji reactions          | React to messages           |

## 📋 Requirements

- Python 3.12+
- Docker (for container deployment)
- Valid Slack Bot Token (xoxb-...)

## 📖 Documentation

Comprehensive documentation is available at **[https://chisanan232.github.io/slack-mcp-server/](https://chisanan232.github.io/slack-mcp-server/)**

### Quick Links

- [Installation Guide](https://chisanan232.github.io/slack-mcp-server/docs/next/quick-start/installation)
- [Logging Configuration](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/logging-configuration)
- [Server Modes](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/mcp-server/server-modes)
- [Environment Configuration](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/environment-configuration)
- [Deployment Guide](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/deployment-guide)

## 🌟 Features

- 🤖 **6 Essential MCP Tools**: Complete Slack API integration for AI assistants
- 🪝 **Webhook Processing**: Real-time event handling with secure HMAC verification
- 🔗 **Integrated Mode**: Combined MCP + webhook server for complete functionality
- 🚀 **Multiple Transports**: stdio, SSE, and HTTP streaming protocols
- 📦 **Message Queue Backends**: Memory, Redis, and Kafka support
- 🔒 **Enterprise Security**: Token management and comprehensive logging
- 🐳 **Production Ready**: Docker, Kubernetes, and cloud platform deployment

## 🔨 Development

Want to contribute? Great! Check out our [GitHub repository](https://github.com/Chisanan232/slack-mcp-server) for contribution guidelines.

### Development Workflow

```bash
# Install development dependencies
uv sync --dev

# Run code quality checks
uv run pre-commit run --all-files

# Run tests
uv run pytest
```

## 🏗️ Use Cases

- Building AI assistants with Slack integration
- Creating custom automation tools for Slack workflows
- Developing real-time Slack applications with event processing
- Integrating Slack with other tools and platforms

## 📜 License

[MIT License](./LICENSE)
