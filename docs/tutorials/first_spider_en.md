# Creating Your First Spider

This tutorial will guide you through creating your first Crawlo spider, from installation to running the complete process.

## Environment Setup

### Install Python
Make sure your system has Python 3.7 or higher installed:

```bash
python --version
```

### Install Crawlo
Install Crawlo using pip:

```bash
pip install crawlo
```

## Create a Project

Use the Crawlo command-line tool to create a new project:

```bash
crawlo startproject my_first_spider
cd my_first_spider
```

This will create the following project structure:

```
my_first_spider/
├── settings.py          # Project configuration file
├── spiders/             # Spider directory
│   ├── __init__.py
│   └── example.py       # Example spider
├── pipelines/           # Data pipeline directory
│   └── __init__.py
├── middlewares/         # Middleware directory
│   └── __init__.py
└── items/               # Data item definition directory
    └── __init__.py
```

## Write a Spider

Edit the `spiders/example.py` file to create your first spider:

```python
from crawlo import Spider

class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['http://httpbin.org/get']
    
    def parse(self, response):
        # Extract page information
        yield {
            'url': response.url,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'text': response.text[:100] + '...' if len(response.text) > 100 else response.text
        }
```

## Run the Spider

Run the spider in the project directory:

```bash
crawlo run example
```

You will see output similar to the following:

```
2023-01-01 12:00:00 [crawlo] INFO: Spider opened: example
2023-01-01 12:00:01 [crawlo] INFO: Received response: 200 http://httpbin.org/get
2023-01-01 12:00:01 [crawlo] INFO: Spider closed: example
```

## Advanced Example

Let's create a more complex spider to crawl news website titles and links:

```python
from crawlo import Spider

class NewsSpider(Spider):
    name = 'news'
    start_urls = ['https://news.ycombinator.com/']
    
    def parse(self, response):
        # Extract news titles and links
        for item in response.css('.storylink'):
            yield {
                'title': item.css('::text').get(),
                'url': item.css('::attr(href)').get()
            }
        
        # Follow next page link
        next_page = response.css('.morelink::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

## Configure the Spider

You can configure spider behavior through the `settings.py` file:

```python
# settings.py
CONCURRENCY = 10           # Concurrent requests
DOWNLOAD_DELAY = 1.0       # Download delay (seconds)
DOWNLOAD_TIMEOUT = 30      # Download timeout (seconds)
DOWNLOADER_TYPE = 'httpx'  # Downloader type

# Custom request headers
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Crawlo/1.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
```

## Use Pipelines to Process Data

Create a simple pipeline to process crawled data:

```python
# pipelines.py
class JsonWriterPipeline:
    def open_spider(self, spider):
        self.file = open('items.json', 'w')
    
    def close_spider(self, spider):
        self.file.close()
    
    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
        return item
```

Enable the pipeline in `settings.py`:

```python
# settings.py
PIPELINES = {
    'my_first_spider.pipelines.JsonWriterPipeline': 300,
}
```

## Use Middleware

Create a simple middleware to handle requests and responses:

```python
# middlewares.py
class UserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers['User-Agent'] = 'MyBot/1.0'
        return request
```

Enable the middleware in `settings.py`:

```python
# settings.py
MIDDLEWARES = {
    'my_first_spider.middlewares.UserAgentMiddleware': 400,
}
```

## Run Spider with Parameters

```bash
# Set log level
crawlo run example --log-level DEBUG

# Specify configuration file
crawlo run example --config settings.py

# Set concurrency
crawlo run example --concurrency 20
```

## View Statistics

After running, view spider statistics:

```bash
crawlo stats example
```

## Next Steps

- Learn more about [Downloaders](../modules/downloader/index_en.md)
- Explore [Middleware](../modules/middleware/index_en.md) functionality
- Master [Pipelines](../modules/pipeline/index_en.md) usage
- Learn about [Distributed Deployment](../modules/advanced/distributed_en.md)