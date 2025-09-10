# Crawlo Documentation

Welcome to the Crawlo framework documentation. Crawlo is a modern, high-performance Python asynchronous web scraping framework designed to simplify the development and deployment of web crawlers.

## Language Selection

- [English Documentation](index.md)
- [中文文档](index_zh.md)

## Overview

Crawlo provides:

- **Multiple Execution Modes**: Standalone (default), Distributed (Redis-based), and Auto-detection mode
- **Command-line Interface**: Tools like `crawlo startproject`, `crawlo genspider`, and `crawlo run` streamline project creation and execution
- **Automatic Spider Discovery**: Automatically loads spider modules from the `spiders/` directory without manual registration
- **Smart Configuration System**: Chainable configuration methods and preset configurations for different environments
- **High-Performance Architecture**: Built on `asyncio`, supports multiple downloaders (aiohttp, httpx, curl-cffi), and includes intelligent middleware for deduplication, retries, and proxy support
- **Monitoring and Management**: Real-time statistics, structured logging, health checks, and performance analysis tools

## Documentation Structure

1. [Getting Started](getting_started/) - Get up and running with Crawlo quickly
2. [Core Concepts](core_concepts/) - Fundamental concepts and architecture
3. [Development Guide](development_guide/) - Comprehensive guide to developing with Crawlo
4. [Advanced Topics](advanced_topics/) - Advanced features and techniques
5. [Configuration Reference](configuration_reference/) - Detailed configuration options
6. [API Reference](api_reference/) - Complete API documentation
7. [Examples](examples/) - Real-world examples
8. [Troubleshooting](troubleshooting/) - Common issues and solutions
9. [Contribution Guide](contribution/) - How to contribute to Crawlo

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/crawl-coder/Crawlo).