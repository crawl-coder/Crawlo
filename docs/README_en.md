# Crawlo Documentation

Welcome to the official documentation for the Crawlo framework. Crawlo is a high-performance, scalable Python crawling framework that supports both standalone and distributed deployment.

## Introduction

Crawlo is a modern asynchronous web crawling framework based on asyncio, designed for high-performance data collection. It provides a complete toolkit to handle everything from simple web scraping to complex distributed crawling scenarios.

### Key Features

- **High-performance asynchronous crawling** - High concurrency processing based on asyncio
- **Multiple downloader support** - Supports various HTTP clients including aiohttp, httpx, and curl-cffi
- **Built-in data cleaning and validation** - Powerful data processing capabilities
- **Distributed crawling support** - Seamless switching between standalone and distributed deployment
- **Flexible middleware system** - Extensible request/response processing mechanism
- **Powerful configuration management system** - Unified configuration management and validation
- **Detailed logging and monitoring** - Comprehensive runtime status tracking
- **Windows and Linux compatibility** - Cross-platform support

## Quick Start

### Installation

```bash
pip install crawlo
```

Or install from source:

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

### Your First Spider

```python
from crawlo import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # Parsing logic
        pass

# Run the spider
# crawlo run example
```

## Documentation Index

### Core Concepts
- [Architecture Overview](modules/architecture/index_en.md) - Overall architecture design of Crawlo
- [Running Modes](modules/architecture/modes_en.md) - Detailed explanation of standalone and distributed modes
- [Configuration System](modules/configuration/index_en.md) - Configuration management and validation

### Core Modules
- [Engine](modules/core/engine_en.md) - Core coordinator of the crawling process
- [Scheduler](modules/core/scheduler_en.md) - Request queue and deduplication management
- [Processor](modules/core/processor_en.md) - Response processing and data extraction
- [Spider Base Class](modules/core/spider_en.md) - Spider base class and lifecycle

### Functional Modules
- [Downloader](modules/downloader/index_en.md) - HTTP client implementations
- [Queue](modules/queue/index_en.md) - Request queue management
- [Filter](modules/filter/index_en.md) - Request deduplication functionality
- [Middleware](modules/middleware/index_en.md) - Request/response processing components
- [Pipeline](modules/pipeline/index_en.md) - Data processing and storage components
- [Extension](modules/extension/index_en.md) - Additional features and monitoring components

### CLI Tools
- [CLI Overview](modules/cli/index_en.md) - Command-line tool usage guide
- [startproject](modules/cli/startproject_en.md) - Project initialization command
- [genspider](modules/cli/genspider_en.md) - Spider generation command
- [run](modules/cli/run_en.md) - Spider execution command
- [list](modules/cli/list_en.md) - View spider list
- [check](modules/cli/check_en.md) - Configuration check command
- [stats](modules/cli/stats_en.md) - View statistics information

### Advanced Topics
- [Distributed Deployment](modules/advanced/distributed_en.md) - Distributed crawling configuration and deployment
- [Performance Optimization](modules/advanced/performance_en.md) - Performance tuning guide
- [Troubleshooting](modules/advanced/troubleshooting_en.md) - Common issues and solutions
- [Best Practices](modules/advanced/best_practices_en.md) - Development best practices

### API Reference
- [Complete API Documentation](api/) - Detailed class and method reference

## Learning Path

If you're new to Crawlo, we recommend learning in the following order:

1. **Getting Started** - Read the quick start guide and run your first example
2. **Core Concepts** - Understand the framework architecture and basic concepts
3. **Core Modules** - Dive deep into core components like engine, scheduler, and processor
4. **Functional Modules** - Learn modules like downloader, queue, and filter based on your needs
5. **Advanced Topics** - Master advanced features like distributed deployment and performance optimization

## Contributing

We welcome community contributions! If you'd like to contribute to Crawlo:

1. Fork the project repository
2. Create a feature branch
3. Commit your changes
4. Submit a Pull Request

## License

Crawlo is released under the MIT License.