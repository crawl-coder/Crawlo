# Crawlo 文档

欢迎使用 Crawlo - 一个高性能、可扩展的 Python 爬虫框架。

## 什么是 Crawlo？

Crawlo 是一个基于 asyncio 的现代异步网络爬虫框架，专为高性能数据采集而设计。它提供了完整的工具集来处理从简单网页抓取到复杂分布式爬取的各种场景。

### 核心特性

- **高性能异步爬取** - 基于 asyncio 实现大规模并发抓取
- **智能混合下载器 (Hybrid)** - 自动在协议(aiohttp)与浏览器(Playwright)间智能切换
- **自适应选择器 (Adaptive)** - 基于元素指纹的自动修复技术，解决选择器失效痛点
- **AI 适配层 (MCP Server)** - 让 LLM (Claude/Cursor) 直接驱动爬虫抓取数据
- **分布式爬取支持** - 支持单机(Standalone)与分布式(Distributed)的一键切换
- **强大的反爬对抗** - 内置 Cloudflare 绕过、Stealth 指纹伪造及 Camoufox 支持
- **高度可配置的中间件** - 洋葱模型设计，处理请求、响应、重试、代理与过滤
- **详细的监控与日志** - 支持内存监控、Redis 状态监控及多平台消息通知

## 快速开始

### 安装

```bash
pip install crawlo
```

### 第一个爬虫

```python
from crawlo import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # 解析逻辑
        pass

# 运行爬虫
# crawlo run example
```

## 文档导航

### [🔰 新手教程](tutorials/index.md)
**推荐！** 从零开始，系统学习Crawlo爬虫框架。

### [🚀 快速入门](getting-started/index.md)
项目初始化、爬虫编写及运行基础。

### [🏗️ 核心架构](concepts/architecture.md)
深入了解 Crawlo 的异步引擎、洋葱模型中间件以及灵活的运行模式（单机/分布式）。

### [🛠️ 核心组件](concepts/core-components.md)
详解下载器、调度器、管道和爬虫基类。学习如何配置代理、处理重试以及对接 MySQL/MongoDB。

### [⚙️ 配置指南](guides/configuration/index.md)
三种运行模式（Standalone/Auto/Distributed）详解，配置优先级与合并策略。

### [💡 实战案例库](examples/index.md)
包含东方财富、InfoQ、OFweek 等多个真实场景的完整案例代码。

### [🌟 高级特性](reference/index.md)
探索 Crawlo 的杀手级功能：
- **AI 适配层 (MCP)**：让 Claude/Cursor 直接驱动爬虫。
- **自适应选择器**：网页改版后的自动修复技术。
- **混合下载器**：协议与浏览器的智能切换。
- **Cloudflare 绕过**：自动识别并处理验证码挑战。

### [💻 命令行参考](reference/cli-reference.md)
一站式查阅所有 `crawlo` 命令及参数。

### [🐚 Shell 交互式终端](shell-guide.md)
实时调试选择器、测试动态渲染，无需编写完整爬虫。

### [🔄 curl 命令转换](migration/curl-conversion.md)
将浏览器 DevTools 的 curl 命令直接转换为 Crawlo Request，快速复现浏览器请求。

### [💾 检查点持久化](concepts/checkpoint-guide.md)
Ctrl+C 优雅关闭后从断点续爬，支持 JSON/SQLite 双存储后端。

## 学习路径

如果您是 Crawlo 的新用户，建议按以下顺序学习：

1. **入门** - 阅读[快速入门指南](getting-started/index.md)，运行第一个示例。
2. **架构** - 了解[核心架构](concepts/architecture.md)设计及运行模式。
3. **深入** - 掌握[核心组件](concepts/core-components.md)的使用。
4. **调试** - 使用 [Shell 交互式终端](shell-guide.md)实时调试选择器。
   - 尝试 [curl 命令转换](migration/curl-conversion.md)：从浏览器复制 curl 直接执行
5. **持久化** - 了解[检查点持久化](concepts/checkpoint-guide.md)：Ctrl+C 后断点续爬
6. **高阶** - 探索[高级特性](reference/index.md)如 AI 适配、自适应选择器。

## 贡献

我们欢迎社区贡献！如果您想为 Crawlo 做出贡献：

1. Fork 项目仓库
2. 创建功能分支
3. 提交您的更改
4. 发起 Pull Request

## 许可证

Crawlo 采用 MIT 许可证发布。