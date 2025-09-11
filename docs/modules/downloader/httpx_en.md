# HttpXDownloader

The HttpXDownloader is a downloader based on the httpx library that provides HTTP/2 support and excellent async capabilities. It is a good alternative to AioHttpDownloader when HTTP/2 support is needed.

## Overview

The HttpXDownloader uses the httpx library to provide advanced HTTP client functionality with HTTP/2 support. It is optimized for:

- HTTP/2 protocol support
- Modern async/await interface
- Comprehensive HTTP features
- Excellent compatibility

## Key Features

### HTTP/2 Support

The HttpXDownloader supports HTTP/2 protocol which provides:

- Multiplexing of requests over a single connection
- Header compression
- Server push (when supported)
- Improved performance for modern websites

### Configuration Options

The HttpXDownloader supports various configuration options:

```python
# In settings.py
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

# HttpX specific settings
HTTPX_HTTP2 = True
HTTPX_FOLLOW_REDIRECTS = True
CONNECTION_POOL_LIMIT = 50
CONNECTION_TTL_DNS_CACHE = 300
```

### Middleware Integration

The HttpXDownloader integrates with the middleware system to provide:

- Request preprocessing
- Response postprocessing
- Exception handling
- Statistics tracking

## API Reference

### `HttpXDownloader(crawler)`

Creates a new HttpXDownloader instance.

**Parameters:**
- `crawler`: The crawler instance that owns this downloader

### `async download(request)`

Downloads a request using the httpx client.

**Parameters:**
- `request`: The request to download

**Returns:**
- `Response`: The downloaded response

### `open()`

Initializes the downloader and creates the httpx client.

### `async close()`

Cleans up resources and closes the httpx client.

### `idle()`

Checks if the downloader is idle (no active requests).

**Returns:**
- `bool`: True if downloader is idle

## Configuration Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `HTTPX_HTTP2` | Enable HTTP/2 support | True |
| `HTTPX_FOLLOW_REDIRECTS` | Automatically follow redirects | True |
| `CONNECTION_POOL_LIMIT` | Maximum number of connections in the pool | 50 |
| `CONNECTION_TTL_DNS_CACHE` | DNS cache TTL in seconds | 300 |

## Example Usage

```python
from crawlo.downloader import HttpXDownloader

# Configure in settings.py
DOWNLOADER = "crawlo.downloader.httpx_downloader.HttpXDownloader"

# Or create directly (not recommended for production)
downloader = HttpXDownloader(crawler)
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

- HTTP/2 can significantly improve performance for sites that support it
- Connection pooling helps reduce overhead for multiple requests
- Adjust `CONNECTION_POOL_LIMIT` based on target server capacity
- Monitor HTTP/2 connection reuse statistics

## When to Use HttpXDownloader

The HttpXDownloader is recommended for:

- Websites that support HTTP/2
- Cases where HTTP/2 performance benefits are needed
- Modern web applications
- When you need the latest HTTP features
- APIs that benefit from HTTP/2 multiplexing

It may not be suitable for:

- Older websites that only support HTTP/1.1
- Cases where maximum raw performance is needed (AioHttp may be faster)
- Sites with specific compatibility requirements