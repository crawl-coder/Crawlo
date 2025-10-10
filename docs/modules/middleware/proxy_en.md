# Proxy Middleware

The Crawlo framework provides two proxy middleware implementations to meet different scenario requirements:

1. [ProxyMiddleware (Advanced Version)](#proxy-middleware-advanced-version) - Advanced version with rich features but complex implementation
2. [SimpleProxyMiddleware (Basic Version)](#simpleproxy-middleware-basic-version) - Basic version with fundamental features but simple implementation

## ProxyMiddleware (Advanced Version)

### Overview

ProxyMiddleware is a feature-rich proxy middleware that supports dynamic proxy acquisition, proxy pool management, health checks, and more. It is suitable for scenarios requiring advanced proxy management features.

### Features

1. **Dynamic Proxy Acquisition**: Dynamically obtain proxy servers through API
2. **Proxy Pool Management**: Maintain proxy pool list, support multiple proxies
3. **Health Check**: Track proxy health status, statistics success rate
4. **Multiple Downloader Support**: Compatible with aiohttp, httpx, curl-cffi and other downloaders
5. **Flexible Configuration**: Support multiple configuration options

### Configuration Options

```python
# Enable proxy middleware
PROXY_ENABLED = True

# Proxy API configuration
PROXY_API_URL = "http://proxy-api.example.com/get"  # Proxy acquisition interface
PROXY_EXTRACTOR = "data.proxy.list"  # Proxy extraction method
PROXY_REFRESH_INTERVAL = 60  # Proxy refresh interval (seconds)
PROXY_API_TIMEOUT = 10  # Request proxy API timeout

# Proxy pool configuration
PROXY_POOL_SIZE = 5  # Proxy pool size
PROXY_HEALTH_CHECK_THRESHOLD = 0.5  # Health check threshold
```

### Usage Example

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.proxy.ProxyMiddleware',
    # ... other middleware
]

# Proxy configuration
PROXY_ENABLED = True
PROXY_API_URL = "http://proxy-api.example.com/get"
PROXY_EXTRACTOR = "data.proxy.list"
PROXY_REFRESH_INTERVAL = 60
```

### Applicable Scenarios

1. Need to dynamically obtain proxies from API
2. Need proxy pool management and health checking
3. Need statistics on proxy success rates
4. Have a large number of proxies to manage
5. Have high requirements for proxy availability

## SimpleProxyMiddleware (Basic Version)

### Overview

SimpleProxyMiddleware is a lightweight proxy middleware based on a fixed proxy list implementation. It has simple code, is easy to configure and use, and is suitable for scenarios that only require basic proxy functionality.

### Features

1. **Simple Implementation**: Based on fixed proxy list
2. **Lightweight**: Less code, low performance overhead
3. **Easy Configuration**: Only need to provide proxy list
4. **Easy to Understand**: Clear logic, easy to maintain

### Configuration Options

```python
# Enable simple proxy middleware
PROXY_ENABLED = True

# Proxy list configuration
PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]
```

### Usage Example

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.simple_proxy.SimpleProxyMiddleware',
    # ... other middleware
]

# Simple proxy configuration
PROXY_ENABLED = True
PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
]
```

### Applicable Scenarios

1. Have a fixed list of proxy servers
2. Do not need to dynamically obtain proxies
3. Have no special requirements for proxy health status
4. Want simpler configuration and usage
5. Have high performance requirements
6. Beginners or simple projects

## Complexity Comparison

| Feature | ProxyMiddleware (Advanced) | SimpleProxyMiddleware (Basic) |
|---------|----------------------------|-------------------------------|
| Feature Richness | High | Basic |
| Configuration Complexity | High | Low |
| Code Lines | ~380 lines | ~80 lines |
| Dependency Complexity | High | Low |
| Performance Overhead | Medium | Low |
| Maintenance Difficulty | High | Low |
| Applicable Scenarios | Advanced proxy management needs | Basic proxy needs |

## Selection Recommendations

### Choose ProxyMiddleware When

1. Project needs to dynamically obtain proxy servers from API
2. Need to maintain proxy pool and perform health checks
3. Need statistics on proxy success rates
4. Using multiple different types of downloaders
5. Large project scale with high proxy management requirements

### Choose SimpleProxyMiddleware When

1. Project has a fixed list of proxy servers
2. Do not need to dynamically obtain proxies
3. Have no special requirements for proxy health status
4. Want to simplify configuration and usage
5. Project scale is small or in early development stage
6. Have high performance requirements and want to reduce unnecessary overhead

## Best Practices

### 1. Choose Based on Requirements

When selecting a proxy middleware, choose based on the project's actual requirements:

- Evaluate whether you really need dynamic proxy acquisition functionality
- Consider the project's scale and complexity
- Avoid over-engineering, choose the simplest implementation that meets requirements

### 2. Progressive Upgrade

It is recommended to use proxy middleware in a progressive way:

1. Use SimpleProxyMiddleware in early project stages
2. Upgrade to ProxyMiddleware when advanced features are needed
3. Maintain configuration compatibility for easy switching

### 3. Configuration Management

- Centralize proxy configuration management for easy maintenance
- Use environment variables to configure sensitive information (such as API keys)
- Provide clear configuration documentation and examples

### 4. Monitoring and Logging

- Enable appropriate log levels for debugging
- Monitor proxy usage and success rates
- Regularly check the validity of proxy configurations

## Summary

The two proxy middleware implementations provided by the Crawlo framework each have their advantages:

- **ProxyMiddleware** is suitable for complex scenarios requiring advanced proxy management features
- **SimpleProxyMiddleware** is suitable for simple scenarios requiring only basic proxy functionality

Developers should choose the appropriate proxy middleware implementation based on the project's actual requirements, avoid unnecessary complexity, and ensure that functional requirements are met.