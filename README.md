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
  <a href="#-快速开始3步上手">快速开始</a> •
  <a href="#-核心特性">核心特性</a> •
  <a href="#-文档">文档</a> •
  <a href="#-示例">示例</a>
</p>

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
- **HybridDownloader**：6 级检测优先级（请求标记 → URL 模式 → 域名 → 扩展名 → 默认），自动切换协议/浏览器引擎
- **Cloudflare 自动绕过**：检测挑战页面后自动切换隐身浏览器
- **5 种浏览器下载器**：Playwright / Camoufox / CloakBrowser / DrissionPage / Chrome
- **BROWSER_* 统一配置层**：一套参数覆盖所有浏览器下载器
- **自适应选择器**：网站改版时自动重新定位元素（选择器自愈）

### 🤖 AI 集成（MCP Server）
- Claude / Cursor 直接调用 Crawlo 抓取能力
- 三种抓取模式：`basic`（1-3s）→ `stealth`（3-10s）→ `max-stealth`（10s+）
- 浏览器单例池：stealth/max-stealth 模式复用实例，消除重复启动开销
- 结构化错误返回：区分 `TIMEOUT` / `CONNECTION_ERROR` / `STEALTH_UNAVAILABLE` 等，含建议提示
- `spider` 工具内置 `delay` 限流参数，保护目标站点

### 📊 四级背压防线
- **Engine** 层：请求生成端控制（入队 + TaskManager 双维度检查）
- **QueueManager** 层：策略驱动（`QueueSizeStrategy` / `AdaptiveStrategy` / `CompositeStrategy`）
- **MemoryQueue** 层：Mixin 委托 + 回退逻辑
- **硬限制**：队列满直接拒绝
- 智能增强：`IntelligentBackpressureCalculator` + `BackpressureMonitor` 可选集成

### 📬 多渠通知系统
- **5 种渠道**：钉钉 / 飞书 / 企业微信 / 邮件 / 短信
- **30+ 预定义模板**：任务启停、异常告警、进度更新、数据库监控
- **异步发送**：`async_send_*` 函数，`run_in_executor` 包装避免阻塞事件循环
- 消息去重 + 窗口限制，防止通知风暴

### 🔄 灵活的配置模式
| 模式 | 适用场景 | Redis 要求 |
|------|---------|-----------|
| **Standalone** | 单机开发测试 | 不需要 |
| **Distributed** | 多节点分布式 | 必需 |
| **Auto** ⭐ | 智能检测（推荐） | 可选 |

👉 **[详细了解配置模式 →](docs/guides/configuration/run-modes.md)**

---

## 📚 文档

### 🎯 按角色阅读

| 你是？ | 推荐阅读 |
|--------|---------|
| **新手** | [5分钟快速上手](docs/getting-started/5min-quickstart.md) → [安装指南](docs/getting-started/installation.md) |
| **开发者** | [配置指南](docs/guides/configuration/) → [调度指南](docs/guides/scheduling/) |
| **运维** | [配置模式详解](docs/guides/configuration/run-modes.md) → [检查点系统](docs/concepts/checkpoint-guide.md) |

### 📖 完整文档导航

- 🚀 **[快速开始](docs/getting-started/)** - 安装、创建第一个爬虫
- 📚 **[教程系列](docs/tutorials/)** - 从基础到生产的完整教程
- 🎯 **[使用指南](docs/guides/)** - 按场景分类的深度指南
  - [配置指南](docs/guides/configuration/)、[调度指南](docs/guides/scheduling/)
  - [背压系统](docs/guides/scheduling/backpressure.md)、[运行模式](docs/guides/configuration/run-modes.md)
- 📖 **[核心概念](docs/concepts/)** - 架构设计、生命周期、错误处理
- 🔧 **[API参考](docs/reference/)** - 完整的 API 文档
- 💡 **[实战案例](docs/examples/)** - 真实项目示例和最佳实践
- ❓ **[常见问题](docs/faq/)** - FAQ 和故障排查

👉 **[浏览完整文档 →](docs/index.md)**

---

## 💡 示例项目

查看 [`examples/`](examples/) 目录：

- **基础示例** - 快速上手
- **高级示例** - 复杂场景
- **生产级示例** - 可直接用于生产

👉 **[查看所有示例 →](docs/examples/)**

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 BSD 3-Clause 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

<p align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给我们一个 Star！</strong>
</p>
