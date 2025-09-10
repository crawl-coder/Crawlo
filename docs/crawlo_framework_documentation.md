# Crawlo Framework Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Project Structure](#project-structure)
5. [Core Components](#core-components)
6. [Configuration](#configuration)
7. [Spiders](#spiders)
8. [Items](#items)
9. [Pipelines](#pipelines)
10. [Middleware](#middleware)
11. [Distributed Crawling](#distributed-crawling)
12. [Command Line Interface](#command-line-interface)
13. [Best Practices](#best-practices)
14. [Troubleshooting](#troubleshooting)

## Introduction

Crawlo is a modern, high-performance Python asynchronous web scraping framework designed to simplify the development and deployment of web crawlers. It supports both standalone and distributed modes, making it suitable for everything from small-scale development to large-scale production environments.

### Key Features

- **Multiple Execution Modes**: Standalone (default), Distributed (Redis-based), and Auto-detection mode
- **Command-line Interface**: Tools like `crawlo startproject`, `crawlo genspider`, and `crawlo run` streamline project creation and execution
- **Automatic Spider Discovery**: Automatically loads spider modules from the `spiders/` directory without manual registration
- **Smart Configuration System**: Chainable configuration methods and preset configurations for different environments
- **High-Performance Architecture**: Built on `asyncio`, supports multiple downloaders (aiohttp, httpx, curl-cffi), and includes intelligent middleware for deduplication, retries, and proxy support
- **Monitoring and Management**: Real-time statistics, structured logging, health checks, and performance analysis tools

## Installation

To install Crawlo, you can use pip:

```bash
# Clone the repository
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo

# Install in development mode
pip install -e .
```

### Dependencies

Crawlo requires Python 3.10+ and has the following key dependencies:

- aiohttp~=3.12.14
- aiomysql==0.2.0
- asyncmy==0.2.10
- cssselect==1.2.0
- dateparser==1.2.2
- httpx[http2]==0.27.0
- curl-cffi==0.13.0
- lxml==5.2.1
- motor==3.7.0
- parsel==1.9.1
- pydantic==2.11.7
- pymongo==4.11
- PyMySQL==1.1.1
- python-dateutil==2.9.0.post0
- redis==6.2.0
- requests==2.32.4
- six==1.17.0
- ujson==5.9.0
- urllib3==2.5.0
- w3lib==2.1.2
- psutil~=7.0.0
- anyio~=4.3.0
- httpcore~=1.0.5
- rich>=13.0.0
- astor>=0.8.0
- watchdog>=3.0.0

## Getting Started

### Creating a New Project

To create a new Crawlo project, use the `startproject` command:

```bash
crawlo startproject myproject
cd myproject
```

This will create the following directory structure:

```
myproject/
├── crawlo.cfg          # Project configuration
├── myproject/
│   ├── __init__.py
│   ├── settings.py     # Settings file
│   ├── items.py        # Data item definitions
│   └── spiders/        # Spider directory
└── run.py              # Run script
```

### Generating a Spider

To generate a spider template, use the `genspider` command:

```bash
crawlo genspider example example.com
```

This will create a spider in the `spiders/` directory with the following structure:

```python
from crawlo import Spider, Request
from myproject.items import ExampleItem

class ExampleSpider(Spider):
    name = "example"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        # Extract data
        item = ExampleItem()
        item['title'] = response.css('title::text').get()
        item['url'] = response.url
        yield item
        
        # Follow links
        for link in response.css('a::attr(href)').getall():
            yield Request(url=response.urljoin(link), callback=self.parse)
```

### Running a Spider

You can run a spider in several ways:

```bash
# Standalone mode (default)
python run.py example

# Distributed mode
python run.py example --distributed

# Development environment
python run.py example --env development --debug

# Custom concurrency
python run.py example --concurrency 20 --delay 0.5

# Using preset configurations
python run.py example --env production
```

## Project Structure

A typical Crawlo project follows this structure:

```
project_name/
├── crawlo.cfg              # Project configuration file
├── run.py                  # Main execution script
├── logs/                   # Log directory
├── project_name/           # Main Python package
│   ├── __init__.py         # Package initializer
│   ├── settings.py         # Configuration settings
│   ├── items.py            # Data item definitions
│   ├── middlewares.py      # Custom middlewares
│   ├── pipelines.py        # Data processing pipelines
│   └── spiders/            # Spider implementations
│       ├── __init__.py     # Spiders package initializer
│       └── *.py            # Individual spider files
```

### Key Files

1. **crawlo.cfg**: Project configuration file that identifies the project root
2. **run.py**: Main execution script for running spiders
3. **settings.py**: Configuration settings for the project
4. **items.py**: Data item definitions
5. **spiders/\*.py**: Individual spider implementations

## Core Components

### Engine

The engine is the core component that coordinates the crawling process. It manages the scheduler, downloader, and processor components.

### Scheduler

The scheduler manages the request queue and handles request deduplication. It supports both memory-based and Redis-based implementations for standalone and distributed modes respectively.

### Downloader

The downloader is responsible for fetching web pages. Crawlo supports multiple downloaders:

- **aiohttp**: High-performance default downloader
- **httpx**: Supports HTTP/2
- **curl-cffi**: Browser fingerprint simulation

### Processor

The processor handles the extraction of data from responses and passes items through the pipeline.

## Configuration

Crawlo provides a flexible configuration system with multiple ways to configure your project.

### Traditional Configuration

In `settings.py`:

```python
PROJECT_NAME = 'myproject'
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0
QUEUE_TYPE = 'memory'  # Standalone mode
# QUEUE_TYPE = 'redis'   # Distributed mode
```

### Smart Configuration Factory

```python
from crawlo.config import CrawloConfig

# Standalone mode
config = CrawloConfig.standalone().set_concurrency(16)

# Distributed mode
config = CrawloConfig.distributed(redis_host='192.168.1.100')

# Preset configurations
config = CrawloConfig.presets().production()

# Chainable calls
config = (CrawloConfig.standalone()
    .set_concurrency(20)
    .set_delay(1.5)
    .enable_debug()
    .enable_mysql())

# Environment variable configuration
config = CrawloConfig.from_env()
```

### Preset Configurations

| Configuration | Use Case | Features |
|---------------|----------|----------|
| `development()` | Development and debugging | Low concurrency, detailed logging, debug-friendly |
| `production()` | Production environment | High performance, auto mode, stable and reliable |
| `large_scale()` | Large-scale crawling | Distributed, memory optimized, batch processing |
| `gentle()` | Gentle mode | Low load, friendly to target servers |

## Spiders

Spiders are classes that define how to crawl and parse a particular website or set of websites.

### Basic Spider Structure

```python
from crawlo import Spider, Request
from myproject.items import MyItem

class MySpider(Spider):
    name = "myspider"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com"]
    
    def parse(self, response):
        # Extract data and yield items
        item = MyItem()
        item['title'] = response.css('title::text').get()
        yield item
        
        # Follow links
        for link in response.css('a::attr(href)').getall():
            yield Request(url=response.urljoin(link), callback=self.parse)
```

### Spider Attributes

- `name`: Unique identifier for the spider
- `allowed_domains`: List of domains the spider is allowed to crawl
- `start_urls`: List of URLs where the spider will begin crawling
- `custom_settings`: Dictionary of settings that override project settings

### Spider Methods

- `start_requests()`: Generates initial requests
- `parse(response)`: Parses responses and extracts data

## Items

Items are containers for scraped data. They define the structure of the data you want to extract.

### Defining Items

```python
from crawlo.items import Item, Field

class MyItem(Item):
    title = Field(description="Page title")
    url = Field(description="Page URL")
    content = Field(description="Page content")
```

### Using Items

```python
def parse(self, response):
    item = MyItem()
    item['title'] = response.css('title::text').get()
    item['url'] = response.url
    item['content'] = response.css('body').get()
    yield item
```

## Pipelines

Pipelines process items after they are extracted by spiders. They can clean, validate, and store data.

### Built-in Pipelines

- `ConsolePipeline`: Outputs items to the console
- `JsonPipeline`: Saves items to JSON files
- `CsvPipeline`: Saves items to CSV files
- `AsyncmyMySQLPipeline`: Stores items in MySQL database
- `MongoPipeline`: Stores items in MongoDB

### Configuring Pipelines

In `settings.py`:

```python
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]
```

### Custom Pipelines

```python
class CustomPipeline:
    def process_item(self, item, spider):
        # Process the item
        return item
```

## Middleware

Middleware components process requests and responses as they flow through the system.

### Built-in Middleware

- `RequestIgnoreMiddleware`: Filters requests
- `DownloadDelayMiddleware`: Controls download delays
- `DefaultHeaderMiddleware`: Adds default headers
- `ProxyMiddleware`: Handles proxies
- `RetryMiddleware`: Implements retry logic
- `ResponseCodeMiddleware`: Processes response codes

### Configuring Middleware

In `settings.py`:

```python
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
]
```

## Distributed Crawling

Crawlo supports distributed crawling using Redis for coordination between multiple nodes.

### Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Node A     │    │  Node B     │    │  Node N     │
│ (Crawler)   │    │ (Crawler)   │    │ (Crawler)   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
              ┌───────────▼────────────┐
              │     Redis Cluster     │
              │ ┌─────────────────────┐│
              │ │ Task Queue          ││
              │ │ Deduplication Set   ││
              │ │ Statistics          ││
              │ └─────────────────────┘│
              └─────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │    Shared Storage     │
              │   MySQL / MongoDB     │
              └─────────────────────────┘
```

### Distributed Features

- **Automatic Load Balancing**: Tasks are automatically distributed among nodes
- **Distributed Deduplication**: Prevents duplicate crawling across nodes
- **Horizontal Scaling**: Dynamically add or remove nodes
- **Fault Recovery**: Node failures don't affect overall operation

### Configuration

To enable distributed crawling, configure the following in `settings.py`:

```python
# Distributed mode configuration
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis'

# Concurrency settings
CONCURRENCY = 16
DOWNLOAD_DELAY = 1.0

# Scheduler configuration
SCHEDULER = 'crawlo.scheduler.redis_scheduler.RedisScheduler'

# Redis configuration
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Distributed deduplication
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'
REDIS_KEY = 'myproject:fingerprint'
```

### Running Distributed Crawlers

```bash
# Start Redis server
redis-server

# Run distributed crawler
python run.py myspider --distributed

# Multi-node deployment
# Node 1
python run.py myspider --distributed --redis-host 192.168.1.100

# Node 2
python run.py myspider --distributed --redis-host 192.168.1.100 --concurrency 20
```

## Command Line Interface

Crawlo provides a comprehensive command-line interface for managing projects and crawlers.

### Available Commands

| Command | Function | Example |
|---------|----------|---------|
| `startproject` | Create a new project | `crawlo startproject myproject` |
| `genspider` | Generate a spider | `crawlo genspider news news.com` |
| `list` | List all spiders | `crawlo list` |
| `check` | Check spider compliance | `crawlo check` |
| `run` | Run a spider | `crawlo run news --distributed` |
| `stats` | View statistics | `crawlo stats news` |

### Command Examples

```bash
# Create a new project
crawlo startproject myproject

# Generate a spider
crawlo genspider example example.com

# List available spiders
crawlo list

# Check spider syntax
crawlo check example

# Run a spider
crawlo run example

# View statistics
crawlo stats example
```

## Best Practices

### Development Phase

```bash
# Use development configuration with low concurrency and detailed logging
python run.py my_spider --env development --debug
```

### Testing Phase

```bash
# Dry run mode to validate logic
python run.py my_spider --dry-run
```

### Production Environment

```bash
# Use production configuration or distributed mode
python run.py my_spider --env production
python run.py my_spider --distributed --concurrency 50
```

### Large-Scale Crawling

```bash
# Use large-scale configuration with distributed mode
python run.py my_spider --env large-scale
```

### Downloader Selection Best Practices

```python
# Development/Testing - Use httpx (stable, good compatibility)
DOWNLOADER_TYPE = 'httpx'

# Production - Use aiohttp (high performance)
DOWNLOADER_TYPE = 'aiohttp'

# Anti-scraping scenarios - Use curl_cffi (browser fingerprint)
DOWNLOADER_TYPE = 'curl_cffi'
CURL_BROWSER_TYPE = 'chrome136'
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   ImportError: No module named 'myproject'
   ```
   **Solution**: Ensure you're running the script from the project root directory where `crawlo.cfg` is located.

2. **Redis Connection Failures**
   ```
   Redis connection failed: localhost:6379
   ```
   **Solution**: Check Redis service status and use `--check-redis` to test the connection.

3. **Configuration File Errors**
   ```
   crawlo.cfg not found
   ```
   **Solution**: Ensure you're in the directory containing `crawlo.cfg` when running framework commands.

4. **Spider Class Not Found**
   ```
   No spider found for: myspider
   ```
   **Solution**: Check that the spider file has the correct `name` attribute.

### Debugging Methods

```bash
# Enable debug mode
python run.py myspider --debug

# Limit data for testing
python run.py myspider --max-pages 5

# Check configuration
python -c "from myproject import settings; print(settings.CONCURRENCY)"
```

### Performance Tuning

```python
# Concurrency control
CONCURRENCY = 16                    # Concurrent requests
DOWNLOAD_DELAY = 1.0               # Download delay
CONNECTION_POOL_LIMIT = 100        # Global connection pool size
CONNECTION_POOL_LIMIT_PER_HOST = 30 # Connections per host

# Retry strategy
MAX_RETRY_TIMES = 3                # Maximum retry attempts
RETRY_HTTP_CODES = [500, 502, 503] # Retry status codes

# Statistics and monitoring
DOWNLOADER_STATS = True            # Enable downloader statistics
DOWNLOAD_STATS = True              # Record download time and size
DOWNLOADER_HEALTH_CHECK = True     # Downloader health check
REQUEST_STATS_ENABLED = True       # Request statistics
```