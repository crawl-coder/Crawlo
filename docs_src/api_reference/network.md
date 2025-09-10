# Network API Reference

This document provides detailed information about the network-related components in the Crawlo framework, including requests, responses, and downloaders.

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

#### Attributes

##### `url`
The URL of the request.

##### `method`
The HTTP method of the request.

##### `headers`
The HTTP headers of the request.

##### `body`
The body of the request.

##### `cookies`
The cookies to send with the request.

##### `meta`
Metadata for the request.

##### `encoding`
The encoding of the request.

##### `priority`
The priority of the request.

##### `dont_filter`
Whether to filter the request.

##### `errback`
The error callback function.

##### `flags`
Flags for the request.

#### Methods

##### `copy(self)`
Create a copy of the request.

**Returns:**
- `Request`: A copy of the request.

##### `replace(self, *args, **kwargs)`
Create a new Request object with the same attributes, except for those given new values.

**Parameters:**
- `*args`: Positional arguments to pass to the Request constructor.
- `**kwargs`: Keyword arguments to update in the new Request.

**Returns:**
- `Request`: A new Request object.

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

#### Attributes

##### `url`
The URL of the response.

##### `status`
The HTTP status code of the response.

##### `headers`
The HTTP headers of the response.

##### `body`
The body of the response.

##### `flags`
Flags for the response.

##### `request`
The request that generated this response.

##### `encoding`
The encoding of the response.

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

##### `text(self)`
Get the response body as text.

**Returns:**
- `str`: The response body as text.

##### `copy(self)`
Create a copy of the response.

**Returns:**
- `Response`: A copy of the response.

##### `replace(self, *args, **kwargs)`
Create a new Response object with the same attributes, except for those given new values.

**Parameters:**
- `*args`: Positional arguments to pass to the Response constructor.
- `**kwargs`: Keyword arguments to update in the new Response.

**Returns:**
- `Response`: A new Response object.

## Downloader Classes

Crawlo provides multiple downloader implementations for different use cases.

### Class: AioHttpDownloader

An asynchronous HTTP downloader based on aiohttp.

```python
class AioHttpDownloader(BaseDownloader):
    def __init__(self, settings):
        # Initialize the downloader with settings
        pass
    
    async def download(self, request):
        # Download a request
        pass
```

#### Methods

##### `__init__(self, settings)`
Initialize the downloader with settings.

**Parameters:**
- `settings` (Settings): The settings for the downloader.

##### `download(self, request)`
Download a request asynchronously.

**Parameters:**
- `request` (Request): The request to download.

**Returns:**
- `Coroutine`: A coroutine that resolves to a Response object.

### Class: HttpXDownloader

An HTTP downloader based on httpx with HTTP/2 support.

```python
class HttpXDownloader(BaseDownloader):
    def __init__(self, settings):
        # Initialize the downloader with settings
        pass
    
    async def download(self, request):
        # Download a request
        pass
```

#### Methods

##### `__init__(self, settings)`
Initialize the downloader with settings.

**Parameters:**
- `settings` (Settings): The settings for the downloader.

##### `download(self, request)`
Download a request asynchronously.

**Parameters:**
- `request` (Request): The request to download.

**Returns:**
- `Coroutine`: A coroutine that resolves to a Response object.

### Class: CurlCffiDownloader

An HTTP downloader based on curl-cffi with browser fingerprinting capabilities.

```python
class CurlCffiDownloader(BaseDownloader):
    def __init__(self, settings):
        # Initialize the downloader with settings
        pass
    
    async def download(self, request):
        # Download a request
        pass
```

#### Methods

##### `__init__(self, settings)`
Initialize the downloader with settings.

**Parameters:**
- `settings` (Settings): The settings for the downloader.

##### `download(self, request)`
Download a request asynchronously.

**Parameters:**
- `request` (Request): The request to download.

**Returns:**
- `Coroutine`: A coroutine that resolves to a Response object.

## Selector Classes

Crawlo uses Parsel for data extraction, providing CSS and XPath selectors.

### Class: Selector

A selector for extracting data from HTML/XML documents.

```python
class Selector(object):
    def __init__(self, text=None, type=None, namespaces=None, root=None, 
                 base_url=None, _expr=None, features=None):
        # Initialize the selector
        pass
```

#### Methods

##### `css(self, query)`
Apply the given CSS selector.

**Parameters:**
- `query` (str): The CSS selector to apply.

**Returns:**
- `SelectorList`: A list of Selector objects.

##### `xpath(self, query)`
Apply the given XPath query.

**Parameters:**
- `query` (str): The XPath query to apply.

**Returns:**
- `SelectorList`: A list of Selector objects.

##### `extract(self)`
Extract the text content of the selector.

**Returns:**
- `str`: The text content.

##### `get(self)`
Get the first element or None if no elements exist.

**Returns:**
- `str` or `None`: The text content of the first element or None.

##### `getall(self)`
Get all elements as a list.

**Returns:**
- `list`: A list of text contents.

### Class: SelectorList

A list-like object that contains multiple Selector objects.

```python
class SelectorList(object):
    def __init__(self, selectorlist):
        # Initialize the selector list
        pass
```

#### Methods

##### `css(self, query)`
Apply the given CSS selector to all selectors in the list.

**Parameters:**
- `query` (str): The CSS selector to apply.

**Returns:**
- `SelectorList`: A new SelectorList with the results.

##### `xpath(self, query)`
Apply the given XPath query to all selectors in the list.

**Parameters:**
- `query` (str): The XPath query to apply.

**Returns:**
- `SelectorList`: A new SelectorList with the results.

##### `extract(self)`
Extract the text content of all selectors in the list.

**Returns:**
- `list`: A list of text contents.

##### `get(self)`
Get the first element or None if no elements exist.

**Returns:**
- `str` or `None`: The text content of the first element or None.

##### `getall(self)`
Get all elements as a list.

**Returns:**
- `list`: A list of text contents.

## Example Usage

```python
from crawlo import Spider, Request
from crawlo.network.response import Response

class MySpider(Spider):
    name = "example"
    
    def start_requests(self):
        yield Request(
            url="https://httpbin.org/get",
            callback=self.parse,
            headers={"User-Agent": "Crawlo/1.0"},
            meta={"custom_data": "value"}
        )
    
    def parse(self, response: Response):
        # Extract data using CSS selectors
        title = response.css('title::text').get()
        
        # Extract data using XPath
        links = response.xpath('//a/@href').getall()
        
        # Parse JSON response
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            
        # Yield items or new requests
        yield {"title": title, "links": links}
```