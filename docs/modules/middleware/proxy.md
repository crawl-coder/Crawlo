# 代理中间件

Crawlo框架提供了两种代理中间件实现，以满足不同场景的需求：

1. [ProxyMiddleware](#proxy-middleware-复杂版) - 复杂版，功能丰富但实现复杂
2. [SimpleProxyMiddleware](#simple-proxy-middleware-简化版) - 简化版，功能基础但实现简洁

## ProxyMiddleware (复杂版)

### 概述

ProxyMiddleware是一个功能丰富的代理中间件，支持动态代理获取、代理池管理、健康检查等功能。它适用于需要高级代理管理功能的场景。

### 功能特性

1. **动态代理获取**：通过API动态获取代理服务器
2. **代理池管理**：维护代理池列表，支持多个代理
3. **健康检查**：跟踪代理健康状态，统计成功率
4. **多种下载器支持**：兼容aiohttp、httpx、curl-cffi等多种下载器
5. **灵活配置**：支持多种配置选项

### 配置选项

```python
# 启用代理中间件
PROXY_ENABLED = True

# 代理API配置
PROXY_API_URL = "http://proxy-api.example.com/get"  # 代理获取接口
PROXY_EXTRACTOR = "data.proxy.list"  # 代理提取方式
PROXY_REFRESH_INTERVAL = 60  # 代理刷新间隔（秒）
PROXY_API_TIMEOUT = 10  # 请求代理API超时时间

# 代理池配置
PROXY_POOL_SIZE = 5  # 代理池大小
PROXY_HEALTH_CHECK_THRESHOLD = 0.5  # 健康检查阈值
```

### 使用示例

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.proxy.ProxyMiddleware',
    # ... 其他中间件
]

# 代理配置
PROXY_ENABLED = True
PROXY_API_URL = "http://proxy-api.example.com/get"
PROXY_EXTRACTOR = "data.proxy.list"
PROXY_REFRESH_INTERVAL = 60
```

### 适用场景

1. 需要从API动态获取代理
2. 需要代理健康检查和成功率统计
3. 需要复杂的代理提取逻辑
4. 有大量代理需要管理
5. 对代理的可用性有较高要求

## SimpleProxyMiddleware (简化版)

### 概述

SimpleProxyMiddleware是一个轻量级的代理中间件，基于固定代理列表实现。它代码简洁，易于配置和使用，适用于只需要基本代理功能的场景。

### 功能特性

1. **简单实现**：基于固定代理列表
2. **轻量级**：代码量少，性能开销低
3. **易于配置**：只需要提供代理列表
4. **易于理解**：逻辑清晰，便于维护

### 配置选项

```python
# 启用简化版代理中间件
PROXY_ENABLED = True

# 代理列表配置
PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]
```

### 使用示例

```python
# settings.py
MIDDLEWARES = [
    'crawlo.middleware.simple_proxy.SimpleProxyMiddleware',
    # ... 其他中间件
]

# 简化版代理配置
PROXY_ENABLED = True
PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
]
```

### 适用场景

1. 有固定的代理列表
2. 不需要动态获取代理
3. 对代理的健康状况没有特殊要求
4. 希望配置和使用更简单
5. 对性能有较高要求
6. 初学者或简单项目

## 复杂性对比

| 特性 | ProxyMiddleware (复杂版) | SimpleProxyMiddleware (简化版) |
|------|-------------------------|-------------------------------|
| 功能丰富度 | 高 | 基础 |
| 配置复杂度 | 高 | 低 |
| 代码行数 | ~380行 | ~80行 |
| 依赖复杂度 | 高 | 低 |
| 性能开销 | 中等 | 低 |
| 维护难度 | 高 | 低 |
| 适用场景 | 高级代理管理需求 | 基础代理需求 |

## 选择建议

### 选择ProxyMiddleware的场景

1. 项目需要从API动态获取代理服务器
2. 需要维护代理池并进行健康检查
3. 对代理的成功率有统计需求
4. 使用多种不同类型的下载器
5. 项目规模较大，对代理管理有较高要求

### 选择SimpleProxyMiddleware的场景

1. 项目有固定的代理服务器列表
2. 不需要动态获取代理
3. 对代理的健康状况没有特殊要求
4. 希望简化配置和使用
5. 项目规模较小或处于初期开发阶段
6. 对性能有较高要求，希望减少不必要的开销

## 最佳实践

### 1. 根据需求选择

在选择代理中间件时，应根据项目的实际需求进行选择：

- 评估是否真的需要动态代理获取功能
- 考虑项目的规模和复杂度
- 避免过度设计，选择满足需求的最简实现

### 2. 渐进式升级

建议采用渐进式的方式使用代理中间件：

1. 项目初期使用SimpleProxyMiddleware
2. 当需要高级功能时再升级到ProxyMiddleware
3. 保持配置的兼容性，便于切换

### 3. 配置管理

- 将代理配置集中管理，便于维护
- 使用环境变量配置敏感信息（如API密钥）
- 提供清晰的配置文档和示例

### 4. 监控和日志

- 启用适当的日志级别，便于调试
- 监控代理的使用情况和成功率
- 定期检查代理配置的有效性

## 总结

Crawlo框架提供的两种代理中间件实现各有优势：

- **ProxyMiddleware**适用于需要高级代理管理功能的复杂场景
- **SimpleProxyMiddleware**适用于只需要基本代理功能的简单场景

开发者应根据项目的实际需求选择合适的代理中间件实现，避免不必要的复杂性，同时确保满足项目的功能要求。