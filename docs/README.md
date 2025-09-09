# Crawlo Documentation

Welcome to the Crawlo framework documentation. Crawlo is a modern, high-performance Python asynchronous web scraping framework designed to simplify the development and deployment of web crawlers.

## Table of Contents

1. [Quick Start Guide](quick_start_guide.md) - Get up and running with Crawlo quickly
2. [Framework Documentation](crawlo_framework_documentation.md) - Comprehensive guide to all framework features
3. [API Reference](api_reference.md) - Detailed documentation of all classes and methods
4. [Distributed Crawling Tutorial](distributed_crawling_tutorial.md) - Complete guide to setting up distributed crawling
5. [Configuration Best Practices](configuration_best_practices.md) - Guidelines for configuring Crawlo projects
6. [Deduplication Pipelines Guide](deduplication_pipelines_guide.md) - Detailed guide to all deduplication pipelines
7. [Deduplication Configuration](deduplication_configuration.md) - How to configure deduplication for different modes
8. [Examples](../examples/) - Real-world examples showing how to use Crawlo

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

For detailed information about specific classes and methods, refer to the [API Reference](api_reference.md).

For a complete guide to distributed crawling, see the [Distributed Crawling Tutorial](distributed_crawling_tutorial.md).

For guidelines on configuring your projects, see [Configuration Best Practices](configuration_best_practices.md).

For information about deduplication pipelines, see [Deduplication Pipelines Guide](deduplication_pipelines_guide.md) and [Deduplication Configuration](deduplication_configuration.md).

## Examples

The [examples](../examples/) directory contains complete, working examples that demonstrate various aspects of the framework:

- Standalone crawling example
- Distributed crawling example with Redis
- Real-world data extraction scenarios

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/crawl-coder/Crawlo).