# Crawlo Documentation

Welcome to the Crawlo framework documentation. Crawlo is a modern, high-performance Python asynchronous web scraping framework designed to simplify the development and deployment of web crawlers.

## Language Selection

- [English Documentation](README.md)
- [中文文档](README_zh.md)

## Overview

Crawlo provides:

- **Multiple Execution Modes**: Standalone (default), Distributed (Redis-based), and Auto-detection mode
- **Command-line Interface**: Tools like `crawlo startproject`, `crawlo genspider`, and `crawlo run` streamline project creation and execution
- **Automatic Spider Discovery**: Automatically loads spider modules from the `spiders/` directory without manual registration
- **Smart Configuration System**: Chainable configuration methods and preset configurations for different environments
- **High-Performance Architecture**: Built on `asyncio`, supports multiple downloaders (aiohttp, httpx, curl-cffi), and includes intelligent middleware for deduplication, retries, and proxy support
- **Monitoring and Management**: Real-time statistics, structured logging, health checks, and performance analysis tools

## Getting Started

To get started with Crawlo, read the [Quick Start Guide](quick_start_guide.md) which will walk you through creating your first project and running your first spider.

For more detailed information about the framework's features and capabilities, see the [Framework Documentation](crawlo_framework_documentation.md).

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/crawl-coder/Crawlo).