# DefaultHeaderMiddleware 使用指南

## 概述

DefaultHeaderMiddleware 是 Crawlo 框架提供的一个中间件，用于为所有 HTTP 请求添加默认请求头，包括 User-Agent。它支持静态配置和随机更换功能，可以有效提高爬虫的隐蔽性和成功率。

## 为什么需要随机更换 User-Agent

### 主要优势

1. **反反爬虫能力**
   - 固定 User-Agent 容易被网站识别为爬虫
   - 随机更换可以模拟真实用户行为，降低被识别风险

2. **提高请求成功率**
   - 许多网站会封禁频繁使用相同 User-Agent 的请求
   - 随机更换可以有效避免封禁，提高爬取成功率

3. **增强兼容性**
   - 不同网站可能对不同的浏览器有偏好
   - 随机更换可以适配更多网站

## 简单配置方法

### 一行代码启用随机 User-Agent

在项目配置文件中添加一行配置即可启用随机 User-Agent 功能：

```python
# settings.py
RANDOM_USER_AGENT_ENABLED = True
```

就这么简单！启用后，框架会自动为每个请求随机选择一个现代浏览器的 User-Agent。

## 随机 User-Agent 的来源

当启用 `RANDOM_USER_AGENT_ENABLED = True` 时，随机 User-Agent 来自框架内置的丰富 User-Agent 库：

### 内置 User-Agent 库构成

- **桌面浏览器**: 30个User-Agent
  - Chrome系列（多个版本）
  - Firefox系列（多个版本）
  - Safari系列
  - Edge系列
  - Opera系列

- **移动设备**: 18个User-Agent
  - iPhone系列（多个版本）
  - iPad系列（多个版本）
  - Android手机和平板

### 默认行为

默认情况下，框架会从所有 48 个 User-Agent 中随机选择：

```python
# 默认设备类型为 "all"，包含所有类型的User-Agent
USER_AGENT_DEVICE_TYPE = "all"  # 可选值: "all", "desktop", "mobile", "chrome", "firefox", "safari", "edge", "opera"
```

### 选择特定类型

如果需要只使用特定类型的 User-Agent：

```python
# settings.py
RANDOM_USER_AGENT_ENABLED = True

# 只使用桌面浏览器User-Agent（30个）
USER_AGENT_DEVICE_TYPE = "desktop"

# 只使用移动设备User-Agent（18个）
# USER_AGENT_DEVICE_TYPE = "mobile"

# 只使用Chrome浏览器User-Agent（20个）
# USER_AGENT_DEVICE_TYPE = "chrome"
```

## 默认配置说明

框架已提供合理的默认配置：

```python
# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
}

# 默认User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
```

这些默认配置已经足够应对大多数网站，一般无需修改。

## 高级配置（可选）

如果需要更精细的控制，可以使用以下配置：

### 自定义 User-Agent 列表

```python
# settings.py
RANDOM_USER_AGENT_ENABLED = True

# 使用自定义User-Agent列表（会覆盖内置列表）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
]
```

## 最佳实践

### 1. 基础使用

对于大多数项目，只需在配置文件中添加：

```python
RANDOM_USER_AGENT_ENABLED = True
```

### 2. 配合下载延迟使用

```python
# settings.py
RANDOM_USER_AGENT_ENABLED = True
DOWNLOAD_DELAY = 1.0
RANDOMNESS = True
```

### 3. 生产环境建议

```python
# settings.py
RANDOM_USER_AGENT_ENABLED = True
DOWNLOAD_DELAY = 2.0  # 增加延迟时间
RANDOMNESS = True
CONCURRENCY = 8  # 控制并发数
```

## 注意事项

### 1. 性能影响
- 随机更换 User-Agent 会增加轻微的性能开销
- 但对于现代硬件来说可以忽略不计

### 2. 调试建议
- 开发阶段可以暂时禁用随机功能以便调试
- 生产环境再启用以获得更好的效果

### 3. 兼容性
- 某些特殊网站可能需要特定的 User-Agent
- 遇到问题时可以针对性地调整配置

## 故障排除

### 1. 功能未生效
检查是否正确设置了 `RANDOM_USER_AGENT_ENABLED = True`

### 2. User-Agent 未更换
检查请求中是否手动设置了 User-Agent，中间件不会覆盖已存在的 User-Agent

### 3. 日志调试
启用 DEBUG 级别日志可以查看详细的 User-Agent 更换信息：

```python
LOG_LEVEL = "DEBUG"
```

## 总结

DefaultHeaderMiddleware 的随机 User-Agent 功能是 Crawlo 框架提供的强大反反爬虫工具。通过简单的配置，可以显著提高爬虫的成功率和稳定性。

**只需一行配置即可启用：**

```python
RANDOM_USER_AGENT_ENABLED = True
```

这就是全部！框架会处理剩下的所有工作，从内置的 48 个现代浏览器 User-Agent 中随机选择，有效提高爬虫的隐蔽性。