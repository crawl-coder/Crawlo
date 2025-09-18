# 增强版代理中间件使用指南

## 概述

增强版ProxyMiddleware在原有功能基础上增加了代理池管理和健康检查机制，提供了更稳定和高效的代理服务。

## 新增功能

### 1. 代理池管理
- 支持维护多个代理的池化管理
- 自动轮询使用不同代理
- 可配置代理池大小

### 2. 健康检查机制
- 跟踪每个代理的成功率和失败率
- 自动标记不健康的代理
- 可配置健康检查阈值

### 3. 智能代理选择
- 优先选择健康的代理
- 基于成功率的代理选择策略
- 自动更新代理池

## 配置选项

```python
# 是否启用代理
PROXY_ENABLED = False

# 代理API地址
PROXY_API_URL = "https://api.proxyprovider.com/get"

# 代理提取字段路径
PROXY_EXTRACTOR = "proxy"

# 代理刷新间隔（秒）
PROXY_REFRESH_INTERVAL = 60

# 请求代理API超时时间（秒）
PROXY_API_TIMEOUT = 10

# 代理池大小
PROXY_POOL_SIZE = 5

# 健康检查阈值（成功率低于此值的代理将被标记为不健康）
PROXY_HEALTH_CHECK_THRESHOLD = 0.5
```

## 使用示例

### 基本配置
```python
# settings.py
PROXY_ENABLED = True
PROXY_API_URL = "http://your-proxy-api.com/get"
PROXY_EXTRACTOR = "data.proxy"
PROXY_POOL_SIZE = 10
PROXY_HEALTH_CHECK_THRESHOLD = 0.7
```

### API响应格式
增强版ProxyMiddleware支持多种API响应格式：

1. 单个代理字符串：
```json
{
  "proxy": "http://proxy.example.com:8080"
}
```

2. 代理列表：
```json
{
  "data": {
    "proxy": [
      "http://proxy1.example.com:8080",
      "http://proxy2.example.com:8080",
      "http://proxy3.example.com:8080"
    ]
  }
}
```

3. 多字段代理信息：
```json
{
  "proxies": [
    {"ip": "proxy1.example.com", "port": 8080},
    {"ip": "proxy2.example.com", "port": 8080}
  ]
}
```

### 使用指定代理API的配置示例
```python
# settings.py
PROXY_ENABLED = True
PROXY_API_URL = 'http://123.56.42.142:5000/proxy/getitem/'
PROXY_EXTRACTOR = 'proxy'
PROXY_REFRESH_INTERVAL = 60
PROXY_API_TIMEOUT = 10
PROXY_POOL_SIZE = 5
PROXY_HEALTH_CHECK_THRESHOLD = 0.5
```

API响应格式示例：
```json
{
  "status": 0,
  "desc": "资源请求成功",
  "proxy": {
    "http": "http://username:password@proxy.example.com:8080",
    "https": "http://username:password@proxy.example.com:8080"
  }
}
```

## 工作原理

### 代理池更新流程
```mermaid
flowchart TD
    A[定时检查] --> B{超过刷新间隔?}
    B -->|是| C[请求代理API]
    C --> D[解析代理数据]
    D --> E[更新代理池]
    B -->|否| F[继续使用当前代理池]
    E --> G[代理池可用]
```

### 健康检查流程
```mermaid
flowchart TD
    A[选择代理] --> B{代理健康?}
    B -->|是| C[使用代理]
    B -->|否| D[选择其他代理]
    C --> E[发起请求]
    E --> F{请求成功?}
    F -->|是| G[标记代理成功]
    F -->|否| H[标记代理失败]
    H --> I{失败率过高?}
    I -->|是| J[标记为不健康]
    I -->|否| K[保持健康状态]
```

## 最佳实践

### 1. 合理配置代理池大小
根据实际需求和代理质量配置代理池大小：
```python
# 高质量代理可适当减小池大小
PROXY_POOL_SIZE = 3

# 一般质量代理可适当增大池大小
PROXY_POOL_SIZE = 10
```

### 2. 设置合适的健康检查阈值
```python
# 对稳定性要求高的场景
PROXY_HEALTH_CHECK_THRESHOLD = 0.9

# 对可用性要求高的场景
PROXY_HEALTH_CHECK_THRESHOLD = 0.5
```

### 3. 监控代理使用情况
通过日志监控代理使用情况和成功率：
```python
# 启用DEBUG级别日志查看详细信息
LOG_LEVEL = "DEBUG"
```

## 故障排除

### 1. 代理池为空
- 检查代理API是否正常工作
- 确认API响应格式是否正确
- 检查网络连接是否正常

### 2. 代理成功率低
- 检查代理API提供的代理质量
- 调整健康检查阈值
- 增加代理池大小

### 3. 代理认证问题
- 确认代理URL格式正确
- 检查用户名和密码是否正确
- 确认下载器是否支持代理认证

## 扩展开发

### 自定义代理提取器
```python
def custom_proxy_extractor(data):
    """自定义代理提取函数"""
    proxies = []
    for item in data.get('proxy_list', []):
        proxy = f"http://{item['ip']}:{item['port']}"
        proxies.append(proxy)
    return proxies

# 在配置中使用
PROXY_EXTRACTOR = custom_proxy_extractor
```

### 自定义健康检查策略
可以继承ProxyMiddleware类并重写健康检查相关方法：
```python
class CustomProxyMiddleware(ProxyMiddleware):
    async def _get_healthy_proxy(self):
        # 实现自定义的代理选择逻辑
        pass