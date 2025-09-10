# Crawlo Quick Start Guide

This guide will help you get started with Crawlo, a modern asynchronous web scraping framework.

## Prerequisites

- Python 3.10 or higher
- Basic knowledge of Python and web scraping concepts

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/crawl-coder/Crawlo.git
   cd crawlo
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

## Creating Your First Project

1. Create a new project:
   ```bash
   crawlo startproject my_first_project
   cd my_first_project
   ```

2. Generate a spider:
   ```bash
   crawlo genspider my_spider example.com
   ```

3. Edit the spider in `my_first_project/spiders/my_spider.py`:
   ```python
   from crawlo import Spider, Request
   from my_first_project.items import MyItem

   class MySpider(Spider):
       name = "my_spider"
       start_urls = ["https://example.com"]

       def parse(self, response):
           # Extract data
           item = MyItem()
           item['title'] = response.css('title::text').get()
           yield item

           # Follow links
           for link in response.css('a::attr(href)').getall():
               yield Request(url=response.urljoin(link), callback=self.parse)
   ```

4. Run the spider:
   ```bash
   python run.py my_spider
   ```

## Distributed Crawling

To run your spider in distributed mode:

1. Start Redis:
   ```bash
   redis-server
   ```

2. Run the spider in distributed mode:
   ```bash
   python run.py my_spider --distributed
   ```

3. Run additional nodes on other machines:
   ```bash
   python run.py my_spider --distributed --redis-host YOUR_REDIS_HOST
   ```

## Configuration

Customize your project by editing `settings.py`:

```python
# Increase concurrency
CONCURRENCY = 16

# Add delays between requests
DOWNLOAD_DELAY = 1.0

# Enable pipelines
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

## Next Steps

- Read the full [Crawlo Framework Documentation](crawlo_framework_documentation.md)
- Explore the [examples](../examples/) directory for more complex use cases
- Check out the [API Reference](api_reference.md) for detailed information on all classes and methods