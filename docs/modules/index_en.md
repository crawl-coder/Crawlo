# Modular Documentation

Welcome to the modular documentation for the Crawlo framework. This section provides detailed, organized documentation for each core component of the framework.

## Why Modular Documentation?

The modular documentation approach organizes information by functional components, making it easier for you to:

- Understand the role of each component in the framework
- Find specific information about individual modules
- Learn how components interact with each other
- Configure and customize each module independently

## Available Modules

Each module documentation section includes:

- **Overview**: Introduction to the module's purpose and functionality
- **Components**: Detailed documentation for each component within the module
- **Configuration**: Settings and options for customizing the module
- **Usage Examples**: Code examples demonstrating how to use the module
- **API Reference**: Detailed technical documentation for classes and methods

### Core Components

- [Core Module](core/index_en.md) - The heart of Crawlo, containing the engine, scheduler, and processor
  - [Engine](core/engine_en.md) - The core engine that orchestrates the crawling process
  - [Scheduler](core/scheduler_en.md) - Manages request queues and deduplication
  - [Processor](core/processor_en.md) - Handles response processing and item extraction
  - [startproject Command](core/cli_startproject_en.md) - Project initialization command
- [Downloader Module](downloader/index_en.md) - HTTP client implementations for fetching content
- [Middleware Module](middleware/index_en.md) - Request/response processing components
- [Pipeline Module](pipeline/index_en.md) - Data processing and storage components
- [Queue Module](queue/index_en.md) - Request queue management for standalone and distributed crawling
- [Filter Module](filter/index_en.md) - Request deduplication functionality
- [Extension Module](extension/index_en.md) - Additional features and monitoring components
- [CLI Tools Reference](cli-tools-reference_en.md) - Command-line tools usage guide

## How to Navigate

1. **Start with Core**: If you're new to Crawlo, start with the [Core Module](core/index_en.md) documentation
2. **Follow Your Interests**: Jump to the modules that interest you most
3. **Check Examples**: Look for code examples on each documentation page
4. **Refer to Configuration**: Learn how to configure each module for your specific needs

## Getting Started Guide

If you're just getting started with Crawlo, we recommend reading in the following order:

1. [Core Module](core/index_en.md) - Understand the basic architecture
2. [Downloader Module](downloader/index_en.md) - Learn how to fetch web content
3. [Middleware Module](middleware/index_en.md) - Explore request/response processing
4. [Pipeline Module](pipeline/index_en.md) - Learn how to process and store data
5. Other modules as needed for your specific use case

## Feedback and Contributions

We welcome feedback on this documentation and encourage contributions. If you find errors, omissions, or have suggestions for improvement, please:

1. Submit an issue on our GitHub repository
2. Submit a pull request with improvements
3. Contact the development team with questions or feedback