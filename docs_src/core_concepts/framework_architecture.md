# Framework Architecture

This document provides a comprehensive overview of the Crawlo framework architecture, explaining how its components work together to enable efficient web crawling.

## Overview

Crawlo is a modern, high-performance Python asynchronous web scraping framework designed to simplify the development and deployment of web crawlers. It supports both standalone and distributed modes, making it suitable for everything from small-scale development to large-scale production environments.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Crawler                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Spider     │  │   Engine     │  │      ExtensionManager     │  │
│  │              │  │              │  │                          │  │
│  │ start_urls   │  │  Scheduler ◄─┼──┼──► StatsCollector         │  │
│  │ parse()      │  │              │  │                          │  │
│  │              │  │ Downloader ◄─┼──┼──► MiddlewareManager     │  │
│  │              │  │              │  │                          │  │
│  │              │  │ Processor  ◄─┼──┼──► PipelineManager       │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────────────┘  │
└──────────────────────────┼─────────────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │         Scheduler                   │
        │  ┌──────────────────────────────┐   │
        │  │       QueueManager           │   │
        │  │  ┌─────────┐  ┌────────────┐ │   │
        │  │  │ Memory  │  │   Redis    │ │   │
        │  │  │ Queue   │  │  Queue     │ │   │
        │  │  └─────────┘  └────────────┘ │   │
        │  └──────────────────────────────┘   │
        │  ┌──────────────────────────────┐   │
        │  │        Filter                │   │
        │  │  ┌─────────┐  ┌────────────┐ │   │
        │  │  │ Memory  │  │   Redis    │ │   │
        │  │  │ Filter  │  │  Filter    │ │   │
        │  │  └─────────┘  └────────────┘ │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │         Downloader                  │
        │  ┌──────────────────────────────┐   │
        │  │    MiddlewareManager         │   │
        │  │                              │   │
        │  │ RequestMiddleware ◄────────┐ │   │
        │  │ ResponseMiddleware        │ │   │
        │  │ ExceptionMiddleware       │ │   │
        │  │                          ╱  │   │
        │  └─────────────────────────╱───┘   │
        │                           ╱        │
        │  ┌───────────────────────▼──┐      │
        │  │  Download Implementations │      │
        │  │  - AioHttpDownloader   │      │
        │  │  - HttpXDownloader     │      │
        │  │  - CurlCffiDownloader  │      │
        │  └──────────────────────────┘      │
        └─────────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │          Processor                  │
        │  ┌──────────────────────────────┐   │
        │  │    PipelineManager           │   │
        │  │  ┌─────────────────────────┐ │   │
        │  │  │   Pipeline Stages       │ │   │
        │  │  │ - ValidationPipeline    │ │   │
        │  │  │ - ProcessingPipeline    │ │   │
        │  │  │ - StoragePipeline       │ │   │
        │  │  └─────────────────────────┘ │   │
        │  └──────────────────────────────┘   │
        └─────────────────────────────────────┘
