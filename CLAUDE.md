# CLAUDE.md

This file provides guidance for AI assistants working in this repository.

## Project Overview

`slack-mcp` is a Python MCP (Model Context Protocol) server for Slack integration. It enables AI clients to interact with Slack via 6 tools: post messages, read channel/thread messages, reply to threads, read emojis, and add reactions.

- **Package**: `slack-mcp` v0.2.0 on PyPI
- **Python**: 3.12+ (supports 3.12, 3.13; not 3.14 due to PyO3 limitation)
- **Package manager**: `uv`
- **Build backend**: Hatchling

## Repository Structure

```
slack_mcp/          # Main source package
├── settings.py     # Pydantic settings (all config lives here)
├── types.py        # PEP 695 type aliases
├── events.py       # Slack event type definitions
├── client/         # Slack SDK client management
├── logging/        # Logging configuration
├── mcp/            # MCP server (entry, app factory, server/tools, CLI, models)
├── webhook/        # Webhook server (entry, FastAPI app, event consumer/handlers)
└── integrate/      # Integrated MCP + Webhook server

test/               # Test suites
├── unit_test/      # Fast, heavily mocked
├── integration_test/
├── e2e_test/       # Requires real Slack API credentials
├── contract_test/
└── ci_script_test/

docs/               # Docusaurus documentation site (pnpm)
scripts/            # CI and Docker helper scripts
examples/           # Usage examples
```

## Development Commands

```bash
# Install all dependencies (dev + pre-commit-ci groups by default)
uv sync

# Run pre-commit hooks on all files
uv run pre-commit run --all-files

# Run all tests
uv run pytest

# Run specific test type
uv run pytest test/unit_test/
uv run pytest test/integration_test/
uv run pytest test/e2e_test/      # Requires SLACK_BOT_TOKEN, E2E_TEST_API_TOKEN

# Build the package
uv build

# Build Docker image
docker build -t slack-mcp-server .
```

## Running the Servers

```bash
# MCP server (stdio is default transport)
slack-mcp-server

# MCP server via SSE on port 8000
slack-mcp-server --transport sse --host 0.0.0.0 --port 8000

# MCP server via streamable-http
slack-mcp-server --transport streamable-http --host 0.0.0.0 --port 8000

# Webhook server (processes incoming Slack events)
slack-webhook-server --host 0.0.0.0 --port 3000

# Integrated mode (MCP + Webhook on one port)
slack-mcp-server --integrated --transport sse --port 8000
```

## Environment Variables

Required:
- `SLACK_BOT_TOKEN` — Bot token (`xoxb-...`)
- `SLACK_SIGNING_SECRET` — Required for webhook mode

Optional:
- `SLACK_BOT_ID`, `SLACK_USER_TOKEN`
- `QUEUE_BACKEND` — `memory` (default) | `redis` | `kafka`
- `REDIS_URL`, `KAFKA_BOOTSTRAP`, `SLACK_EVENTS_TOPIC`
- `LOG_LEVEL` — `INFO` (default), `DEBUG`, `WARNING`, `ERROR`, `CRITICAL`
- `LOG_FILE`, `LOG_DIR` — Log output configuration
- `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`

**Configuration priority**: `.env` file > CLI arguments > environment variables.

See `.env.example` for a full template.

## Code Conventions

### Formatting and Linting
- **Black** with `--line-length=120` (enforced via pre-commit)
- **isort** with `--profile=black`
- **autoflake** removes unused imports automatically
- **pylint** via `.pylintrc`
- **mypy** type checking (see `mypy.ini`)

### Type Annotations
- Full type hints are required throughout `slack_mcp/`
- Use PEP 695 `type` statement for aliases (Python 3.12+ only)
- Pydantic models for all data validation and settings
- mypy excludes `test/unit_test/` (heavy mock usage makes strict checking impractical)

### Key Patterns
- **Settings**: All configuration goes through `slack_mcp/settings.py` via `get_settings()` singleton (Pydantic BaseSettings)
- **Factory pattern**: `MCPServerFactory` (in `mcp/app.py`) — assert-guarded singleton, never instantiate directly
- **Entry points**: `mcp/entry.py` and `webhook/entry.py` contain the `main()` CLI functions
- **Event handlers**: Use the decorator pattern in `webhook/event/handler/decorator.py`
- **Enums**: `QueueBackend`, `LogLevel` — always add new options as enum members

### Testing Patterns
- pytest with `pytest-asyncio` for async tests
- `conftest.py` manages event loop lifecycle (platform-specific for macOS CI)
- `pytest-mock` for mocking; avoid mocking the database/queue at integration level
- `pytest-rerunfailures` with `--reruns 1` to handle flaky Slack API calls
- E2E tests require `E2E_TEST_API_TOKEN` and real Slack workspace

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yaml` | Push to master, PRs | Runs all tests via reusable workflow |
| `rw_build_and_test.yaml` | Called by ci.yaml | Tests on ubuntu-latest, ubuntu-22.04, macos-latest, macos-14 |
| `type-check.yml` | Push/PR | MyPy static type checking |
| `docker-ci.yml` | Push/PR | Builds and tests Docker image |
| `documentation.yaml` | Push to master | Builds and deploys Docusaurus site |
| `release.yml` | Manual/tag | Publishes to PyPI and Docker Hub |

## Optional Dependencies

The package uses extras to keep base install minimal:

```bash
pip install slack-mcp[mcp]      # MCP server only
pip install slack-mcp[webhook]  # Webhook server only
pip install slack-mcp[all]      # Everything
```

Base install (`pip install slack-mcp`) only includes `abstract-backend` — no MCP or HTTP server functionality.

## MCP Tools Reference

Defined in `slack_mcp/mcp/server.py`:

| Tool | Description |
|---|---|
| `slack_post_message` | Post a message to a channel |
| `slack_read_channel_messages` | Read message history from a channel |
| `slack_read_thread_messages` | Read replies in a thread |
| `slack_thread_reply` | Reply to a thread |
| `slack_read_emojis` | List workspace custom emojis |
| `slack_add_reactions` | Add emoji reactions to a message |

Input/output models are in `slack_mcp/mcp/model/input.py` and `output.py`.

## Docker

The `Dockerfile` uses a multi-stage build on `python:3.13-slim`. The container:
- Runs as non-root user `appuser`
- Exposes port via `$SERVER_PORT` (default 8000)
- Entry point: `scripts/docker/run-server.sh`

```bash
docker run -p 8000:8000 \
  -e SLACK_BOT_TOKEN=xoxb-... \
  -e SLACK_SIGNING_SECRET=... \
  chisanan232/slack-mcp-server
```
