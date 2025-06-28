## 中文版本 — Slack MCP Server 與消息佇列設計筆記

### 1  設計目標

* **核心套件零相依**：`pip install slack-mcp-server` 就能直接跑 demo。
* **Broker 隨插即用**：裝好 `slack-mcp-<broker>` 就可換成 Redis、Kafka、RabbitMQ …。
* **職責分離**：Slack 入口、MQ 介面、Consumer/AI Worker 只透過極薄介面耦合，易測試。

---

### 2  QueueBackend 抽象

```python
class QueueBackend(Protocol):
    async def publish(self, key: str, payload: Dict[str, Any]) -> None: ...
    async def consume(
        self, *, group: str | None = None
    ) -> AsyncIterator[Dict[str, Any]]: ...
```

* 僅需 `publish` 與 `consume` 兩個方法。
* 採 PEP 544 `Protocol`，鴨式符合即可，無需繼承。

---

### 3  Plugin 機制（Entry Points）

| 元件          | 用途                | 範例                                                         |
|-------------|-------------------|------------------------------------------------------------|
| **group 名** | 登記所有後端            | `slack_mcp.queue_backends`                                 |
| **核心**      | 只內建 MemoryBackend | `toml memory = "slack_mcp.backends.memory:MemoryBackend" ` |
| **第三方**     | 發佈時自宣告            | `toml kafka = "slack_mcp_kafka.backend:KafkaBackend" `     |

安裝插件後，核心透過 `importlib.metadata.entry_points()` 動態載入，無需改程式碼。

---

### 4  內建 MemoryBackend

* 全用標準庫 `asyncio`，**零外部依賴**。
* 單進程、非持久化，僅適合開發／測試。
* 啟動時印出警告：「⚠️ Memory backend 僅供 dev」。

---

### 5  後端載入流程

1. **使用者明確指定** `QUEUE_BACKEND=<name>` → 若已安裝就載入，否則拋錯並提示 `pip install slack-mcp-<name>`。
2. **未指定但檢測到插件** → 自動挑第一個非 `memory` 的後端。
3. **完全沒有插件** → 回退 `MemoryBackend`，並列警告。

---

### 6  Consumer / Worker 抽象

```python
class EventConsumer(Protocol):
    async def run(handler) -> None: ...
    async def shutdown() -> None: ...
```

內建三種範本：

| Consumer             | 場景        | 說明                             |
|----------------------|-----------|--------------------------------|
| `AsyncLoopConsumer`  | 輕量、單機     | 直接 `async for` 迴圈              |
| `CeleryTaskConsumer` | 高併發、需重試   | 借 Celery broker 抽象             |
| `AutoGenTopicBridge` | 用 AutoGen | broker ↔ AgentRuntime queue 映射 |

開發者可：

1. 繼承 `AbstractWorker(process)`；或
2. 用 pluggy hook 注入自訂 Factory。

---

### 7  設定方式 & DX

| 事項     | 做法                                         |
|--------|--------------------------------------------|
| 選擇後端   | `QUEUE_BACKEND=kafka` / CLI                |
| 後端連線資訊 | 環境變數（`KAFKA_BOOTSTRAP`、`REDIS_URL`…）或 YAML |
| 列出插件   | `slack-mcp backends list` 顯示已裝與可裝列表        |
| 錯誤提示   | 拋出「未知後端」時提示 `pip install slack-mcp-<name>` |

---

### 8  快速上手

```bash
# 1. 立即體驗（Memory）
pip install slack-mcp-server
slack-mcp serve

# 2. 改用 Redis Streams
pip install slack-mcp-redis
export QUEUE_BACKEND=redis
export REDIS_URL=redis://127.0.0.1:6379/0
slack-mcp serve

# 3. 再換 Kafka
pip install slack-mcp-kafka
export QUEUE_BACKEND=kafka
export KAFKA_BOOTSTRAP=broker:9092
slack-mcp serve
```

---

### 9  補充建議

* **冪等性**：event 帶 `event_id` 或 `(channel, ts, emoji)`，並在後端／Worker 去重。
* **觀測性**：`publish/consume` 包 OpenTelemetry span。
* **背壓 & 重試**：Redis consumer group、Kafka offset、Celery concurrency。
* **安全**：避免把 Slack secrets 洩漏到下游 Worker；入口驗簽後再送 MQ。
