# Tools Package

The Crawlo framework provides a comprehensive tools package that encapsulates various utilities commonly used in web scraping scenarios. This package includes date processing, data cleaning, data validation, request handling, anti-crawler measures, and distributed coordination tools.

## Package Structure

The tools package contains the following modules:

1. **Date Tools** - Date parsing and formatting utilities
2. **Data Cleaning Tools** - Text cleaning, data extraction, and formatting utilities
3. **Data Validation Tools** - Data validation utilities for common formats
4. **Request Handling Tools** - URL building and request preparation utilities
5. **Anti-Crawler Tools** - Tools to handle anti-crawling mechanisms
6. **Distributed Coordinator Tools** - Tools for distributed crawling coordination

## Usage

### Importing Tools

```python
from crawlo.tools import (
    # Date tools
    TimeUtils,
    parse_time,
    format_time,
    time_diff,
    
    # Data cleaning tools
    TextCleaner,
    DataFormatter,
    clean_text,
    format_currency,
    extract_emails,
    
    # Data validation tools
    DataValidator,
    validate_email,
    validate_url,
    validate_phone,
    
    # Request handling tools
    RequestHandler,
    build_url,
    add_query_params,
    merge_headers,
    
    # Anti-crawler tools
    AntiCrawler,
    get_random_user_agent,
    rotate_proxy,
    
    # Distributed coordinator tools
    DistributedCoordinator,
    generate_task_id,
    get_cluster_info
)
```

### Date Tools

```python
from crawlo.tools import parse_time, format_time, time_diff

# Parse time
time_str = "2025-09-10 14:30:00"
parsed_time = parse_time(time_str)

# Format time
formatted_time = format_time(parsed_time, "%Y-%m-%d")

# Calculate time difference
time_str2 = "2025-09-11 14:30:00"
parsed_time2 = parse_time(time_str2)
diff = time_diff(parsed_time2, parsed_time)  # Returns difference in seconds
```

### Data Cleaning Tools

```python
from crawlo.tools import clean_text, format_currency, extract_emails

# Clean text
dirty_text = "<p>This is a&nbsp;<b>test</b>&amp;text</p>"
clean_result = clean_text(dirty_text)

# Format currency
price = 1234.567
formatted_price = format_currency(price, "$", 2)

# Extract emails
text_with_email = "Contact: test@example.com"
emails = extract_emails(text_with_email)
```

### Data Validation Tools

```python
from crawlo.tools import validate_email, validate_url, validate_phone

# Validate email
is_valid = validate_email("test@example.com")

# Validate URL
is_valid = validate_url("https://example.com")

# Validate phone
is_valid = validate_phone("13812345678")
```

### Request Handling Tools

```python
from crawlo.tools import build_url, add_query_params, merge_headers

# Build URL
base_url = "https://api.example.com"
path = "/v1/users"
query_params = {"page": 1, "limit": 10}
full_url = build_url(base_url, path, query_params)

# Add query parameters
existing_url = "https://api.example.com/v1/users?page=1"
new_params = {"sort": "name"}
updated_url = add_query_params(existing_url, new_params)

# Merge headers
base_headers = {"Content-Type": "application/json"}
additional_headers = {"Authorization": "Bearer token123"}
merged_headers = merge_headers(base_headers, additional_headers)
```

### Anti-Crawler Tools

```python
from crawlo.tools import get_random_user_agent, rotate_proxy

# Get random User-Agent
user_agent = get_random_user_agent()

# Rotate proxy
proxy = rotate_proxy()
```

### Distributed Coordinator Tools

```python
from crawlo.tools import generate_task_id, get_cluster_info

# Generate task ID
task_id = generate_task_id("https://example.com", "example_spider")

# Get cluster info
cluster_info = get_cluster_info()
```

## In Spider Usage

```python
from crawlo import Spider, Request
from crawlo.tools import (
    clean_text, 
    validate_email, 
    get_random_user_agent,
    build_url
)

class ExampleSpider(Spider):
    def start_requests(self):
        headers = {"User-Agent": get_random_user_agent()}
        yield Request("https://example.com", headers=headers)
    
    def parse(self, response):
        # Extract data
        title = response.css('h1::text').get()
        email = response.css('.email::text').get()
        
        # Clean and validate data
        clean_title = clean_text(title) if title else None
        is_valid_email = validate_email(email) if email else False
        
        # Build next page URL
        next_page_url = build_url("https://example.com", "/page/2")
        
        # Process data...
```

## Module APIs

### Date Tools
- `parse_time()`: Parse time string to datetime object
- `format_time()`: Format datetime object to string
- `time_diff()`: Calculate time difference in seconds

### Data Cleaning Tools
- `TextCleaner`: Text cleaning utilities
- `DataFormatter`: Data formatting utilities
- `clean_text()`: Clean HTML tags and entities from text
- `format_currency()`: Format number as currency
- `extract_emails()`: Extract email addresses from text

### Data Validation Tools
- `DataValidator`: Data validation utilities
- `validate_email()`: Validate email address format
- `validate_url()`: Validate URL format
- `validate_phone()`: Validate phone number format

### Request Handling Tools
- `RequestHandler`: Request handling utilities
- `build_url()`: Build complete URL
- `add_query_params()`: Add query parameters to URL
- `merge_headers()`: Merge HTTP headers

### Anti-Crawler Tools
- `AntiCrawler`: Anti-crawler utilities
- `get_random_user_agent()`: Get random User-Agent string
- `rotate_proxy()`: Rotate proxy settings

### Distributed Coordinator Tools
- `DistributedCoordinator`: Distributed coordination utilities
- `generate_task_id()`: Generate unique task ID
- `get_cluster_info()`: Get cluster information

This tools package makes it easy to handle common tasks in web scraping projects, providing reliable and reusable utilities for various scenarios.