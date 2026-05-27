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
  <a href="README.zh.md">中文</a> ·
  <a href="README.md">English</a>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#核心特性">核心特性</a> ·
  <a href="#文档">文档</a> ·
  <a href="#示例">示例</a>
</p>

---

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

### 🔄 三种部署模式

| 模式 | 配置 | 协调机制 | 适用场景 |
|------|------|---------|---------|
| **内存模式** | `RUN_MODE='standalone'` `QUEUE_TYPE='memory'` | 无（单机自动退出） | 开发调试、快速验证 |
| **多节点协作** ⭐ | `RUN_MODE='auto'` `QUEUE_TYPE='redis'` | 竞争消费（BZPOPMIN） | 多机并发，可接受任务丢失 |
| **分布式系统** | `RUN_MODE='distributed'` `QUEUE_TYPE='redis_stream'` | ACK + 心跳 + 故障转移 | 生产环境，任务可靠性高 |

> 三种模式的优先级模型完全一致，切换模式无需修改爬虫代码。
> [详细了解 →](docs/concepts/architecture.md#2-部署模式-deployment-modes)

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
