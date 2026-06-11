# 代理配置指南

> 静态列表 + 动态 API + 自动切换 — 三种代理模式覆盖所有场景。

## 概述

Crawlo 通过 `ProxyMiddleware` 实现自动代理管理，支持静态代理列表、动态代理 API 和自动切换策略。

## 静态代理

配置固定的代理列表，随机分配：

```python
# settings.py
PROXY_LIST = [
    "http://user:pass@proxy1.example.com:8080",
    "http://user:pass@proxy2.example.com:8080",
    "socks5://user:pass@proxy3.example.com:1080",
]
```

支持的协议：`http`、`https`、`socks5`。

轮询策略：默认**随机选择**，每次请求从池中随机抽取。

## 动态代理 API

从代理 API 动态获取：

```python
PROXY_API_URL = "http://proxy-pool.example.com/api/get"
PROXY_EXTRACTOR = "proxy"              # 从 JSON 响应的 'proxy' 字段提取
```

API 响应格式：

```json
{
    "proxy": "http://1.2.3.4:8080",
    "expire": 300
}
```

### 自定义提取器

```python
# extractors.py
def extract_proxy(data):
    # data['data']['ip'] = '1.2.3.4', data['data']['port'] = 8080
    ip = data['data']['ip']
    port = data['data']['port']
    return f"http://{ip}:{port}"

# settings.py
PROXY_API_URL = "http://api.example.com/proxy"
PROXY_EXTRACTOR = "myproject.extractors.extract_proxy"
```

## 自动切换策略

与 `RetryMiddleware` 协同工作：

```python
# 触发重试时：
# 1. 网络/连接错误 → 清除当前代理 → 从池中获取新代理 → 重试
# 2. HTTP 错误（4xx/5xx） → 保留当前代理 → 重试（通常是目标服务器问题）
```

```python
MAX_RETRY_TIMES = 3                    # 代理切换也是重试逻辑的一部分
RETRY_PRIORITY = 10                    # 代理切换重试的优先级
PROXY_SWITCH_THRESHOLD = 2             # 重试超过此阈值切换代理
```

## 免代理（白名单）

```python
PROXY_WHITELIST = ['localhost', '127.0.0.1', 'internal-api.com']
# 匹配白名单的 URL 不使用代理
```

## 配置总览

```python
# settings.py — 完整代理配置
PROXY_ENABLED = True

# 静态代理
PROXY_LIST = [
    "http://proxy1:8080",
    "http://proxy2:8080",
]

# 动态代理
PROXY_API_URL = "http://proxy-api.com/get-proxy"
PROXY_EXTRACTOR = "proxy"              # JSON 字段名或自定义函数路径

# 重试时的代理切换
PROXY_SWITCH_THRESHOLD = 2             # 网络失败 >N 次切换代理

# 白名单
PROXY_WHITELIST = ['localhost', '127.0.0.1']

# 浏览器代理（Playwright/Camoufox/CloakBrowser）
BROWSER_PROXY = None                   # 或: "http://proxy:8080"
```
