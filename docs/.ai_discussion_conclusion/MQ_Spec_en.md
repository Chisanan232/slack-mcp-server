## English Version — Slack MCP Server × Message-Queue (MQ) Design Notes

### 1  Goals

* **Keep the core package dependency-free.**
  Developers can `pip install slack-mcp-server` and run a demo immediately.
* **Plug-and-play for any broker.**
  Installing `slack-mcp-<broker>` should be all that is required to switch to Redis, Kafka, RabbitMQ, NSQ, etc.
* **Clean separation of concerns.**
  Slack ingress → MQ adapter → consumer/AI-worker share only tiny, testable interfaces.

---

### 2  Queue Backend Abstraction

```python
from typing import Protocol, Dict, Any, AsyncIterator

class QueueBackend(Protocol):
    async def publish(self, key: str, payload: Dict[str, Any]) -> None: ...
    async def consume(
        self, *, group: str | None = None
    ) -> AsyncIterator[Dict[str, Any]]: ...
```

* Two async methods are enough: **`publish`** and **`consume`**.
* Based on PEP 544 `Protocol` → implementation can be *any* class that *structurally* satisfies the API (no inheritance required).

---

### 3  Plugin Mechanism (Python Entry Points)

| Element               | Purpose                                           | Example                                                                                                                                     |
|-----------------------|---------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| **Entry-point group** | Registry for all queue backends                   | `slack_mcp.queue_backends`                                                                                                                  |
| **Core package**      | Declares only the built-in fallback               | `toml [project.entry-points."slack_mcp.queue_backends"] memory = "slack_mcp.backends.memory:MemoryBackend" `                                |
| **3rd-party plugin**  | Adds a new backend simply by publishing a package | `toml [project] name = "slack-mcp-kafka" [project.entry-points."slack_mcp.queue_backends"] kafka = "slack_mcp_kafka.backend:KafkaBackend" ` |

After installation, `importlib.metadata.entry_points(group="slack_mcp.queue_backends")`
reveals every available backend class; no code changes in the core server are necessary.

---

### 4  Built-in `MemoryBackend`

```python
class MemoryBackend:
    _queue: "asyncio.Queue[tuple[str, dict]]" = asyncio.Queue()

    @classmethod
    def from_env(cls): return cls()

    async def publish(self, key, payload):  await self._queue.put((key, payload))
    async def consume(self, group=None):
        while True:
            _, payload = await self._queue.get()
            yield payload
```

* **Zero external dependencies** — uses only `asyncio`.
* **Dev-only** — single process, non-persistent.
  When selected, the server prints a yellow banner:
  “⚠️ Memory backend is for development/testing only.”

---

### 5  Backend Loader Logic

```python
def load_backend() -> QueueBackend:
    want = os.getenv("QUEUE_BACKEND")           # ① explicit selection
    eps   = entry_points(group="slack_mcp.queue_backends")

    if want:
        if want in eps:
            return eps[want].load().from_env()
        raise RuntimeError(
            f"Unknown backend '{want}'. Try: pip install slack-mcp-{want}"
        )

    # ② auto-pick first non-memory plugin, if present
    for name, ep in eps.items():
        if name != "memory":
            return ep.load().from_env()

    # ③ fallback
    warn("No external backend found — using MemoryBackend (dev only).")
    return MemoryBackend()
```

---

### 6  Consumer / Worker Abstraction

```python
class EventConsumer(Protocol):
    async def run(
        self, handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None: ...
    async def shutdown(self) -> None: ...
```

Typical built-ins (instantiated by a factory):

| Consumer             | Use-case                         | Notes                              |
|----------------------|----------------------------------|------------------------------------|
| `AsyncLoopConsumer`  | light single-instance demo       | loops over `backend.consume()`     |
| `CeleryTaskConsumer` | high-volume, retries, scheduling | uses Celery’s broker abstraction   |
| `AutoGenTopicBridge` | event-driven AutoGen deployments | maps broker → `AgentRuntime` queue |

Users may also subclass `AbstractWorker(process)` or write their own factory via a pluggy hook.

---

### 7  Configuration & DX

| Item                 | Method                                                              |
|----------------------|---------------------------------------------------------------------|
| Select backend       | `QUEUE_BACKEND=kafka` or CLI flag                                   |
| Per-backend settings | environment variables (e.g. `KAFKA_BOOTSTRAP`, `REDIS_URL`) or YAML |
| Discover plugins     | `slack-mcp backends list` prints installed vs. available plugins    |
| On error             | Loader raises with guidance: *“pip install slack-mcp-<backend>”*    |

---

### 8  Quick Start

```bash
# 1. basic demo (in-memory)
pip install slack-mcp-server
slack-mcp serve   # ← memory backend auto-selected

# 2. switch to Redis Streams
pip install slack-mcp-redis
export QUEUE_BACKEND=redis
export REDIS_URL=redis://localhost:6379/0
slack-mcp serve

# 3. later switch to Kafka
pip install slack-mcp-kafka
export QUEUE_BACKEND=kafka
export KAFKA_BOOTSTRAP=broker:9092
slack-mcp serve
```

---

### 9  Edge-case Guidelines

* **Idempotency** — include `event_id` or `(channel, ts, emoji)` keys; memory backend can’t deduplicate across restarts.
* **Observability** — wrap `publish/consume` in OpenTelemetry spans.
* **Back-pressure** — Redis consumer groups, Kafka commit offsets, or Celery concurrency settings.
* **Security** — secret material (e.g., Slack signing secret) stays outside workers.

---
