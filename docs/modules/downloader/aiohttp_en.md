# AioHttpDownloader

The AioHttpDownloader is a high-performance downloader based on the aiohttp library. It is the default downloader for Crawlo and provides excellent performance for most web scraping tasks.

## Overview

The AioHttpDownloader leverages the aiohttp library to provide asynchronous HTTP client functionality. It is optimized for:

- High concurrency
- Connection pooling
- Efficient memory usage
- HTTP/1.1 support

## Key Features

### Performance Optimizations

- **Connection Pooling**: Reuses connections to reduce overhead
- **Keep-Alive Support**: Maintains persistent connections
- **Concurrent Requests**: Handles multiple requests simultaneously
- **Efficient Memory Usage**: Minimal memory footprint per request

### Configuration Options

The AioHttpDownloader supports various configuration options:

```python
# In settings.py
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"

# AioHttp specific settings
CONNECTION_POOL_LIMIT = 50
CONNECTION_TTL_DNS_CACHE = 300
CONNECTION_KEEPALIVE_TIMEOUT = 15
AIOHTTP_AUTO_DECOMPRESS = True
AIOHTTP_FORCE_CLOSE = False
```

### Middleware Integration

The AioHttpDownloader integrates with the middleware system to provide:

- Request preprocessing
- Response postprocessing
- Exception handling
- Statistics tracking

## API Reference

### `AioHttpDownloader(crawler)`

Creates a new AioHttpDownloader instance.

**Parameters:**
- `crawler`: The crawler instance that owns this downloader

### `async download(request)`

Downloads a request using the aiohttp client.

**Parameters:**
- `request`: The request to download

**Returns:**
- `Response`: The downloaded response

### `open()`

Initializes the downloader and creates the aiohttp client session.

### `async close()`

Cleans up resources and closes the aiohttp client session.

### `idle()`

Checks if the downloader is idle (no active requests).

**Returns:**
- `bool`: True if downloader is idle

## Configuration Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `CONNECTION_POOL_LIMIT` | Maximum number of connections in the pool | 50 |
| `CONNECTION_TTL_DNS_CACHE` | DNS cache TTL in seconds | 300 |
| `CONNECTION_KEEPALIVE_TIMEOUT` | Keep-alive timeout in seconds | 15 |
| `AIOHTTP_AUTO_DECOMPRESS` | Automatically decompress responses | True |
| `AIOHTTP_FORCE_CLOSE` | Force close connections after each request | False |

## Example Usage

```python
from crawlo.downloader import AioHttpDownloader

# Configure in settings.py
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"

# Or create directly (not recommended for production)
downloader = AioHttpDownloader(crawler)
await downloader.open()

# Download a request
response = await downloader.download(request)

# Check if idle
if downloader.idle():
    print("No active downloads")

# Cleanup
await downloader.close()
```

## Performance Considerations

- Adjust `CONNECTION_POOL_LIMIT` based on target server capacity
- Use appropriate timeout settings to avoid hanging requests
- Enable `AIOHTTP_AUTO_DECOMPRESS` for compressed content
- Monitor connection reuse statistics to optimize performance

## When to Use AioHttpDownloader

The AioHttpDownloader is recommended for:

- General-purpose web scraping
- High-concurrency scenarios
- Static content downloading
- When maximum performance is required
- Most standard web scraping tasks

It may not be suitable for:

- JavaScript-heavy websites (use Selenium or Playwright instead)
- Cases requiring browser fingerprinting (use CurlCffi instead)
- Sites with strict anti-bot measures (consider alternatives)