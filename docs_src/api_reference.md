# Crawlo API Reference

This document provides detailed information about the core classes and methods in the Crawlo framework.

## Core Classes

### Spider

The base class for all spiders.

#### Attributes

- `name` (str): Unique identifier for the spider. Required.
- `allowed_domains` (list): List of domains the spider is allowed to crawl.
- `start_urls` (list): List of URLs where the spider will begin crawling.
- `custom_settings` (dict): Dictionary of settings that override project settings.

#### Methods

- `start_requests()`: Generates initial requests. Override this method to provide custom start requests.
- `parse(response)`: Parses responses and extracts data. Must be implemented by subclasses.

#### Example

```python
from crawlo import Spider, Request

class MySpider(Spider):
    name = "my_spider"
    start_urls = ["https://example.com"]

    def parse(self, response):
        # Extract data from response
        yield {"title": response.css("title::text").get()}
        
        # Follow links
        for link in response.css("a::attr(href)").getall():
            yield Request(url=response.urljoin(link), callback=self.parse)
```

### Item

Base class for scraped items.

#### Field

Represents a field in an item.

##### Parameters

- `description` (str): Description of the field.
- `default` (any): Default value for the field.

#### Example

```python
from crawlo.items import Item, Field

class MyItem(Item):
    title = Field(description="Page title")
    url = Field(description="Page URL", default="")
```

### Request

Represents an HTTP request.

#### Parameters

- `url` (str): URL to request.
- `callback` (callable): Function to call with the response.
- `method` (str): HTTP method (default: "GET").
- `headers` (dict): HTTP headers.
- `body` (str): Request body.
- `meta` (dict): Metadata to pass to the callback.
- `dont_filter` (bool): Whether to skip duplicate filtering.

#### Example

```python
from crawlo import Request

request = Request(
    url="https://example.com",
    callback=self.parse,
    method="POST",
    headers={"Content-Type": "application/json"},
    body='{"key": "value"}',
    meta={"custom_data": "example"}
)
```

### Response

Represents an HTTP response.

#### Attributes

- `url` (str): URL of the response.
- `status_code` (int): HTTP status code.
- `headers` (dict): HTTP headers.
- `body` (bytes): Response body.
- `meta` (dict): Metadata from the request.

#### Methods

- `css(selector)`: Extract data using CSS selectors.
- `xpath(selector)`: Extract data using XPath selectors.
- `json()`: Parse response body as JSON.
- `text`: Get response body as text.

#### Example

```python
def parse(self, response):
    # Extract data with CSS selectors
    title = response.css("title::text").get()
    
    # Extract data with XPath
    links = response.xpath("//a/@href").getall()
    
    # Parse JSON response
    data = response.json()
```

## Configuration

### Settings

Settings can be configured in `settings.py` or through the `custom_settings` attribute in spiders.

#### Core Settings

- `PROJECT_NAME` (str): Name of the project.
- `CONCURRENCY` (int): Number of concurrent requests.
- `DOWNLOAD_DELAY` (float): Delay between requests in seconds.
- `DOWNLOAD_TIMEOUT` (int): Request timeout in seconds.

#### Downloader Settings

- `DOWNLOADER` (str): Full path to downloader class.
- `DOWNLOADER_TYPE` (str): Simplified downloader name ("aiohttp", "httpx", "curl_cffi").
- `VERIFY_SSL` (bool): Whether to verify SSL certificates.
- `USE_SESSION` (bool): Whether to use session for requests.

#### Pipeline Settings

- `PIPELINES` (list): List of pipeline classes to use.

#### Middleware Settings

- `MIDDLEWARES` (list): List of middleware classes to use.

#### Distributed Settings

- `RUN_MODE` (str): "standalone" or "distributed".
- `QUEUE_TYPE` (str): "memory" or "redis".
- `SCHEDULER` (str): Scheduler class for distributed mode.
- `FILTER_CLASS` (str): Filter class for duplicate detection.
- `REDIS_HOST` (str): Redis host.
- `REDIS_PORT` (int): Redis port.
- `REDIS_PASSWORD` (str): Redis password.
- `REDIS_DB` (int): Redis database number.

## Pipelines

### ConsolePipeline

Outputs items to the console.

### JsonPipeline

Saves items to JSON files.

#### Settings

- `JSON_FILE` (str): Path to JSON file.

### CsvPipeline

Saves items to CSV files.

#### Settings

- `CSV_FILE` (str): Path to CSV file.

### AsyncmyMySQLPipeline

Stores items in MySQL database using asyncmy.

#### Settings

- `MYSQL_HOST` (str): MySQL host.
- `MYSQL_PORT` (int): MySQL port.
- `MYSQL_USER` (str): MySQL user.
- `MYSQL_PASSWORD` (str): MySQL password.
- `MYSQL_DB` (str): MySQL database.
- `MYSQL_TABLE` (str): MySQL table.

## Middleware

### RequestIgnoreMiddleware

Filters requests based on custom logic.

### DownloadDelayMiddleware

Adds delays between requests.

### DefaultHeaderMiddleware

Adds default headers to requests.

### ProxyMiddleware

Handles proxy configuration for requests.

### RetryMiddleware

Implements retry logic for failed requests.

#### Settings

- `MAX_RETRY_TIMES` (int): Maximum retry attempts.
- `RETRY_HTTP_CODES` (list): HTTP status codes to retry.

### ResponseCodeMiddleware

Processes response codes and handles errors.

## Utilities

### get_logger

Returns a configured logger.

#### Parameters

- `name` (str): Logger name.

#### Example

```python
from crawlo.utils.log import get_logger

logger = get_logger(__name__)
logger.info("This is a log message")
```

### request_fingerprint

Generates a fingerprint for a request to detect duplicates.

#### Parameters

- `request` (Request): Request to fingerprint.

#### Example

```python
from crawlo.utils.request import request_fingerprint

fp = request_fingerprint(request)
```