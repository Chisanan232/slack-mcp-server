# Type Definitions for Slack MCP Server

This module provides comprehensive type definitions for the Slack MCP Server package, following PEP 561, PEP 484, PEP 585, and PEP 544 standards.

## Quick Start

```python
from slack_mcp import types

# Use type annotations in your code
def handle_event(event: types.SlackEventPayload) -> None:
    channel: types.SlackChannelID = event["channel"]
    print(f"Event in channel: {channel}")
```

## PEP Standards Compliance

- **PEP 561**: Package includes `py.typed` marker for type checker discovery
- **PEP 484**: Full type hints using `typing` module
- **PEP 585**: Modern type hints using built-in generics (Python 3.9+)
- **PEP 544**: Protocol-based structural subtyping

## Type Categories

### JSON Types
Basic JSON-compatible types for API payloads:
- `JSONPrimitive`: str, int, float, bool, None
- `JSONValue`: Any valid JSON value
- `JSONDict`: JSON object
- `JSONList`: JSON array

### Slack Types
Slack-specific identifiers and payloads:
- `SlackChannelID`: Channel identifier (e.g., "C1234567890")
- `SlackUserID`: User identifier (e.g., "U1234567890")
- `SlackTimestamp`: Message timestamp (e.g., "1234567890.123456")
- `SlackToken`: API token (e.g., "xoxb-...")
- `SlackEventPayload`: Event payload dictionary
- `SlackClient`: Slack SDK WebClient type
- `SlackAPIResponse`: Slack SDK response type

### Transport Types
MCP transport configuration:
- `TransportType`: Literal["stdio", "sse", "streamable-http"]
- `MCPTransport`: Alias for TransportType

### Handler Types
Event handler function signatures:
- `EventHandlerFunc`: Sync or async handler
- `AsyncEventHandlerFunc`: Async-only handler
- `SyncEventHandlerFunc`: Sync-only handler

### Queue Types
Message queue types:
- `QueueKey`: Routing key or topic
- `QueuePayload`: Message payload
- `QueueMessage`: Complete message with metadata

## Protocol Definitions

### EventHandlerProtocol
Structural type for event handlers:

```python
class MyHandler:
    async def handle_event(self, event: dict[str, Any]) -> None:
        pass

handler: types.EventHandlerProtocol = MyHandler()
```

### QueueBackendProtocol
Structural type for queue backends:

```python
class MyBackend:
    async def publish(self, key: str, payload: dict[str, Any]) -> None:
        pass

    async def consume(self, *, group: str | None = None):
        yield {}

    @classmethod
    def from_env(cls) -> "MyBackend":
        return cls()

backend: types.QueueBackendProtocol = MyBackend()
```

## Type Guards

Runtime validation functions:

```python
# Validate Slack identifiers
types.is_slack_channel_id("C1234567890")  # True
types.is_slack_user_id("U1234567890")     # True
types.is_slack_timestamp("1234567890.123456")  # True
```

## Usage Examples

### Event Handler with Type Safety

```python
from slack_mcp import types
from slack_mcp.webhook.event.handler import BaseSlackEventHandler

class MyHandler(BaseSlackEventHandler):
    async def on_message(self, event: types.SlackEventPayload) -> None:
        channel: types.SlackChannelID = event["channel"]
        user: types.SlackUserID = event.get("user", "")
        text: str = event.get("text", "")
        print(f"{user} in {channel}: {text}")
```

### Queue Backend Implementation

```python
from slack_mcp.types import QueueBackendProtocol, QueuePayload

class RedisBackend:
    async def publish(self, key: str, payload: QueuePayload) -> None:
        # Implementation here
        pass

    async def consume(self, *, group: str | None = None):
        # Implementation here
        yield {}

    @classmethod
    def from_env(cls) -> "RedisBackend":
        return cls()

# Type checker verifies protocol compliance
backend: QueueBackendProtocol = RedisBackend()
```

### Transport Configuration

```python
from slack_mcp.types import TransportType

def configure_server(transport: TransportType) -> dict:
    if transport == "sse":
        return {"host": "0.0.0.0", "port": 8000}
    elif transport == "streamable-http":
        return {"host": "0.0.0.0", "port": 8000}
    else:  # stdio
        return {"stdio": True}
```

## Running Type Checks

```bash
# Check specific files
uv run mypy slack_mcp/types.py

# Check entire package
uv run mypy slack_mcp/

# Check with strict mode
uv run mypy --strict slack_mcp/
```

## IDE Integration

Modern IDEs automatically recognize the type information:

- **VS Code**: Install Pylance extension
- **PyCharm**: Built-in type checking support
- **Vim/Neovim**: Use ALE or coc-pyright

## Package Distribution

The `py.typed` marker file ensures type information is distributed with the package:

```
slack_mcp/
├── __init__.py
├── py.typed          # PEP 561 marker
├── types.py          # Type definitions
└── ...
```

When users install the package, type checkers automatically discover the type information:

```bash
pip install slack-mcp
# Type information is automatically available
```

## Contributing

When adding new types:

1. Add type definitions to `types.py`
2. Export in `__all__`
3. Add docstrings with examples
4. Run MyPy to verify: `uv run mypy slack_mcp/`
5. Update documentation

## References

- [PEP 561 – Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [PEP 585 – Type Hinting Generics](https://peps.python.org/pep-0585/)
- [PEP 544 – Protocols](https://peps.python.org/pep-0544/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