```

## Core Components

### Engine

The Engine is the central component that coordinates the crawling process. It manages the interaction between the Scheduler, Downloader, and Processor components.

#### Responsibilities

1. **Orchestration**: Coordinates the flow of requests and responses between components
2. **Concurrency Management**: Controls the number of concurrent requests
3. **Event Handling**: Manages crawler lifecycle events
4. **Error Handling**: Handles exceptions and implements retry logic

#### Key Methods

- `start()`: Initialize and start the crawling process
- `stop()`: Gracefully stop the crawling process
- `pause()`: Pause crawling activities
- `resume()`: Resume paused crawling activities

### Scheduler

The Scheduler manages the request queue and handles request deduplication. It supports both memory-based and Redis-based implementations for standalone and distributed modes respectively.

#### Responsibilities

1. **Request Queue Management**: Maintains queues of pending requests
2. **Deduplication**: Prevents processing the same request multiple times
3. **Priority Handling**: Manages request priorities
4. **Queue Monitoring**: Tracks queue statistics and health

#### Components

- **QueueManager**: Manages different queue implementations
- **Filter**: Handles request deduplication

### Downloader

The Downloader is responsible for fetching web pages. Crawlo supports multiple downloaders:

- **AioHttpDownloader**: High-performance default downloader
- **HttpXDownloader**: Supports HTTP/2
- **CurlCffiDownloader**: Browser fingerprint simulation

#### Responsibilities

1. **HTTP Request Execution**: Makes HTTP requests to web servers
2. **Response Handling**: Processes HTTP responses
3. **Middleware Integration**: Works with request/response middleware
4. **Connection Management**: Manages HTTP connections efficiently

### Processor

The Processor handles the extraction of data from responses and passes items through the pipeline.

#### Responsibilities

1. **Response Parsing**: Extracts data from HTTP responses
2. **Item Generation**: Creates data items from parsed content
3. **Pipeline Coordination**: Passes items through processing pipelines
4. **Spider Callback Execution**: Calls spider parse methods

### Spider

Spiders are classes that define how to crawl and parse a particular website or set of websites.

#### Responsibilities

1. **Request Generation**: Defines initial requests and follow-up requests
2. **Response Parsing**: Extracts data from responses
3. **Data Yielding**: Produces items and new requests
4. **Custom Logic**: Implements domain-specific crawling logic

## Supporting Components

### Middleware

Middleware components process requests and responses as they flow through the system.

#### Types

- **RequestMiddleware**: Processes requests before they're sent
- **ResponseMiddleware**: Processes responses after they're received
- **ExceptionMiddleware**: Handles exceptions during processing

#### Built-in Middleware

- `RequestIgnoreMiddleware`: Filters requests
- `DownloadDelayMiddleware`: Controls download delays
- `DefaultHeaderMiddleware`: Adds default headers
- `ProxyMiddleware`: Handles proxies
- `RetryMiddleware`: Implements retry logic
- `ResponseCodeMiddleware`: Processes response codes

### Pipelines

Pipelines process items after they are extracted by spiders.

#### Built-in Pipelines

- `ConsolePipeline`: Outputs items to the console
- `JsonPipeline`: Saves items to JSON files
- `CsvPipeline`: Saves items to CSV files
- `AsyncmyMySQLPipeline`: Stores items in MySQL database
- `MongoPipeline`: Stores items in MongoDB

### Extensions

Extensions provide additional functionality to the crawler.

#### Built-in Extensions

- `LogIntervalExtension`: Periodically logs statistics
- `LogStats`: Collects and logs crawler statistics
- `CustomLoggerExtension`: Initializes logging system
- `MemoryMonitorExtension`: Monitors memory usage
- `PerformanceProfilerExtension`: Profiles performance

## Data Flow

### Request Processing Flow

1. **Spider generates requests** → Initial requests from `start_urls` or `start_requests()`
2. **Scheduler enqueues requests** → Requests are added to the queue with deduplication
3. **Scheduler dequeues requests** → Requests are pulled from the queue for processing
4. **Downloader processes requests** → HTTP requests are made and responses received
5. **Middleware processes requests/responses** → Pre/post processing of requests and responses
6. **Processor handles responses** → Spider parse methods are called
7. **Spider yields items/requests** → Data items and new requests are generated
8. **Pipeline processes items** → Items are processed through configured pipelines
9. **Scheduler enqueues new requests** → New requests are added back to the queue

### Data Flow Diagram

```
┌─────────────┐    1. Generate requests    ┌──────────────┐
│   Spider    ├───────────────────────────►│  Scheduler   │
└─────────────┘                            └──────┬───────┘
                                                  │ 2. Deduplication
                                                  ▼
                                        ┌─────────────────┐
                                        │     Filter      │
                                        └─────────┬───────┘
                                                  │ 3. Queue
                                                  ▼
                                        ┌─────────────────┐
                                        │      Queue      │
                                        └─────────┬───────┘
                                                  │ 4. Dequeue
                                                  ▼
                                        ┌─────────────────┐    5. Download
                                        │   Downloader    ├──────────────────┐
                                        └─────────────────┘                  │
                                                  │ 6. Parse               │
                                                  ▼                        ▼
                                        ┌─────────────────┐    7. Generate   ┌─────────────┐
                                        │   Processor     ├────────────────►│   Pipeline  │
                                        └─────────────────┘                 └─────────────┘
                                                  │ 8. Store
                                                  ▼
                                        ┌─────────────────┐
                                        │     Items       │
                                        └─────────────────┘
