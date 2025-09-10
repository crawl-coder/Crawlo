# Crawlo API Reference

## Table of Contents
- [Core Components](#core-components)
- [Network](#network)
- [Downloader](#downloader)
- [Middleware](#middleware)
- [Tools](#tools)
- [Utils](#utils)

## Core Components

### Spider
The base class for all spiders.

#### Methods
- `__init__(self, name: str = None, **kwargs)` - Initialize spider
- `start_requests(self) -> Iterator[Request]` - Generate initial requests
- `parse(self, response)` - Parse response (must be implemented)
- `spider_opened(self)` - Called when spider starts
- `spider_closed(self)` - Called when spider ends

#### Properties
- `name: str` - Spider name (required)
- `start_urls: List[str]` - Initial URLs
- `custom_settings: Dict[str, Any]` - Custom settings
- `allowed_domains: List[str]` - Allowed domains

### Request
HTTP request wrapper with rich features.

#### Constructor
```python
Request(
    url: str,
    callback: Optional[Callable] = None,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Union[bytes, str, Dict[Any, Any]]] = None,
    form_data: Optional[Dict[Any, Any]] = None,
    json_body: Optional[Dict[Any, Any]] = None,
    cb_kwargs: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    priority: int = 0,
    dont_filter: bool = False,
    timeout: Optional[float] = None,
    proxy: Optional[str] = None,
    allow_redirects: bool = True,
    auth: Optional[tuple] = None,
    verify: bool = True,
    flags: Optional[List[str]] = None,
    encoding: str = 'utf-8'
)
```

#### Methods
- `copy(self) -> Request` - Create a copy
- `set_meta(self, key: str, value: Any) -> Request` - Set meta data
- `add_header(self, key: str, value: str) -> Request` - Add header
- `add_headers(self, headers: Dict[str, str]) -> Request` - Add multiple headers
- `set_proxy(self, proxy: str) -> Request` - Set proxy
- `set_timeout(self, timeout: float) -> Request` - Set timeout
- `add_flag(self, flag: str) -> Request` - Add flag
- `remove_flag(self, flag: str) -> Request` - Remove flag

#### Properties
- `url: str` - Request URL
- `meta: Dict[str, Any]` - Metadata
- `headers: Dict[str, str]` - Request headers

### Response
HTTP response wrapper.

#### Constructor
```python
Response(
    url: str,
    headers: Dict[str, str],
    status_code: int,
    body: bytes,
    request: Request
)
```

#### Methods
- `css(self, query: str)` - CSS selector
- `xpath(self, query: str)` - XPath selector
- `extract_text(self, query: str, first: bool = True) -> Union[str, List[str]]` - Extract text
- `extract_texts(self, query: str) -> List[str]` - Extract all texts
- `extract_attr(self, query: str, attr: str, first: bool = True) -> Union[str, List[str]]` - Extract attribute
- `extract_attrs(self, query: str, attr: str) -> List[str]` - Extract all attributes

#### Properties
- `url: str` - Response URL
- `headers: Dict[str, str]` - Response headers
- `status_code: int` - HTTP status code
- `body: bytes` - Response body
- `text: str` - Response body as text
- `title: str` - Page title

## Network

### Request Priority Constants
- `RequestPriority.URGENT = -200`
- `RequestPriority.HIGH = -100`
- `RequestPriority.NORMAL = 0`
- `RequestPriority.LOW = 100`
- `RequestPriority.BACKGROUND = 200`

## Downloader

### Supported Downloaders
1. `aiohttp` - High performance async HTTP client
2. `httpx` - Modern async HTTP client with HTTP/2 support
3. `curl_cffi` - curl-based downloader with browser fingerprinting
4. `selenium` - Browser automation for dynamic content
5. `playwright` - High-performance browser automation

### Downloader Configuration
```python
# In settings.py or Spider.custom_settings
custom_settings = {
    'DOWNLOADER_TYPE': 'httpx',  # or 'aiohttp', 'curl_cffi', 'selenium', 'playwright'
    'DOWNLOAD_DELAY': 1,
    'DOWNLOAD_TIMEOUT': 30,
    'CONNECTION_POOL_LIMIT': 100,
}
```

## Middleware

### ProxyMiddleware
Proxy support with automatic rotation.

#### Configuration
```python
# In settings.py
custom_settings = {
    'MIDDLEWARES': [
        'crawlo.middleware.proxy.ProxyMiddleware',
        # ... other middlewares
    ],
    'PROXY_ENABLED': True,
    'PROXY_API_URL': 'https://api.proxyprovider.com/get',
    'PROXY_EXTRACTOR': 'proxy',
    'PROXY_REFRESH_INTERVAL': 60,
}
```

### RetryMiddleware
Automatic retry with exponential backoff.

#### Configuration
```python
custom_settings = {
    'RETRY_TIMES': 3,
    'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
}
```

## Tools

### Date Tools
```python
from crawlo.tools import parse_time, format_time, time_diff

# Parse time
dt = parse_time("2023-01-01 12:00:00")

# Format time
formatted = format_time(dt, "%Y-%m-%d %H:%M:%S")

# Time difference
diff = time_diff(dt2, dt1)  # seconds
```

### Data Cleaning Tools
```python
from crawlo.tools import clean_text, format_currency, extract_emails

# Clean HTML text
clean = clean_text("<p>Hello&nbsp;World</p>")  # "Hello World"

# Format currency
formatted = format_currency(1234.56, "¥", 2)  # "¥1,234.56"

# Extract emails
emails = extract_emails("Contact: test@example.com")  # ["test@example.com"]
```

### Data Validation Tools
```python
from crawlo.tools import validate_email, validate_url, validate_phone

# Validate email
is_valid = validate_email("test@example.com")  # True

# Validate URL
is_valid = validate_url("https://example.com")  # True

# Validate phone
is_valid = validate_phone("13812345678")  # True
```

### Authenticated Proxy Tools
```python
from crawlo.tools import AuthenticatedProxy, create_proxy_config

# Create authenticated proxy
proxy = AuthenticatedProxy("http://username:password@proxy.example.com:8080")

# Get clean URL without auth
clean_url = proxy.clean_url  # "http://proxy.example.com:8080"

# Get authentication credentials
auth = proxy.get_auth_credentials()  # {"username": "username", "password": "password"}

# Get proxy configuration for different downloaders
config = create_proxy_config("http://username:password@proxy.example.com:8080")
aiohttp_config = format_proxy_for_request(config, "aiohttp")
httpx_config = format_proxy_for_request(config, "httpx")
curl_config = format_proxy_for_request(config, "curl_cffi")
```

### Retry Mechanism
```python
from crawlo.tools import retry, exponential_backoff

# Retry decorator
@retry(max_retries=3)
def fetch_data():
    # ... some network operation
    pass

# Exponential backoff
delay = exponential_backoff(attempt_number)  # seconds
```

### Anti-Crawler Tools
```python
from crawlo.tools import AntiCrawler, get_random_user_agent

# Get random user agent
ua = get_random_user_agent()

# Anti-crawler toolkit
anti_crawler = AntiCrawler()
proxy = anti_crawler.rotate_proxy()
has_captcha = anti_crawler.handle_captcha(response_text)
is_rate_limited = anti_crawler.detect_rate_limiting(status_code, headers)
```

### Distributed Coordinator
```python
from crawlo.tools import DistributedCoordinator, generate_pagination_tasks

# Generate pagination tasks
tasks = generate_pagination_tasks("https://api.example.com/items", 1, 100)

# Distributed coordinator
coordinator = DistributedCoordinator()
task_id = coordinator.generate_task_id(url, spider_name)
is_duplicate = await coordinator.is_duplicate(item_data)
```

## Utils

### Logging
```python
from crawlo.utils.log import get_logger

logger = get_logger(__name__)
logger.info("Message")
```

### URL Utilities
```python
from crawlo.utils.url import escape_ajax, add_url_param

# Escape AJAX URLs
escaped = escape_ajax("#!hashbang")

# Add URL parameters
url_with_params = add_url_param("https://example.com", {"key": "value"})
```

### Environment Configuration
```python
from crawlo.utils.env_config import get_runtime_config, get_redis_config

# Get runtime configuration
runtime_config = get_runtime_config()

# Get Redis configuration
redis_config = get_redis_config()
```