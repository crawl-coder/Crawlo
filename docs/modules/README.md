# Module Documentation

This directory contains the modular documentation for the Crawlo framework, organized by core components. Each module has its own subdirectory with detailed documentation about its functionality, configuration, and usage.

## Documentation Structure

The documentation is organized into the following modules:

### Core Module
- [Engine](core/engine.md) - The central coordinator that manages the crawling lifecycle
- [Scheduler](core/scheduler.md) - Manages request queues and deduplication
- [Processor](core/processor.md) - Handles response processing and item extraction

### Downloader Module
- [Overview](downloader/index.md) - Introduction to the downloader system
- [AioHttpDownloader](downloader/aiohttp.md) - High-performance downloader based on aiohttp
- [HttpXDownloader](downloader/httpx.md) - HTTP/2 support with httpx
- [CurlCffiDownloader](downloader/curl_cffi.md) - Browser fingerprint simulation

### Middleware Module
- [Overview](middleware/index.md) - Introduction to the middleware system
- [MiddlewareManager](middleware/manager.md) - Core middleware management system
- [Built-in Middlewares](middleware/built_in.md) - Overview of built-in middleware components

### Pipeline Module
- [Overview](pipeline/index.md) - Introduction to the pipeline system
- [PipelineManager](pipeline/manager.md) - Core pipeline management system
- [Built-in Pipelines](pipeline/built_in.md) - Overview of built-in pipeline components

### Queue Module
- [Overview](queue/index.md) - Introduction to the queue system
- [QueueManager](queue/manager.md) - Unified queue management system
- [Memory Queue](queue/memory.md) - In-memory queue implementation
- [Redis Queue](queue/redis.md) - Distributed Redis-based queue

### Filter Module
- [Overview](filter/index.md) - Introduction to the filter system
- [BaseFilter](filter/base.md) - Base filter class and interface
- [MemoryFilter](filter/memory.md) - In-memory deduplication
- [AioRedisFilter](filter/redis.md) - Distributed Redis-based deduplication

### Extension Module
- [Overview](extension/index.md) - Introduction to the extension system
- [ExtensionManager](extension/manager.md) - Core extension management system
- [Built-in Extensions](extension/built_in.md) - Overview of built-in extension components

## How to Use This Documentation

1. **Start with the Overview**: Each module directory contains an index.md file that provides an overview of that module's functionality.

2. **Dive into Specific Components**: Follow the links to detailed documentation for specific components within each module.

3. **Check Configuration Options**: Most documentation pages include information about configuration options and settings.

4. **Look at Examples**: Many pages include code examples showing how to use the components.

5. **Refer to API Documentation**: For detailed method and class documentation, refer to the API reference section.

## Contributing to Documentation

If you'd like to contribute to this documentation:

1. Follow the existing structure and formatting
2. Use clear, concise language
3. Include code examples where appropriate
4. Update the navigation in mkdocs.yml when adding new pages
5. Test your changes by building the documentation locally

## Getting Help

If you have questions about the documentation or need help with Crawlo:

1. Check the [main documentation](../index.md) for general information
2. Look at the [API reference](../api/) for detailed technical information
3. File an issue on the GitHub repository if you find errors or omissions