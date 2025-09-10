# Standalone Crawler Examples

This document provides examples of standalone crawlers using the Crawlo framework.

## Simple Standalone Crawler

This example demonstrates a basic standalone crawler that extracts data from a website.

### Project Structure

```
simple_standalone/
├── simple_standalone/
│   ├── __init__.py
│   ├── items.py
│   ├── settings.py
│   └── spiders/
│       ├── __init__.py
│       └── quotes.py
├── crawlo.cfg
└── run.py
```

### Items Definition

```python
# simple_standalone/items.py
from crawlo.items import Item, Field

class QuoteItem(Item):
    text = Field(description="Quote text")
    author = Field(description="Author name")
    tags = Field(description="List of tags")
```

### Spider Implementation

```python
# simple_standalone/spiders/quotes.py
from crawlo import Spider, Request
from simple_standalone.items import QuoteItem

class QuotesSpider(Spider):
    name = 'quotes'
    start_urls = ['http://quotes.toscrape.com/']
    
    def parse(self, response):
        # Extract quotes from the page
        for quote in response.css('div.quote'):
            item = QuoteItem()
            item['text'] = quote.css('span.text::text').get()
            item['author'] = quote.css('small.author::text').get()
            item['tags'] = quote.css('div.tags a.tag::text').getall()
            yield item
        
        # Follow pagination links
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield Request(url=response.urljoin(next_page), callback=self.parse)
```

### Settings Configuration

```python
# simple_standalone/settings.py
PROJECT_NAME = 'simple_standalone'
CONCURRENCY = 4
DOWNLOAD_DELAY = 1.0
LOG_LEVEL = 'INFO'

# Use memory-based components for standalone mode
QUEUE_TYPE = 'memory'
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# Pipelines
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

### Running the Crawler

```bash
# Navigate to the project directory
cd simple_standalone

# Run the crawler
python run.py quotes
```

## Advanced Standalone Crawler with Custom Middleware

This example demonstrates a more advanced standalone crawler with custom middleware.

### Custom Middleware

```python
# simple_standalone/middlewares.py
from crawlo.middleware import RequestMiddleware

class CustomHeaderMiddleware(RequestMiddleware):
    async def process_request(self, request, spider):
        request.headers['X-Custom-Header'] = 'Crawlo-Standalone'
        return request
```

### Updated Spider with Custom Parsing

```python
# simple_standalone/spiders/advanced_quotes.py
from crawlo import Spider, Request
from simple_standalone.items import QuoteItem

class AdvancedQuotesSpider(Spider):
    name = 'advanced_quotes'
    start_urls = ['http://quotes.toscrape.com/']
    
    custom_settings = {
        'CONCURRENCY': 8,
        'DOWNLOAD_DELAY': 0.5,
        'MIDDLEWARES': [
            'crawlo.middleware.default_header.DefaultHeaderMiddleware',
            'simple_standalone.middlewares.CustomHeaderMiddleware',
            'crawlo.middleware.retry.RetryMiddleware',
        ]
    }
    
    def parse(self, response):
        # Extract quotes from the page
        for quote in response.css('div.quote'):
            item = QuoteItem()
            item['text'] = quote.css('span.text::text').get()
            item['author'] = quote.css('small.author::text').get()
            item['tags'] = quote.css('div.tags a.tag::text').getall()
            yield item
        
        # Follow pagination links
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield Request(url=response.urljoin(next_page), callback=self.parse)
    
    def parse_author(self, response):
        # Parse author details (if we had links to author pages)
        yield {
            'name': response.css('h3.author-title::text').get(),
            'birthdate': response.css('.author-born-date::text').get(),
        }
```

### Updated Settings

```python
# simple_standalone/settings.py
PROJECT_NAME = 'advanced_standalone'
CONCURRENCY = 8
DOWNLOAD_DELAY = 0.5
LOG_LEVEL = 'DEBUG'

# Use memory-based components for standalone mode
QUEUE_TYPE = 'memory'
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# Middlewares
MIDDLEWARES = [
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'simple_standalone.middlewares.CustomHeaderMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
]

# Pipelines
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    'crawlo.pipelines.csv_pipeline.CsvPipeline',
]
```

## Standalone Crawler with Database Pipeline

This example demonstrates a standalone crawler that stores data in a database.

### Database Pipeline

```python
# simple_standalone/pipelines.py
from crawlo.pipelines import BasePipeline

class DatabasePipeline(BasePipeline):
    def __init__(self, crawler):
        super().__init__(crawler)
        self.connection = None
        self.cursor = None
    
    async def open_spider(self, spider):
        # Connect to database
        import sqlite3
        self.connection = sqlite3.connect('quotes.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                author TEXT,
                tags TEXT
            )
        ''')
        self.connection.commit()
    
    async def process_item(self, item, spider):
        # Insert item into database
        self.cursor.execute('''
            INSERT INTO quotes (text, author, tags)
            VALUES (?, ?, ?)
        ''', (item['text'], item['author'], ','.join(item['tags'])))
        self.connection.commit()
        return item
    
    async def close_spider(self, spider):
        # Close database connection
        if self.connection:
            self.connection.close()
```

### Updated Settings for Database Pipeline

```python
# simple_standalone/settings.py
PROJECT_NAME = 'database_standalone'
CONCURRENCY = 4
DOWNLOAD_DELAY = 1.0
LOG_LEVEL = 'INFO'

# Use memory-based components for standalone mode
QUEUE_TYPE = 'memory'
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# Pipelines
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'simple_standalone.pipelines.DatabasePipeline',
]
```

## Running Examples

### Basic Example

```bash
# Create project
crawlo startproject simple_standalone
cd simple_standalone

# Create spider
crawlo genspider quotes quotes.toscrape.com

# Edit spider, items, and settings as shown above

# Run crawler
python run.py quotes
```

### Advanced Example

```bash
# Run with custom settings
python run.py advanced_quotes --concurrency 16 --delay 0.2

# Run with debug logging
python run.py advanced_quotes --debug
```

## Best Practices for Standalone Crawlers

1. **Resource Management**: Use appropriate concurrency settings for your system
2. **Rate Limiting**: Always respect website robots.txt and implement appropriate delays
3. **Error Handling**: Implement proper error handling and retry mechanisms
4. **Data Storage**: Choose appropriate pipelines for your data storage needs
5. **Logging**: Use appropriate log levels for monitoring crawler progress
6. **Testing**: Test your crawlers with a small dataset before running on large datasets

## Performance Tuning

### Memory Usage Optimization

```python
# settings.py
CONCURRENCY = 4  # Lower concurrency to reduce memory usage
DOWNLOAD_DELAY = 2.0  # Higher delay to reduce request frequency
QUEUE_TYPE = 'memory'  # Use memory queue for standalone mode
```

### Speed Optimization

```python
# settings.py
CONCURRENCY = 16  # Higher concurrency for faster crawling
DOWNLOAD_DELAY = 0.1  # Lower delay for faster requests
CONNECTION_POOL_LIMIT = 50  # Increase connection pool size
```

These examples demonstrate various ways to use Crawlo for standalone crawling, from simple data extraction to more complex scenarios with custom middleware and database storage.