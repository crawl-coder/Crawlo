# 配置问题

## 如何选择部署模式？

Crawlo 提供三种部署模式：

### 内存模式

对应配置：`RUN_MODE='standalone'`，`QUEUE_TYPE='memory'`

**适用场景**：
- 本地开发调试
- 小规模数据采集（< 10万条）
- 不需要外部依赖

**配置**：
```python
# settings.py
RUN_MODE = 'standalone'
QUEUE_TYPE = 'memory'
CONCURRENCY = 8
```

### 多节点协作模式

对应配置：`RUN_MODE='auto'`，`QUEUE_TYPE='redis'`

**适用场景**：
- 多机并发爬取
- 能接受任务丢失
- 已有 Redis 环境

**配置**：
```python
# settings.py
RUN_MODE = 'auto'
QUEUE_TYPE = 'redis'
CONCURRENCY = 16
```

### 分布式系统模式 ⭐

对应配置：`RUN_MODE='distributed'`，`QUEUE_TYPE='redis_stream'`

**适用场景**：
- 生产环境部署
- 任务可靠性要求高
- 需要 ACK 确认、故障转移、自动协调退出

**配置**：
```python
# settings.py
RUN_MODE = 'distributed'
QUEUE_TYPE = 'redis_stream'
CONCURRENCY = 16
```

查看 [三种部署模式详解](../guides/configuration/run-modes.md) 了解更多。

## Redis 是必需的吗？

**不是！** 取决于部署模式：

| 模式 | Redis 要求 |
|------|-----------|
| 内存模式 | ❌ 不需要 |
| 多节点协作 | ✅ 必需 |
| 分布式系统 | ✅ 必需 |

**建议**：
- 开发测试：使用内存模式，无需 Redis
- 多机并发：使用多节点协作或分布式系统模式

## 如何配置代理？

### 简单代理

```python
# settings.py
PROXY_ENABLED = True
PROXY_LIST = [
    'http://proxy1.example.com:8080',
    'http://proxy2.example.com:8080',
]
PROXY_MODE = 'round-robin'  # 轮询
```

### 动态代理

```python
# settings.py
PROXY_ENABLED = True
PROXY_API_URL = 'https://proxy-api.example.com/get'
PROXY_API_PARAMS = {'key': 'your_api_key'}
```

### 在请求中使用代理

```python
yield Request(
    url='https://example.com',
    meta={'proxy': 'http://proxy:8080'}
)
```

查看 [代理中间件源码](../../crawlo/middleware/proxy.py) 了解更多。

## 如何调整并发数？

```python
# settings.py
CONCURRENCY = 16  # 同时请求数
```

**建议值**：
- 小规模爬取：4-8
- 中等规模：8-16
- 大规模：16-32
- 有代理支持：32-64

**注意**：并发数过高可能导致：
- 目标网站拒绝服务
- 本地资源耗尽
- IP 被封禁

## 如何设置下载延迟？

```python
# settings.py
DOWNLOAD_DELAY = 1.0  # 基础延迟（秒）
RANDOMNESS = True     # 启用随机抖动
```

**实际延迟**：`DOWNLOAD_DELAY * (0.5 ~ 1.5)`

例如 `DOWNLOAD_DELAY = 1.0` 时，实际延迟为 0.5~1.5 秒。

## 如何启用浏览器渲染？

### 方式1: 在请求中指定

```python
yield Request(
    url='https://example.com',
    meta={'use_dynamic_loader': True}
)
```

### 方式2: 全局配置

```python
# settings.py
DEFAULT_USE_DYNAMIC_LOADER = True
```

### 方式3: 按域名配置

```python
# settings.py
DYNAMIC_LOADER_URL_PATTERNS = [
    r'.*\.example\.com/.*',  # example.com 使用浏览器
]
```

## 如何配置数据存储？

### 保存到文件

```bash
crawlo run myspider -o output.json
```

### 保存到 MySQL

```python
# settings.py
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
MYSQL_DATABASE = 'mydb'

# 方式1：短路径（推荐，需 v1.6.0+）
PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}

# 方式2：完整路径（v2.0 新目录结构）
# PIPELINES = {
#     'crawlo.pipelines.sql.mysql.MySQLPipeline': 300,
# }
```

### 保存到 MongoDB

```python
# settings.py
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'mydb'

# 方式1：短路径（推荐）
PIPELINES = {
    'crawlo.pipelines.MongoPipeline': 300,
}

# 方式2：完整路径
# PIPELINES = {
#     'crawlo.pipelines.doc.mongo.MongoPipeline': 300,
# }
```

## 如何配置日志？

```python
# settings.py
LOG_LEVEL = 'INFO'  # DEBUG/INFO/WARNING/ERROR
LOG_FILE = 'spider.log'  # 日志文件
LOG_FORMAT = '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
```

**日志级别**：
- `DEBUG`: 详细信息（开发调试）
- `INFO`: 一般信息（生产推荐）
- `WARNING`: 警告信息
- `ERROR`: 错误信息

## 如何配置重试？

```python
# settings.py
RETRY_ENABLED = True
RETRY_TIMES = 3  # 最大重试次数
RETRY_HTTP_CODES = [500, 502, 503, 504, 408]
```

## 如何配置去重？

```python
# settings.py
# 内存去重（内存模式）
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.MemoryDedupPipeline'

# Redis 去重（分布式系统模式）
DEFAULT_DEDUP_PIPELINE = 'crawlo.pipelines.RedisDedupPipeline'
```

## 配置文件优先级？

Crawlo 配置有多个层级，优先级从低到高：

1. **默认配置**（框架内置）
2. **项目配置**（settings.py）
3. **爬虫配置**（spider 类属性）
4. **请求配置**（Request.meta）
5. **命令行参数**（最高）

**示例**：
```python
# settings.py（优先级低）
CONCURRENCY = 8

# 爬虫代码中（优先级高）
class MySpider(Spider):
    custom_settings = {
        'CONCURRENCY': 16,  # 覆盖 settings.py
    }
```

## 如何实现深度优先/广度优先？

通过 `DEPTH_PRIORITY` 配置项控制。框架自动传播请求深度（`depth`），配合此配置实现不同调度策略：

### 深度优先（详情页优先出队）

```python
# settings.py
DEPTH_PRIORITY = 1  # 默认值
```

**效果**：列表页解析后，详情页立即被消费，不会等所有列表页处理完。

**原理**：
```
列表页 (depth=1) → 内部 priority = -1
详情页 (depth=2) → 内部 priority = -2
-2 < -1 → 详情页先出队
```

### 广度优先（列表页优先出队）

```python
# settings.py
DEPTH_PRIORITY = -1
```

**效果**：同层级的请求先处理完，再处理下一层级。

**原理**：
```
列表页 (depth=1) → 内部 priority = 1
详情页 (depth=2) → 内部 priority = 2
1 < 2 → 列表页先出队
```

### 不按深度调整

```python
# settings.py
DEPTH_PRIORITY = 0  # 仅按用户设置的 priority 排序
```

> **注意**：`depth` 由框架自动传播（Engine 层面），无需在 Spider 中手动设置。`start_requests` 的 depth 默认为 1，Spider 回调产生的子请求 depth 自动为 `parent.depth + 1`。

---

**还有其他配置问题？** 查看 [配置指南](../guides/configuration/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
