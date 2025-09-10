# Crawlo 框架文档

欢迎使用 Crawlo 框架文档。Crawlo 是一个现代化、高性能的 Python 异步网络爬虫框架，旨在简化网络爬虫的开发和部署。

## 语言选择

- [English Documentation](index.md)
- [中文文档](index_zh.md)

## 概述

Crawlo 提供：

- **多种执行模式**：单机模式（默认）、分布式模式（基于 Redis）和自动检测模式
- **命令行界面**：`crawlo startproject`、`crawlo genspider` 和 `crawlo run` 等工具简化项目创建和执行
- **自动爬虫发现**：自动从 `spiders/` 目录加载爬虫模块，无需手动注册
- **智能配置系统**：链式配置方法和预设配置，适用于不同环境
- **高性能架构**：基于 `asyncio` 构建，支持多种下载器（aiohttp、httpx、curl-cffi），并包含智能中间件用于去重、重试和代理支持
- **监控和管理**：实时统计、结构化日志记录、健康检查和性能分析工具

## 文档结构

1. [入门指南](getting_started/) - 快速上手 Crawlo
2. [核心概念](core_concepts/) - 基本概念和架构
3. [开发指南](development_guide/) - 使用 Crawlo 开发的综合指南
4. [高级主题](advanced_topics/) - 高级特性和技术
5. [配置参考](configuration_reference/) - 详细的配置选项
6. [API 参考](api_reference/) - 完整的 API 文档
7. [示例](examples/) - 真实示例
8. [故障排除](troubleshooting/) - 常见问题和解决方案
9. [贡献指南](contribution/) - 如何为 Crawlo 做贡献

## 支持

如有问题、疑问或贡献，请访问 [GitHub 仓库](https://github.com/crawl-coder/Crawlo)。