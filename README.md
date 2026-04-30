<p align="center">
  <img src="assets/logo.svg" alt="Crawlo Logo" width="150"/>
</p>

<h1 align="center">Crawlo</h1>

<p align="center">
  <strong>一个基于 asyncio 的现代化、高性能 Python 异步爬虫框架。</strong>
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
- 基于 asyncio + aiohttp，充分利用异步 I/O
- 智能并发控制，自动优化吞吐量

### 🛡️ 强大的反反爬能力
- **智能混合下载器**：自动切换协议/浏览器引擎
- **Cloudflare 自动绕过**：内置多种绕过策略
- **隐身浏览器集成**：camoufox/playwright/drissionpage
- **自适应选择器**：元素自愈，网站改版自动适配

### 🤖 AI 集成（MCP Server）
- Claude/Cursor 直接调用 Crawlo 抓取能力
- 智能抓取模式：basic/stealth/max-stealth

### 📊 智能调度系统
- 优先级队列、自动重试、智能限速
- **多维度自适应背压系统**：实时调控，防止队列溢出

### 🔄 灵活的配置模式
| 模式 | 适用场景 | Redis要求 |
|------|---------|----------|
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

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

<p align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给我们一个 Star！</strong>
</p>
