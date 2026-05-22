<p align="center">
  <img src="assets/logo.svg" alt="Crawlo Logo" width="150"/>
</p>

<h1 align="center">Crawlo</h1>

<p align="center">
  <strong>基于 asyncio 的现代化高性能 Python 异步爬虫框架</strong>
</p>

<p align="center">
  <strong>Python 3.11+</strong> · <strong>已适配 Python 3.14</strong>
</p>

<p align="center">
  <a href="javascript:void(0)" onclick="document.getElementById('cn-content').style.display='';document.getElementById('en-content').style.display='none';">中文</a> |
  <a href="javascript:void(0)" onclick="document.getElementById('cn-content').style.display='none';document.getElementById('en-content').style.display='';">English</a>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> •
  <a href="#核心特性">核心特性</a> •
  <a href="#文档">文档</a> •
  <a href="#示例">示例</a>
</p>

---

<div id="cn-content">

## ✨ 快速开始（3步上手）

### 1. 安装
```bash
pip install crawlo
```

### 2. 创建爬虫
```bash
crawlo startproject myproject
cd myproject
crawlo genspider example example.com
```

### 3. 运行
```bash
crawlo run example
```

👉 **[查看5分钟快速上手教程 →](docs/getting-started/5min-quickstart.md)**

---

## 🚀 核心特性

### ⚡ 高性能异步架构
- 基于 asyncio + aiohttp/httpx/curl-cffi 多种协议下载器
- 智能并发控制，连接池复用，自动优化吞吐量
- 支持 HTTP/2、TLS 指纹模拟（绕过 JA3 检测）

### 🛡️ 强大的反反爬能力
- **HybridDownloader**：6 级检测优先级，自动切换协议/浏览器引擎
- **Cloudflare 自动绕过**：检测挑战页面后自动切换隐身浏览器
- **5 种浏览器下载器**：Playwright / Camoufox / CloakBrowser / DrissionPage / Chrome
- **BROWSER_* 统一配置层**：一套参数覆盖所有浏览器下载器
- **自适应选择器**：网站改版时自动重新定位元素（选择器自愈）

### 🤖 AI 集成（MCP Server）
- Claude / Cursor 直接调用 Crawlo 抓取能力
- 三种抓取模式：`basic`（1-3s）→ `stealth`（3-10s）→ `max-stealth`（10s+）
- 浏览器单例池：stealth/max-stealth 模式复用实例
- 结构化错误返回：区分 `TIMEOUT` / `CONNECTION_ERROR` 等，含建议提示

### 📊 四级背压防线
- Engine 层请求生成控制 + QueueManager 策略驱动
- 智能增强：`IntelligentBackpressureCalculator` + `BackpressureMonitor`

### 📬 多渠道通知系统
- 5 种渠道：钉钉 / 飞书 / 企业微信 / 邮件 / 短信
- 30+ 预定义模板，异步发送，消息去重 + 窗口限制

### 🔄 灵活的配置模式

| 模式 | 适用场景 | Redis 要求 |
|------|---------|-----------|
| **Standalone** | 单机开发测试 | 不需要 |
| **Distributed** | 多节点分布式 | 必需 |
| **Auto** ⭐ | 智能检测（推荐） | 可选 |

---

## 📚 文档

| 你是？ | 推荐阅读 |
|--------|---------|
| **新手** | [5分钟快速上手](docs/getting-started/5min-quickstart.md) → [安装指南](docs/getting-started/installation.md) |
| **开发者** | [配置指南](docs/guides/configuration/) → [调度指南](docs/guides/scheduling/) |
| **运维** | [配置模式详解](docs/guides/configuration/run-modes.md) → [检查点系统](docs/concepts/checkpoint-guide.md) |

👉 **[浏览完整文档 →](docs/index.md)**

---

## 💡 示例项目

查看 [`examples/`](examples/) 目录：
- **基础示例** - 快速上手
- **高级示例** - 复杂场景
- **生产级示例** - 可直接用于生产

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

本项目采用 BSD 3-Clause 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

<p align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给我们一个 Star！</strong>
</p>

</div>

<div id="en-content" style="display:none;">

## ✨ Quick Start (3 Steps)

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

## 🚀 Key Features

### ⚡ High-Performance Async Architecture
- Built on asyncio + aiohttp/httpx/curl-cffi multi-protocol downloaders
- Smart concurrency control, connection pool reuse, auto throughput optimization
- HTTP/2 support, TLS fingerprint emulation (bypass JA3 detection)

### 🛡️ Robust Anti-Bot Capabilities
- **HybridDownloader**: 6-level detection priority, auto-switch protocol/browser engine
- **Cloudflare Auto-Bypass**: Detects challenge pages and auto-switches to stealth browser
- **5 Browser Downloaders**: Playwright / Camoufox / CloakBrowser / DrissionPage / Chrome
- **BROWSER_* Unified Config Layer**: One set of params for all browser downloaders
- **Adaptive Selectors**: Auto-relocate elements when site structure changes

### 🤖 AI Integration (MCP Server)
- Claude / Cursor directly invoke Crawlo scraping capabilities
- Three scraping modes: `basic` (1-3s) → `stealth` (3-10s) → `max-stealth` (10s+)
- Browser singleton pool: stealth/max-stealth modes reuse instances
- Structured error responses: distinguish `TIMEOUT` / `CONNECTION_ERROR` with suggestions

### 📊 Four-Level Backpressure Defense
- Engine-level request generation control + QueueManager strategy-driven
- Intelligent enhancement: `IntelligentBackpressureCalculator` + `BackpressureMonitor`

### 📬 Multi-Channel Notification
- 5 channels: DingTalk / Feishu / WeCom / Email / SMS
- 30+ preset templates, async delivery, message dedup + rate limiting

### 🔄 Flexible Run Modes

| Mode | Use Case | Redis Required |
|------|----------|---------------|
| **Standalone** | Single-machine dev/test | No |
| **Distributed** | Multi-node distributed | Yes |
| **Auto** ⭐ | Auto-detect (recommended) | Optional |

---

## 📚 Documentation

| You are? | Recommended Reading |
|----------|-------------------|
| **Beginner** | [5-Min Quickstart](docs/getting-started/5min-quickstart.md) → [Installation](docs/getting-started/installation.md) |
| **Developer** | [Configuration Guide](docs/guides/configuration/) → [Scheduling Guide](docs/guides/scheduling/) |
| **Ops** | [Run Modes](docs/guides/configuration/run-modes.md) → [Checkpoint System](docs/concepts/checkpoint-guide.md) |

👉 **[Browse Full Docs →](docs/index.md)**

---

## 💡 Examples

See [`examples/`](examples/) directory:
- **Basic** - Quick start
- **Advanced** - Complex scenarios
- **Production** - Ready for production

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

## 📄 License

Licensed under BSD 3-Clause - see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>⭐ If this project helps you, please give us a Star!</strong>
</p>

</div>
