# Crawlo 框架文档

欢迎使用 Crawlo 框架文档。Crawlo 是一个现代化、高性能的 Python 异步网络爬虫框架，旨在简化网络爬虫的开发和部署。

## 目录

1. [快速入门指南](quick_start_guide_zh.md) - 快速上手 Crawlo
2. [框架文档](crawlo_framework_documentation_zh.md) - 框架所有特性的综合指南
3. [API 参考](api_reference_zh.md) - 所有类和方法的详细文档
4. [分布式爬取教程](distributed_crawling_tutorial_zh.md) - 分布式爬取的完整指南
5. [配置最佳实践](configuration_best_practices_zh.md) - 配置 Crawlo 项目的指南
6. [示例](../examples/) - 展示如何使用 Crawlo 的真实示例

## 概述

Crawlo 提供：

- **多种执行模式**：单机模式（默认）、分布式模式（基于 Redis）和自动检测模式
- **命令行界面**：`crawlo startproject`、`crawlo genspider` 和 `crawlo run` 等工具简化项目创建和执行
- **自动爬虫发现**：自动从 `spiders/` 目录加载爬虫模块，无需手动注册
- **智能配置系统**：链式配置方法和预设配置，适用于不同环境
- **高性能架构**：基于 `asyncio` 构建，支持多种下载器（aiohttp、httpx、curl-cffi），并包含智能中间件用于去重、重试和代理支持
- **监控和管理**：实时统计、结构化日志记录、健康检查和性能分析工具

## 快速开始

要开始使用 Crawlo，请阅读[快速入门指南](quick_start_guide_zh.md)，它将引导您创建第一个项目并运行第一个爬虫。

有关框架特性和功能的更多详细信息，请参阅[框架文档](crawlo_framework_documentation_zh.md)。

有关特定类和方法的详细信息，请参阅[API 参考](api_reference_zh.md)。

有关分布式爬取的完整指南，请参阅[分布式爬取教程](distributed_crawling_tutorial_zh.md)。

有关配置项目的指南，请参阅[配置最佳实践](configuration_best_practices_zh.md)。

## 示例

[examples](../examples/) 目录包含完整的实际示例，演示了框架的各个方面：

- 单机爬取示例
- 使用 Redis 的分布式爬取示例
- 真实项目的数据提取场景

## 支持

如有问题、疑问或贡献，请访问 [GitHub 仓库](https://github.com/crawl-coder/Crawlo)。