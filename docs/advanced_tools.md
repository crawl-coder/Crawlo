# Advanced Tools

The Crawlo framework provides a comprehensive set of advanced tools to handle common challenges in web scraping scenarios. These tools include data processing, request handling, anti-crawling measures, and distributed coordination utilities.

## Tool Categories

### 1. Data Processing Tools

#### Data Cleaning Tools
- HTML tag remover: Automatically remove HTML tags and extract plain text
- Data formatting tools: Unify date, number, currency formats
- Encoding conversion tools: Handle data with different character encodings

#### Data Validation Tools
- Field validators: Validate common field formats like email, phone, ID card
- Data integrity checks: Ensure key fields are not empty

### 2. Request Handling Tools

#### Retry Mechanism
- Smart retry: Decide whether to retry based on HTTP status codes and exception types
- Exponential backoff: Automatically increase retry intervals

### 3. Anti-Crawling Tools

#### IP Proxy Tools
- Proxy pool management: Automatically switch proxy IPs
- Proxy validity detection: Regularly check if proxies are available

#### Captcha Handling Tools
- Captcha recognition interface: Integrate third-party captcha recognition services
- Manual captcha handling: Provide interfaces for manual captcha input

### 4. Distributed Coordination Tools

#### Task Distribution Tools
- Pagination task generator: Automatically distribute large numbers of pages to different nodes
- Task progress tracking: Monitor task execution status of each node in real-time

#### Data Deduplication Tools
- Multi-level deduplication: Combine Bloom filters and precise deduplication
- Deduplication strategy configuration: Choose deduplication strategies based on different data types

## Usage Examples

### Data Processing Tools

```python
from crawlo.tools import clean_text, format_currency, validate_email, check_data_integrity

# Data cleaning
dirty_text = "<p>This is a&nbsp;<b>test</b>&amp;text</p>"
clean_result = clean_text(dirty_text)

# Data formatting
price = 1234.567
formatted_price = format_currency(price, "$", 2)

# Field validation
email = "test@example.com"
is_valid_email = validate_email(email)

# Data integrity check
data = {
    "name": "John Doe",
    "email": "test@example.com",
    "phone": "13812345678"
}
required_fields = ["name", "email", "phone", "address"]
integrity_result = check_data_integrity(data, required_fields)
```

### Retry Mechanism

```python
from crawlo.tools import retry, exponential_backoff

# Exponential backoff
for attempt in range(5):
    delay = exponential_backoff(attempt)
    print(f"Retry {attempt}: Delay {delay:.2f} seconds")

# Retry decorator
@retry(max_retries=3)
def unreliable_function():
    import random
    if random.random() < 0.7:  # 70% failure rate
        raise ConnectionError("Network connection failed")
    return "Successfully executed"
```

### Anti-Crawling Tools

```python
from crawlo.tools import AntiCrawler, rotate_proxy, handle_captcha, detect_rate_limiting

# Anti-crawling tools
anti_crawler = AntiCrawler()

# Get random User-Agent
user_agent = anti_crawler.get_random_user_agent()

# Rotate proxy
proxy = anti_crawler.rotate_proxy()

# Detect captcha
response_with_captcha = "Please enter the verification code"
has_captcha = anti_crawler.handle_captcha(response_with_captcha)

# Detect rate limiting
status_code = 429  # Too Many Requests
response_headers = {"Retry-After": "60"}
is_rate_limited = anti_crawler.detect_rate_limiting(status_code, response_headers)
```

### Distributed Coordination Tools

```python
from crawlo.tools import generate_pagination_tasks, distribute_tasks, DistributedCoordinator

# Generate pagination tasks
base_url = "https://example.com/products"
pagination_tasks = generate_pagination_tasks(base_url, 1, 100)

# Task distribution
tasks = list(range(1, 21))  # 20 tasks
distributed = distribute_tasks(tasks, 4)  # Distribute to 4 worker nodes

# Distributed coordinator
coordinator = DistributedCoordinator()
cluster_info = coordinator.get_cluster_info()
```

## In Spider Usage

```python
import asyncio
from crawlo import Spider, Request
from crawlo.tools import (
    clean_text,
    validate_email,
    AntiCrawler,
    DistributedCoordinator,
    retry
)

class AdvancedSpider(Spider):
    def __init__(self):
        super().__init__()
        self.anti_crawler = AntiCrawler()
        self.coordinator = DistributedCoordinator()
        
    def start_requests(self):
        # Generate pagination tasks
        base_url = "https://api.example.com/products"
        pagination_tasks = self.coordinator.generate_pagination_tasks(base_url, 1, 100)
        
        for url in pagination_tasks:
            yield Request(url)
    
    @retry(max_retries=3)
    async def parse(self, response):
        # Check if captcha is encountered
        if self.anti_crawler.handle_captcha(response.text):
            # Handle captcha logic
            print("Captcha encountered, need to handle")
            return
            
        # Extract data
        products = response.css('.product-item')
        for product in products:
            name = product.css('.product-name::text').get()
            price_text = product.css('.price::text').get()
            email = product.css('.contact-email::text').get()
            
            # Data cleaning and validation
            clean_name = clean_text(name) if name else None
            clean_price = clean_text(price_text) if price_text else None
            is_valid_email = validate_email(email) if email else False
            
            # Check if data is duplicate
            if not await self.coordinator.is_duplicate({"name": clean_name, "price": clean_price}):
                # Add to deduplication set
                await self.coordinator.add_to_dedup({"name": clean_name, "price": clean_price})
                
                # Process product data...
                pass
```

These advanced tools make it easy to handle complex scenarios in web scraping projects, providing reliable and reusable utilities for various challenges.