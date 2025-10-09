# PlaywrightDownloader

PlaywrightDownloader is a modern browser automation downloader based on Playwright in the Crawlo framework, offering better performance and a simpler API than Selenium.

## Overview

PlaywrightDownloader is based on Microsoft's Playwright framework, supporting multiple browsers (Chromium, Firefox, WebKit), with faster execution speed and lower resource consumption.

### Core Features

1. **Multi-browser Support** - Supports Chromium, Firefox, WebKit
2. **High Performance** - Faster execution speed than Selenium
3. **Low Resource Consumption** - Consumes fewer resources than Selenium
4. **Modern API** - Clean and easy-to-use API design
5. **Mobile Support** - Supports device emulation and mobile browsers

## Configuration Options

The behavior of PlaywrightDownloader can be adjusted through the following configuration options:

| Configuration Item | Type | Default Value | Description |
|--------------------|------|---------------|-------------|
| PLAYWRIGHT_BROWSER | str | 'chromium' | Browser type (chromium/firefox/webkit) |
| PLAYWRIGHT_HEADLESS | bool | True | Whether to enable headless mode |
| PLAYWRIGHT_VIEWPORT | dict | {'width': 1920, 'height': 1080} | Browser viewport size |
| PLAYWRIGHT_TIMEOUT | int | 30000 | Operation timeout (milliseconds) |
| PLAYWRIGHT_SLOW_MO | int | 0 | Slow motion mode delay (milliseconds) |

## Usage Examples

### Basic Usage

```python
from crawlo.config import CrawloConfig

# Configure to use Playwright downloader
config = CrawloConfig.standalone(
    downloader_type='playwright',
    playwright_browser='chromium',
    playwright_headless=True
)
```

### Advanced Configuration

```python
# Configure browser options
config = CrawloConfig.standalone(
    downloader_type='playwright',
    playwright_browser='firefox',
    playwright_headless=False,
    playwright_viewport={'width': 1366, 'height': 768},
    playwright_timeout=60000
)
```

## Performance Advantages

### Comparison with Selenium

| Feature | Playwright | Selenium |
|---------|------------|----------|
| Startup Time | 1-2 seconds | 5-10 seconds |
| Memory Consumption | Low | High |
| Execution Speed | Fast | Medium |
| API Complexity | Simple | Complex |
| Mobile Support | Native support | Requires additional configuration |

### Resource Management

```python
# Playwright's resource management is more efficient
config = CrawloConfig.standalone(
    downloader_type='playwright',
    concurrency=5,  # Can use higher concurrency
    download_delay=1.0
)
```

## Best Practices

### 1. Browser Selection

```python
# Choose the appropriate browser based on requirements
# Chromium - Best performance, good compatibility
config = CrawloConfig.standalone(playwright_browser='chromium')

# Firefox - Open source choice
config = CrawloConfig.standalone(playwright_browser='firefox')

# WebKit - For Safari compatibility testing
config = CrawloConfig.standalone(playwright_browser='webkit')
```

### 2. Device Emulation

```python
# Mobile device emulation
config = CrawloConfig.standalone(
    playwright_browser='chromium',
    playwright_viewport={
        'width': 375,
        'height': 812,
        'isMobile': True,
        'hasTouch': True
    }
)
```

### 3. Error Handling

```python
# Handle Playwright-related exceptions
def parse_with_playwright(self, response):
    try:
        # Browser operations
        yield self.extract_data(response)
    except TimeoutError as e:
        self.logger.error(f"Operation timeout: {e}")
        # Can choose to retry
    except Error as e:
        self.logger.error(f"Playwright error: {e}")
        # Handle other Playwright errors
```

### 4. Context Management

```python
# Properly use browser contexts
class EfficientSpider(Spider):
    async def parse(self, response):
        # Create a new browser context
        context = await self.playwright.new_context(
            user_agent='Custom User Agent',
            viewport={'width': 1920, 'height': 1080}
        )
        
        try:
            # Perform operations in the context
            page = await context.new_page()
            await page.goto(response.url)
            # Extract data
            yield self.extract_data(page)
        finally:
            # Ensure context is closed
            await context.close()
```