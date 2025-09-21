<h1 align="center">
  Slack MCP Server
</h1>

<p align="center">
  <a href="https://pypi.org/project/slack-mcp">
    <img src="https://img.shields.io/pypi/v/slack-mcp?color=%23099cec&amp;label=PyPI&amp;logo=pypi&amp;logoColor=white" alt="PyPI package version">
  </a>
  <a href="https://github.com/Chisanan232/slack-mcp-server/releases">
    <img src="https://img.shields.io/github/release/Chisanan232/slack-mcp-server.svg?label=Release&logo=github" alt="GitHub release version">
  </a>
  <a href="https://github.com/Chisanan232/slack-mcp-server/actions/workflows/ci.yaml">
    <img src="https://github.com/Chisanan232/slack-mcp-server/actions/workflows/ci.yaml/badge.svg" alt="CI/CD status">
  </a>
  <a href="https://codecov.io/gh/Chisanan232/slack-mcp-server" >
    <img src="https://codecov.io/gh/Chisanan232/slack-mcp-server/graph/badge.svg?token=VVZ0cGPVvp"/>
  </a>
  <a href="https://results.pre-commit.ci/latest/github/Chisanan232/slack-mcp-server/master">
    <img src="https://results.pre-commit.ci/badge/github/Chisanan232/slack-mcp-server/master.svg" alt="Pre-Commit building state">
  </a>
  <a href="https://sonarcloud.io/summary/new_code?id=Chisanan232_slack-mcp-server">
    <img src="https://sonarcloud.io/api/project_badges/measure?project=Chisanan232_slack-mcp-server&metric=alert_status" alt="Code quality level">
  </a>
  <a href="https://chisanan232.github.io/slack-mcp-server/">
    <img src="https://github.com/Chisanan232/slack-mcp-server/actions/workflows/documentation.yaml/badge.svg" alt="documentation CI status">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="Software license">
  </a>

</p>

<img align="center" src="https://raw.githubusercontent.com/Chisanan232/slack-mcp-server/refs/heads/master/docs/static/img/slack_mcp_server_logo.png" alt="slack-mcp-server logo" />

## Overview

🦾 **A strong MCP (Model Context Protocol) server for Slack integration**, providing standardized access to Slack's API features through both MCP tools and webhook processing.

**Key Features:**
- 🤖 **MCP Server**: Provides 6 essential Slack tools for AI assistants and clients
- 🪝 **Webhook Server**: Processes real-time Slack events with secure verification
- 🔗 **Integrated Mode**: Combined MCP + webhook server for complete Slack platform integration
- 🚀 **Multiple Transports**: Supports stdio, SSE, and HTTP streaming protocols
- 📦 **Easy Deployment**: Docker, Kubernetes, and cloud platform ready

