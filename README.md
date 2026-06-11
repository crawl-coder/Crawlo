<p align="center">
  <img src="assets/logo.svg" alt="Crawlo Logo" width="150"/>
</p>

<h1 align="center">Crawlo</h1>

<p align="center">
  <strong>A Modern High-Performance Python Async Web Scraping Framework</strong>
</p>

<p align="center">
  <strong>Python 3.8+</strong> · <strong>Python 3.14 Compatible</strong>
</p>

<p align="center">
  <a href="README.zh.md">中文</a> ·
  <a href="README.md">English</a>
</p>

<p align="center">
  <a href="#quick-start-en">Quick Start</a> ·
  <a href="#features-en">Key Features</a> ·
  <a href="#docs-en">Docs</a> ·
  <a href="#examples-en">Examples</a>
</p>

---

## <a id="quick-start-en"></a>✨ Quick Start (3 Steps)

### 1. Install
```bash
pip install crawlo
```

### 2. Create a Spider
```bash
crawlo startproject myproject
cd myproject
crawlo genspider example example.com
```

### 3. Run
```bash
crawlo run example
```

👉 **[5-Minute Quickstart Tutorial →](docs/getting-started/5min-quickstart.md)**

---

## <a id="features-en"></a>🚀 Key Features

### ⚡ High-Performance Async Architecture
- Built on asyncio + aiohttp/httpx/curl-cffi multi-protocol downloaders
- Smart concurrency control, connection pool reuse, auto throughput optimization
- HTTP/2 support, TLS fingerprint emulation (bypass JA3 detection)

### 🛡️ Robust Anti-Bot Capabilities
- **HybridDownloader**: 6-level detection priority, auto-switch protocol/browser engine
- **Cloudflare Auto-Bypass**: Detects challenge pages and auto-switches to stealth browser
- **5 Browser Downloaders**: Playwright / Camoufox / CloakBrowser / DrissionPage / Chrome
- **BROWSER_* Unified Config Layer**: One set of params for all browser downloaders
- **Adaptive Selectors**: Auto-relocate elements when site structure changes (selector self-healing) — [Guide →](docs/guides/adaptive-selector.md)

### 🤖 AI Integration (MCP Server)
- Claude / Cursor directly invoke Crawlo scraping capabilities
- Three scraping modes: `basic` (1-3s) → `stealth` (3-10s) → `max-stealth` (10s+)
- Browser singleton pool: stealth/max-stealth modes reuse instances
- Structured error responses: distinguish `TIMEOUT` / `CONNECTION_ERROR` / `STEALTH_UNAVAILABLE`, with suggestions

### 📊 Four-Level Backpressure Defense
- **Engine** layer: request generation control (enqueue + TaskManager dual checks)
- **QueueManager** layer: strategy-driven (`QueueSizeStrategy` / `AdaptiveStrategy` / `CompositeStrategy`)
- **MemoryQueue** layer: Mixin delegation + fallback logic
- **Hard limit**: direct rejection when queue is full
- Smart enhancement: `IntelligentBackpressureCalculator` + `BackpressureMonitor` optional integration

### 📬 Multi-Channel Notification
- **5 Channels**: DingTalk / Feishu / WeCom / Email / SMS
- **30+ Preset Templates**: task start/stop, anomaly alerts, progress updates, DB monitoring
- **Async Delivery**: `async_send_*` functions, `run_in_executor` wrapper to avoid blocking event loop
- Message dedup + rate limiting to prevent notification storms

### 🔄 Three Deployment Modes

| Mode | Config | Coordination | Use Case |
|------|-------|-------------|----------|
| **Memory Mode** | `RUN_MODE='standalone'` `QUEUE_TYPE='memory'` | None (auto exit) | Dev/debug, quick validation |
| **Multi-Node** ⭐ | `RUN_MODE='auto'` `QUEUE_TYPE='redis'` | Competing consumption (BZPOPMIN) | Multi-machine, task loss acceptable |
| **Distributed** | `RUN_MODE='distributed'` `QUEUE_TYPE='redis_stream'` | ACK + heartbeat + failover | Production, high reliability |

> All three modes share the same priority model — switch without modifying spider code.
> [Learn More →](docs/concepts/architecture.md#2-部署模式-deployment-modes) · [Production Deployment →](docs/deployment.md)

---

## <a id="docs-en"></a>📚 Documentation

### 🎯 By Role

| You are? | Recommended Reading |
|----------|-------------------|
| **Beginner** | [5-Min Quickstart](docs/getting-started/5min-quickstart.md) → [Installation](docs/getting-started/installation.md) |
| **Developer** | [Configuration Guide](docs/guides/configuration/) → [Scheduling Guide](docs/guides/scheduling/) |
| **Ops** | [Run Mode Deep Dive](docs/guides/configuration/run-modes.md) → [Checkpoint System](docs/concepts/checkpoint-guide.md) → **[Production Deployment](docs/deployment.md)** |

### 📖 Full Docs Navigation

- 🚀 **[Getting Started](docs/getting-started/)** - Install, create your first spider
- 📚 **[Tutorials](docs/tutorials/)** - Complete guides from basics to production
- 🎯 **[Guides](docs/guides/)** - Scenario-based deep dives
  - [Configuration](docs/guides/configuration/), [Scheduling](docs/guides/scheduling/)
  - [Backpressure](docs/guides/scheduling/backpressure.md), [Run Modes](docs/guides/configuration/run-modes.md)
  - [Adaptive Selector](docs/guides/adaptive-selector.md) — selector self-healing after site redesign
- 📖 **[Concepts](docs/concepts/)** - Architecture, lifecycle, error handling
  - [Distributed Architecture](docs/distributed_architecture.md) — Redis Streams, failover, coordinated shutdown
- 🖥 **[Production Deployment](docs/deployment.md)** - Linux server setup, systemd, monitoring
- 🔧 **[API Reference](docs/reference/)** - Complete API docs
- 💡 **[Examples](docs/examples/)** - Real-world examples and best practices
- ❓ **[FAQ](docs/faq/)** - FAQ and troubleshooting

👉 **[Browse Complete Docs →](docs/index.md)**

---

## <a id="examples-en"></a>💡 Examples

Check out the [`examples/`](examples/) directory:
- **Basic** - Quick start
- **Advanced** - Complex scenarios
- **Production** - Ready for production

👉 **[View All Examples →](docs/examples/)**

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Licensed under BSD 3-Clause - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>⭐ If this project helps you, please give us a Star!</strong>
</p>
