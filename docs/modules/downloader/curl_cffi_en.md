# CurlCffiDownloader

The CurlCffiDownloader is a downloader based on curl-cffi that provides browser fingerprint simulation capabilities. It is particularly useful for bypassing anti-bot measures that detect automated requests.

## Overview

The CurlCffiDownloader uses the curl-cffi library to provide HTTP client functionality with browser fingerprint simulation. It is optimized for:

- Browser fingerprint simulation
- Bypassing anti-bot measures
- JavaScript-like request behavior
- High compatibility with real browsers

## Key Features

### Browser Fingerprint Simulation

The CurlCffiDownloader can simulate various browser fingerprints:

- Chrome, Edge, Safari, Firefox browser signatures
- TLS fingerprinting
- HTTP/2 fingerprinting
- JA3 fingerprinting resistance

### Configuration Options

The CurlCffiDownloader supports various configuration options:

```python
# In settings.py
DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"

# CurlCffi specific settings
CURL_BROWSER_TYPE = "chrome"
CURL_BROWSER_VERSION_MAP = {
    "chrome": "chrome136",
    "edge": "edge101",
    "safari": "safari184",
    "firefox": "firefox135",
}
```

### Middleware Integration

The CurlCffiDownloader integrates with the middleware system to provide:

- Request preprocessing
- Response postprocessing
- Exception handling
- Statistics tracking

## API Reference

### `CurlCffiDownloader(crawler)`

Creates a new CurlCffiDownloader instance.

**Parameters:**
- `crawler`: The crawler instance that owns this downloader

### `async download(request)`

Downloads a request using the curl-cffi client.

**Parameters:**
- `request`: The request to download

**Returns:**
- `Response`: The downloaded response

### `open()`

Initializes the downloader and creates the curl-cffi client.

### `async close()`

Cleans up resources and closes the curl-cffi client.

### `idle()`

Checks if the downloader is idle (no active requests).

**Returns:**
- `bool`: True if downloader is idle

## Configuration Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `CURL_BROWSER_TYPE` | Browser type to simulate | "chrome" |
| `CURL_BROWSER_VERSION_MAP` | Browser version mappings | See above |

## Example Usage

```python
from crawlo.downloader import CurlCffiDownloader

# Configure in settings.py
DOWNLOADER = "crawlo.downloader.cffi_downloader.CurlCffiDownloader"

# Configure browser type
CURL_BROWSER_TYPE = "chrome136"

# Or create directly (not recommended for production)
downloader = CurlCffiDownloader(crawler)
await downloader.open()

# Download a request
response = await downloader.download(request)

# Check if idle
if downloader.idle():
    print("No active downloads")

# Cleanup
await downloader.close()
```

## Browser Simulation

The CurlCffiDownloader can simulate different browsers:

```python
# Simulate Chrome
CURL_BROWSER_TYPE = "chrome"

# Simulate Firefox
CURL_BROWSER_TYPE = "firefox"

# Simulate Safari
CURL_BROWSER_TYPE = "safari"

# Simulate Edge
CURL_BROWSER_TYPE = "edge"
```

## Performance Considerations

- Browser fingerprint simulation adds some overhead
- Connection reuse may be less efficient than pure HTTP clients
- Memory usage may be higher than simpler downloaders
- Some advanced features may not be available

## When to Use CurlCffiDownloader

The CurlCffiDownloader is recommended for:

- Websites with strong anti-bot measures
- Cases where browser fingerprint detection is a concern
- Sites that block standard HTTP clients
- When you need to appear more like a real browser
- E-commerce sites with advanced bot protection

It may not be suitable for:

- Simple websites without anti-bot measures
- Cases where maximum performance is required
- When minimal dependencies are preferred
- Internal APIs or simple web services