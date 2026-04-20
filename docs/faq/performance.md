# 性能问题

## 如何提升爬取速度？

### 1. 调整并发数

```python
# settings.py
CONCURRENCY = 32  # 增加并发数
```

**注意**：并发数不是越高越好，需要考虑：
- 目标网站承受能力
- 本地资源（CPU/内存/网络）
- 是否有代理支持

### 2. 减少下载延迟

```python
# settings.py
DOWNLOAD_DELAY = 0  # 无延迟（谨慎使用）
```

### 3. 使用更快的下载器

```python
# settings.py
DOWNLOADER = 'crawlo.downloader.HttpXDownloader'  # httpx 比 aiohttp 快
```

### 4. 禁用不需要的中间件

```python
# settings.py
DOWNLOADER_MIDDLEWARES = {
    # 注释不需要的中间件
    # 'crawlo.middleware.ProxyMiddleware': 100,
}
```

### 5. 优化选择器

```python
# 使用 CSS 选择器（比 XPath 快）
data = response.css('div.item::text').get()

# 避免使用正则表达式
```

### 6. 使用连接池

```python
# settings.py
# MySQL 连接池
MYSQL_POOL_SIZE = 20

# Redis 连接池
REDIS_POOL_SIZE = 20
```

## 内存占用过高怎么办？

### 原因分析

1. **队列积压**：pending 请求过多
2. **数据未清理**：Item 缓存过多
3. **连接未关闭**：数据库连接泄漏
4. **浏览器未关闭**：Playwright 实例泄漏

### 解决方案

#### 1. 限制队列大小

```python
# settings.py
MEMORY_SCHEDULER_MAX_QUEUE_SIZE = 5000  # 限制队列大小
```

#### 2. 启用背压系统

```python
# settings.py
BACKPRESSURE_ENABLED = True
BACKPRESSURE_RATIO = 0.8  # 80% 使用率时触发
```

#### 3. 使用高效的Pipeline

```python
# settings.py
PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,  # MySQL批量存储
}
MYSQL_BATCH_SIZE = 100  # 每100条保存一次
```

#### 4. 定期清理缓存

```python
# settings.py
MEMORY_FILTER_MAX_SIZE = 100000  # 限制过滤器大小
```

## 如何优化并发？

### 网络并发

```python
# settings.py
CONCURRENCY = 32  # 请求并发数
TCP_KEEPALIVE = True  # 启用 TCP 保活
```

### 数据库并发

```python
# settings.py
MYSQL_POOL_SIZE = 20  # MySQL 连接池大小
MYSQL_MAX_OVERFLOW = 10  # 最大溢出连接数
```

### 文件 IO 并发

```python
# settings.py
FILE_PIPELINE_THREADS = 10  # 文件写入线程数
```

## 爬虫运行很慢怎么办？

### 诊断步骤

#### 1. 检查日志

```bash
crawlo run myspider --log-level DEBUG
```

查看：
- 请求延迟是否正常
- 是否有大量重试
- 是否有错误异常

#### 2. 检查网络

```bash
# 测试目标网站响应时间
curl -o /dev/null -s -w '%{time_total}' https://example.com
```

#### 3. 检查资源使用

```bash
# Linux/Mac
top -p $(pgrep -f crawlo)

# Windows
任务管理器 -> 详细信息 -> 查找 Python 进程
```

#### 4. 检查队列状态

```python
# 在爬虫中打印队列状态
async def parse(self, response):
    queue_size = await self.crawler.scheduler.queue.size()
    self.logger.info(f"队列大小: {queue_size}")
```

### 常见原因和解决方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| **请求慢** | 目标网站响应慢 | 增加超时时间、使用代理 |
| **大量重试** | 网站反爬 | 降低并发、使用浏览器渲染 |
| **队列积压** | 生产慢于消费 | 增加数据库连接池、启用背压 |
| **CPU 高** | 选择器复杂 | 优化选择器、使用 CSS 代替 XPath |
| **内存高** | 队列过大 | 限制队列大小、启用背压 |

## 如何监控爬虫性能？

### 1. 启用统计

```python
# settings.py
STATS_ENABLED = True
STATS_INTERVAL = 60  # 每 60 秒打印一次
```

### 2. 查看统计信息

日志中会显示：
```
INFO: Crawled 1234 pages (123 pages/min)
INFO: Success rate: 98.5%
INFO: Average response time: 0.5s
```

### 3. 使用扩展监控

```python
# settings.py
EXTENSIONS = {
    'crawlo.extension.StatsExtension': 100,
    'crawlo.extension.PerformanceExtension': 200,
}
```

## 如何提高成功率？

### 1. 启用重试

```python
# settings.py
RETRY_ENABLED = True
RETRY_TIMES = 3
```

### 2. 使用代理

```python
# settings.py
PROXY_ENABLED = True
PROXY_LIST = ['http://proxy1:8080', 'http://proxy2:8080']
```

### 3. 设置合理的 User-Agent

```python
# settings.py
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'
RANDOM_UA = True  # 随机 UA
```

### 4. 添加随机延迟

```python
# settings.py
DOWNLOAD_DELAY = 1.0
RANDOMNESS = True
```

### 5. 使用浏览器渲染

```python
# settings.py
DYNAMIC_LOADER_ENABLED = True
```

## 大规模爬取的最佳实践？

### 1. 分批次爬取

```python
# 将 URL 列表分成多批
batches = [urls[i:i+1000] for i in range(0, len(urls), 1000)]

for batch in batches:
    # 创建爬虫处理这一批
    pass
```

### 2. 使用分布式模式

```python
config = CrawloConfig.distributed(
    project_name='myproject',
    redis_host='redis.example.com',
    concurrency=32
)
```

### 3. 监控和告警

```python
# settings.py
NOTIFICATION_ENABLED = True
NOTIFICATION_CHANNELS = ['feishu', 'email']
NOTIFICATION_ON_ERROR = True
```

### 4. 断点续爬

```python
# settings.py
CHECKPOINT_ENABLED = True
CHECKPOINT_INTERVAL = 300  # 每 5 分钟保存一次
```

---

**还有其他性能问题？** 查看 [调度指南](../guides/scheduling/) 或提交 [GitHub Issue](https://github.com/crawl-coder/Crawlo/issues)。
