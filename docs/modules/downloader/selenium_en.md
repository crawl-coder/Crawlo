# SeleniumDownloader

SeleniumDownloader is a browser automation downloader based on Selenium in the Crawlo framework, suitable for complex web crawling scenarios that require JavaScript execution or user interaction simulation.

## Overview

SeleniumDownloader provides a complete browser environment that can execute JavaScript, handle AJAX requests, and simulate user interaction operations, making it suitable for crawling modern web applications.

### Core Features

1. **Complete Browser Environment** - Provides a real browser environment
2. **JavaScript Execution** - Supports complex JavaScript execution
3. **User Interaction Simulation** - Supports click, input, scroll and other user operations
4. **Waiting Mechanism** - Supports explicit and implicit waiting
5. **Multi-browser Support** - Supports mainstream browsers like Chrome and Firefox

## Configuration Options

The behavior of SeleniumDownloader can be adjusted through the following configuration options:

| Configuration Item | Type | Default Value | Description |
|--------------------|------|---------------|-------------|
| SELENIUM_BROWSER | str | 'chrome' | Browser type (chrome/firefox) |
| SELENIUM_HEADLESS | bool | True | Whether to enable headless mode |
| SELENIUM_WINDOW_SIZE | tuple | (1920, 1080) | Browser window size |
| SELENIUM_TIMEOUT | int | 30 | Page loading timeout |
| SELENIUM_IMPLICIT_WAIT | int | 10 | Implicit wait time |

## Usage Examples

### Basic Usage

```python
from crawlo.config import CrawloConfig

# Configure to use Selenium downloader
config = CrawloConfig.standalone(
    downloader_type='selenium',
    selenium_browser='chrome',
    selenium_headless=True
)
```

### Advanced Configuration

```python
# Configure browser options
config = CrawloConfig.standalone(
    downloader_type='selenium',
    selenium_browser='firefox',
    selenium_headless=False,
    selenium_window_size=(1366, 768),
    selenium_timeout=60
)
```

## Performance Considerations

### Resource Consumption

SeleniumDownloader consumes more resources compared to other downloaders:

- **Memory Usage** - Each browser instance consumes 100-200MB memory
- **CPU Usage** - High CPU usage during startup and operation
- **Startup Time** - Browser startup takes 5-10 seconds

### Concurrency Limitations

Due to high resource consumption, it's recommended to limit concurrency:

```python
# Limit concurrency
config = CrawloConfig.standalone(
    downloader_type='selenium',
    concurrency=2,  # Low concurrency
    download_delay=2.0  # Increase delay
)
```

## Best Practices

### 1. Selective Usage

```python
# Use Selenium only for necessary requests
class SelectiveSpider(Spider):
    def parse(self, response):
        # Check if browser environment is needed
        if self.needs_browser(response):
            # Use Selenium request
            yield Request(
                url=response.url,
                callback=self.parse_with_browser,
                meta={'use_selenium': True}
            )
        else:
            # Use normal request
            yield Request(
                url=response.url,
                callback=self.parse_normal
            )
```

### 2. Resource Management

```python
# Properly manage browser instances
class EfficientSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.browser_pool = []
    
    def closed(self, reason):
        # Close all browser instances
        for browser in self.browser_pool:
            browser.quit()
        super().closed(reason)
```

### 3. Error Handling

```python
# Handle browser-related exceptions
def parse_with_browser(self, response):
    try:
        # Browser operations
        yield self.extract_data(response)
    except WebDriverException as e:
        self.logger.error(f"Browser operation failed: {e}")
        # Can choose to restart browser or skip
    except TimeoutException as e:
        self.logger.warning(f"Page loading timeout: {e}")
        # Can choose to retry
```