[//]: # (- 🛡️ **Enterprise Security**: HMAC-SHA256 verification, token management, and comprehensive logging)

**Use Cases:**
- Building AI assistants with Slack integration
- Creating custom automation tools for Slack workflows
- Developing real-time Slack applications with event processing
- Integrating Slack with other tools and platforms

## Python versions support

[![Supported Versions](https://img.shields.io/pypi/pyversions/slack-mcp.svg?logo=python&logoColor=FBE072)](https://pypi.org/project/slack-mcp)

**slack-mcp-server** supports Python 3.12+ for optimal performance and modern language features.

## Quickly Start

### Installation

Choose your preferred installation method:

```bash
# Using pip (recommended)
pip install slack-mcp

# Using uv (fast)
uv add slack-mcp

# Using poetry (development)
poetry add slack-mcp
```

### Basic Usage

#### 1. Set Up Environment Variables

```bash
# Required: Slack bot token
export SLACK_BOT_TOKEN="xoxb-your-bot-token-here"

# Optional: For webhook server
export SLACK_SIGNING_SECRET="your-signing-secret"
```

#### 2. Start MCP Server (Standalone)

```bash
# Start with stdio transport (default)
slack-mcp-server

# Start with SSE transport for web clients
slack-mcp-server --transport sse --host 0.0.0.0 --port 3001
```

#### 3. Start Webhook Server (Standalone)

```bash
# Start standalone webhook server
slack-webhook-server --host 0.0.0.0 --port 3000
```

#### 4. Start Integrated Server (MCP + Webhook)

```bash
# Combined server with both MCP and webhook functionality
slack-mcp-server --integrated --transport sse --port 8000
```

### Available MCP Tools

| Tool                          | Description                  | Usage                       |
|-------------------------------|------------------------------|-----------------------------|
| `slack_post_message`          | Send messages to channels    | Post notifications, updates |
| `slack_read_channel_messages` | Read channel message history | Analyze conversations       |
| `slack_read_thread_messages`  | Read thread replies          | Follow discussions          |
| `slack_thread_reply`          | Reply to message threads     | Engage in conversations     |
| `slack_read_emojis`           | Get workspace emojis         | Access custom reactions     |
| `slack_add_reactions`         | Add emoji reactions          | React to messages           |

### Docker Quick Start

```bash
# Pull and run with environment variables
docker run -p 3000:3000 \
  -e SLACK_BOT_TOKEN="xoxb-your-token" \
  -e SLACK_SIGNING_SECRET="your-secret" \
  chisanan232/slack-mcp-server:latest
```

## Documentation

Comprehensive documentation is available at **[https://chisanan232.github.io/slack-mcp-server/](https://chisanan232.github.io/slack-mcp-server/)**

### Documentation Sections

- 📖 **[User Guide](https://chisanan232.github.io/slack-mcp-server/docs/next/introduction)** - Installation, configuration, and usage
- 🛠️ **[Developer Guide](https://chisanan232.github.io/slack-mcp-server/dev/next)** - Contributing, architecture, and development workflow
- 🏗️ **[API Reference](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/)** - Complete CLI and configuration reference
- 🚀 **[Deployment Guide](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/deployment-guide)** - Production deployment patterns

### Quick Links

- [Requirements](https://chisanan232.github.io/slack-mcp-server/docs/next/quick-start/requirements)
- [Installation Guide](https://chisanan232.github.io/slack-mcp-server/docs/next/quick-start/installation)
- [Server Modes](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/mcp-server/server-modes)
- [Environment Configuration](https://chisanan232.github.io/slack-mcp-server/docs/next/server-references/environment-configuration)
- [CI/CD Workflows](https://chisanan232.github.io/slack-mcp-server/dev/next/ci-cd/)

## Coding style and following rules

**slack-mcp-server** follows coding styles **black** and **PyLint** to control code quality, with additional tools for comprehensive code analysis.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Type Checking: mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

### Code Quality Tools

- **Black**: Consistent code formatting
- **PyLint**: Code analysis and style checking
- **MyPy**: Static type checking
- **isort**: Import sorting and organization
- **Pre-commit**: Automated code quality checks

### Development Workflow

```bash
# Install development dependencies
uv sync --dev

# Run code quality checks
uv run pre-commit run --all-files

# Run tests
uv run pytest
```

## Downloading state

Current download statistics for **slack-mcp** package:

[![Downloads](https://pepy.tech/badge/slack-mcp)](https://pepy.tech/project/slack-mcp)
[![Downloads](https://pepy.tech/badge/slack-mcp/month)](https://pepy.tech/project/slack-mcp)
[![Downloads](https://pepy.tech/badge/slack-mcp/week)](https://pepy.tech/project/slack-mcp)

### Container Downloads

[![Docker Pulls](https://img.shields.io/docker/pulls/chisanan232/slack-mcp-server)](https://hub.docker.com/r/chisanan232/slack-mcp-server)

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://chisanan232.github.io/slack-mcp-server/docs/next/contribute) for details.

### Quick Contribution Steps

1. **[Report Issues](https://chisanan232.github.io/slack-mcp-server/docs/next/contribute/report-bug)** - Found a bug? Let us know!
2. **[Request Features](https://chisanan232.github.io/slack-mcp-server/docs/next/contribute/request-changes)** - Have ideas? We'd love to hear them!
3. **[Join Discussions](https://chisanan232.github.io/slack-mcp-server/docs/next/contribute/discuss)** - Connect with the community
4. **[Development Setup](https://chisanan232.github.io/slack-mcp-server/dev/next/workflow)** - Start contributing code

## License

[MIT License](./LICENSE)
