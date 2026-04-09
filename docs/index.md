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

## 文档目录

### 核心概念
- [架构概述](modules/architecture/index.md) - Crawlo 的整体架构设计
- [运行模式](modules/architecture/modes.md) - 单机与分布式模式详解
- [配置系统](modules/configuration/index.md) - 配置管理与验证

### 核心模块
- [引擎 (Engine)](modules/core/engine.md) - 爬取过程的核心协调器
- [调度器 (Scheduler)](modules/core/scheduler.md) - 请求队列与去重管理
- [处理器 (Processor)](modules/core/processor.md) - 响应处理与数据提取
- [爬虫基类 (Spider)](modules/core/spider.md) - 爬虫基础类与生命周期

### 功能模块
- [下载器 (Downloader)](modules/downloader/index.md) - HTTP 客户端实现
- [队列 (Queue)](modules/queue/index.md) - 请求队列管理
- [过滤器 (Filter)](modules/filter/index.md) - 请求去重功能
- [中间件 (Middleware)](modules/middleware/index.md) - 请求/响应处理组件
- [管道 (Pipeline)](modules/pipeline/index.md) - 数据处理和存储组件
- [扩展 (Extension)](modules/extension/index.md) - 附加功能和监控组件

### 命令行工具
- [CLI 概述](modules/cli/index.md) - 命令行工具使用指南
- [startproject](modules/cli/startproject.md) - 项目初始化命令
- [genspider](modules/cli/genspider.md) - 爬虫生成命令
- [run](modules/cli/run.md) - 爬虫运行命令
- [list](modules/cli/list.md) - 查看爬虫列表
- [check](modules/cli/check.md) - 配置检查命令
- [stats](modules/cli/stats.md) - 统计信息查看

### 高级主题
- [分布式部署](modules/advanced/distributed.md) - 分布式爬取配置与部署
- [性能优化](modules/advanced/performance.md) - 性能调优指南
- [故障排除](modules/advanced/troubleshooting.md) - 常见问题与解决方案
- [最佳实践](modules/advanced/best_practices.md) - 开发最佳实践

### API 参考
- [完整 API 文档](api/) - 详细的类和方法参考

## 学习路径

如果您是 Crawlo 的新用户，建议按以下顺序学习：

1. **入门** - 阅读快速开始指南，运行第一个示例
2. **核心概念** - 了解框架架构和基本概念
3. **核心模块** - 深入学习引擎、调度器、处理器等核心组件
4. **功能模块** - 根据需求学习下载器、队列、过滤器等模块
5. **高级主题** - 掌握分布式部署、性能优化等高级功能

## 贡献

我们欢迎社区贡献！如果您想为 Crawlo 做出贡献：

1. Fork 项目仓库
2. 创建功能分支
3. 提交您的更改
4. 发起 Pull Request

## 许可证

Crawlo 采用 MIT 许可证发布。