```

## Execution Modes

Crawlo supports three execution modes:

### Standalone Mode

- Uses in-memory queues and filters
- Suitable for development and small-scale crawling
- Lower resource overhead
- No external dependencies required

### Distributed Mode

- Uses Redis-based queues and filters
- Enables horizontal scaling across multiple nodes
- Shared state across nodes
- Requires Redis server

### Auto Mode

- Automatically detects the best mode based on environment
- Uses standalone mode by default
- Switches to distributed mode if Redis is available

## Configuration System

Crawlo provides a flexible configuration system with multiple configuration methods:

### Configuration Methods

1. **Settings File**: Traditional Python settings file
2. **Environment Variables**: Configuration via environment variables
3. **Smart Configuration Factory**: Programmatic configuration builder

### Key Configuration Options

- `CONCURRENCY`: Number of concurrent requests
- `DOWNLOAD_DELAY`: Delay between requests
- `QUEUE_TYPE`: Queue implementation (memory/redis)
- `DOWNLOADER_TYPE`: Downloader implementation
- `MIDDLEWARES`: Configured middleware components
- `PIPELINES`: Configured pipeline components

## Performance Considerations

### Concurrency Management

Crawlo uses asyncio to handle concurrency efficiently:

- **Event Loop**: Single-threaded event loop for I/O operations
- **Coroutines**: Lightweight concurrency primitives
- **Connection Pooling**: Reuse of HTTP connections
- **Resource Limits**: Configurable concurrency limits

### Memory Management

- **Efficient Data Structures**: Use of generators and iterators
- **Object Reuse**: Minimization of object creation
- **Garbage Collection**: Proper cleanup of resources
- **Memory Monitoring**: Built-in memory usage tracking

### Network Optimization

- **HTTP/2 Support**: Modern HTTP protocol support
- **Connection Reuse**: Persistent connections
- **Compression**: Automatic content decompression
- **Timeout Handling**: Configurable timeout settings

## Error Handling and Recovery

### Error Types

1. **Network Errors**: Connection failures, timeouts
2. **HTTP Errors**: 4xx, 5xx status codes
3. **Parsing Errors**: Data extraction failures
4. **System Errors**: Resource exhaustion, configuration issues

### Recovery Mechanisms

- **Retry Logic**: Automatic retry of failed requests
- **Circuit Breaker**: Prevention of cascading failures
- **Graceful Degradation**: Continued operation despite failures
- **Error Logging**: Comprehensive error tracking

## Monitoring and Debugging

### Built-in Monitoring

- **Statistics Collection**: Real-time crawler metrics
- **Performance Profiling**: Execution time tracking
- **Memory Monitoring**: Resource usage tracking
- **Health Checks**: System health verification

### Debugging Features

- **Verbose Logging**: Detailed operational logging
- **Debug Middleware**: Special middleware for debugging
- **Interactive Debugger**: Integration with Python debugger
- **Request Tracking**: End-to-end request tracing

## Extensibility

### Plugin Architecture

Crawlo follows a plugin architecture that allows easy extension:

- **Middleware Plugins**: Request/response processing
- **Pipeline Plugins**: Item processing
- **Extension Plugins**: Additional functionality
- **Downloader Plugins**: HTTP client implementations

### Custom Component Development

Developers can create custom components by:

1. **Inheriting Base Classes**: Extending framework base classes
2. **Implementing Interfaces**: Following defined interfaces
3. **Configuration Integration**: Making components configurable
4. **Testing**: Providing comprehensive test coverage

This architecture enables Crawlo to be both powerful and flexible, supporting a wide range of crawling scenarios while maintaining high performance and reliability.