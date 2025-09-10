# Spider API Reference

This document provides detailed information about the Spider class and related components in the Crawlo framework.

## Spider Class

The Spider is the base class for all crawlers in Crawlo. It defines how to crawl and parse a particular website or set of websites.

### Class: Spider

```python
class Spider(object):
    name = None
    allowed_domains = []
    start_urls = []
    custom_settings = {}
    
    def __init__(self, name=None, **kwargs):
        # Initialize the spider
        pass
    
    def start_requests(self):
        # Generate initial requests
        pass
    
    def parse(self, response):
        # Parse responses and extract data
        pass
    
    def closed(self, reason):
        # Called when the spider closes
        pass
```

#### Attributes

##### `name`
A string that uniquely identifies the spider. This attribute is required.

##### `allowed_domains`
A list of domains that the spider is allowed to crawl. Requests to URLs outside these domains will be filtered out.

##### `start_urls`
A list of URLs where the spider will begin crawling.

##### `custom_settings`
A dictionary of settings that override the project settings for this specific spider.

#### Methods

##### `__init__(self, name=None, **kwargs)`
Initialize the spider with an optional name and additional keyword arguments.

**Parameters:**
- `name` (str, optional): The name of the spider.
- `**kwargs`: Additional keyword arguments passed to the spider.

##### `start_requests(self)`
This method must return an iterable of Request objects that the spider will begin crawling with.

**Returns:**
- `iterable`: An iterable of Request objects.

##### `parse(self, response)`
This method is called for each response that the spider downloads. It should parse the response data and return extracted items or new requests.

**Parameters:**
- `response` (Response): The response object to parse.

**Returns:**
- `iterable`: An iterable of Item objects or Request objects.

##### `closed(self, reason)`
This method is called when the spider closes.

**Parameters:**
- `reason` (str): The reason why the spider was closed.

## Request Class

The Request class represents an HTTP request to be downloaded.

### Class: Request

```python
class Request(object):
    def __init__(self, url, callback=None, method='GET', headers=None, 
                 body=None, cookies=None, meta=None, encoding='utf-8',
                 priority=0, dont_filter=False, errback=None, flags=None):
        # Initialize the request
        pass
```

#### Parameters

- `url` (str): The URL of the request.
- `callback` (callable, optional): The function that will be called with the response.
- `method` (str, optional): The HTTP method. Defaults to 'GET'.
- `headers` (dict, optional): The HTTP headers for the request.
- `body` (bytes, optional): The request body.
- `cookies` (dict, optional): The cookies to send with the request.
- `meta` (dict, optional): Metadata for the request that will be accessible in the response.
- `encoding` (str, optional): The encoding of the request. Defaults to 'utf-8'.
- `priority` (int, optional): The priority of the request. Higher priority requests are processed first.
- `dont_filter` (bool, optional): If True, the request won't be filtered by the scheduler.
- `errback` (callable, optional): The function that will be called if there's an error processing the request.
- `flags` (list, optional): Flags for the request.

## Response Class

The Response class represents an HTTP response.

### Class: Response

```python
class Response(object):
    def __init__(self, url, status=200, headers=None, body=b'', flags=None, 
                 request=None, encoding='utf-8'):
        # Initialize the response
        pass
```

#### Parameters

- `url` (str): The URL of the response.
- `status` (int, optional): The HTTP status code. Defaults to 200.
- `headers` (dict, optional): The HTTP headers of the response.
- `body` (bytes, optional): The response body.
- `flags` (list, optional): Flags for the response.
- `request` (Request, optional): The request that generated this response.
- `encoding` (str, optional): The encoding of the response. Defaults to 'utf-8'.

#### Methods

##### `css(self, query)`
Apply the given CSS selector and return a list of Selector objects.

**Parameters:**
- `query` (str): The CSS selector to apply.

**Returns:**
- `list`: A list of Selector objects.

##### `xpath(self, query)`
Apply the given XPath query and return a list of Selector objects.

**Parameters:**
- `query` (str): The XPath query to apply.

**Returns:**
- `list`: A list of Selector objects.

##### `json(self)`
Parse the response body as JSON.

**Returns:**
- `dict` or `list`: The parsed JSON data.

## Item Class

The Item class is a container for scraped data.

### Class: Item

```python
class Item(dict):
    def __init__(self, *args, **kwargs):
        # Initialize the item
        pass
```

#### Methods

##### `__init__(self, *args, **kwargs)`
Initialize the item with optional initial data.

**Parameters:**
- `*args`: Positional arguments passed to the dict constructor.
- `**kwargs`: Keyword arguments that become item fields.

## Field Class

The Field class is used to define item fields with metadata.

### Class: Field

```python
class Field(dict):
    def __init__(self, *args, **kwargs):
        # Initialize the field
        pass
```

#### Methods

##### `__init__(self, *args, **kwargs)`
Initialize the field with optional metadata.

**Parameters:**
- `*args`: Positional arguments passed to the dict constructor.
- `**kwargs`: Keyword arguments that become field metadata.

## Example Usage

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