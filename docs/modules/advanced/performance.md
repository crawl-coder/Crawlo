# 性能优化

Crawlo 框架提供了多种性能优化选项，帮助用户提高爬虫的爬取效率和资源利用率。本文档详细介绍各种性能优化策略和最佳实践。

## 概述

性能优化是爬虫开发中的重要环节，通过合理的配置和优化策略，可以显著提高爬取速度、降低资源消耗、增强系统稳定性。

### 优化目标

1. **提高爬取速度** - 在保证质量的前提下加快数据采集速度
2. **降低资源消耗** - 减少内存、CPU 和网络资源使用
3. **增强稳定性** - 提高系统在高负载下的稳定性
4. **优化扩展性** - 便于水平扩展以处理更大规模的数据

## 并发优化

### 调整并发数

并发数是影响爬虫性能的关键参数，需要根据目标网站的承受能力和本地资源情况进行调整。

```python
from crawlo.config import CrawloConfig

# 单机模式并发优化
config = CrawloConfig.standalone(
    concurrency=20,        # 并发请求数
    download_delay=0.5     # 下载延迟
)

# 分布式模式并发优化
config = CrawloConfig.distributed(
    concurrency=50,        # 并发请求数
    download_delay=0.1     # 下载延迟
)
```

### 并发策略

```python
# 根据网站响应时间调整并发数
# 响应快的网站可以使用更高并发
config = CrawloConfig.standalone(concurrency=50)

# 响应慢的网站使用较低并发
config = CrawloConfig.standalone(concurrency=10)

# 根据网络带宽调整并发数
# 高带宽环境
config = CrawloConfig.standalone(concurrency=100)

# 低带宽环境
config = CrawloConfig.standalone(concurrency=5)
```

## 内存优化

### 对象池技术

使用对象池减少对象创建和销毁的开销：

```python
import weakref

class RequestPool:
    def __init__(self):
        self._pool = weakref.WeakSet()
    
    def get_request(self, url, **kwargs):
        # 从池中获取或创建请求对象
        return Request(url, **kwargs)
    
    def release_request(self, request):
        # 释放请求对象到池中
        self._pool.add(request)

# 全局请求池
request_pool = RequestPool()
```

### 内存监控

```python
import psutil
import gc

class MemoryMonitor:
    def __init__(self, threshold_mb=500):
        self.threshold_mb = threshold_mb
    
    def check_memory(self):
        # 检查内存使用情况
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > self.threshold_mb:
            # 触发垃圾回收
            gc.collect()
            self.logger.warning(f"内存使用过高: {memory_mb:.2f}MB")
```

### 数据流优化

```python
# 使用生成器减少内存占用
def parse_large_response(response):
    # 逐行处理大响应
    for line in response.iter_lines():
        yield process_line(line)

# 批量处理数据
def batch_process_items(items, batch_size=100):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
```

## 网络优化

### 连接池优化

```python
# 配置连接池大小
config = CrawloConfig.standalone(
    downloader_type='aiohttp',
    aiohttp_connector_limit=100,      # 连接池大小
    aiohttp_connector_limit_per_host=20  # 每主机连接数限制
)

# HTTP/2 支持
config = CrawloConfig.standalone(
    downloader_type='httpx',
    http2=True  # 启用 HTTP/2
)
```

### DNS 缓存

```python
# 配置 DNS 缓存
config = CrawloConfig.standalone(
    dns_cache_timeout=600,  # DNS 缓存超时时间（秒）
    dns_cache_size=1000     # DNS 缓存大小
)
```

### 压缩支持

```python
# 启用响应压缩
config = CrawloConfig.standalone(
    accept_encoding=True  # 接受压缩编码
)

# 自定义请求头部
HEADERS = {
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (compatible; Crawlo/1.0)'
}
```

## 存储优化

### 批量写入

```python
class BatchPipeline:
    def __init__(self, settings):
        self.batch_size = 100
        self.buffer = []
    
    def process_item(self, item, spider):
        self.buffer.append(item)
        
        if len(self.buffer) >= self.batch_size:
            self.flush_buffer()
        
        return item
    
    def flush_buffer(self):
        # 批量写入数据库
        with self.db.transaction():
            for item in self.buffer:
                self.db.insert(item)
        self.buffer.clear()
```

### 异步存储

```python
import asyncio

class AsyncPipeline:
    def __init__(self, settings):
        self.queue = asyncio.Queue(maxsize=1000)
        self.worker_task = None
    
    async def open_spider(self, spider):
        # 启动异步写入工作者
        self.worker_task = asyncio.create_task(self.worker())
    
    async def close_spider(self, spider):
        # 等待队列处理完成
        await self.queue.join()
        if self.worker_task:
            self.worker_task.cancel()
    
    async def process_item(self, item, spider):
        # 异步处理数据项
        await self.queue.put(item)
        return item
    
    async def worker(self):
        while True:
            try:
                item = await self.queue.get()
                # 异步写入数据库
                await self.async_save_item(item)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
```

## CPU 优化

### 异步处理

```python
import asyncio
import concurrent.futures

class CPUIntensivePipeline:
    def __init__(self, settings):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    async def process_item(self, item, spider):
        # 将 CPU 密集型任务放到线程池中执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor, 
            self.cpu_intensive_task, 
            item
        )
        return result
    
    def cpu_intensive_task(self, item):
        # CPU 密集型处理逻辑
        return complex_processing(item)
```

### 缓存优化

```python
from functools import lru_cache

class OptimizedSpider(Spider):
    @lru_cache(maxsize=1000)
    def parse_url(self, url):
        # 缓存解析结果
        return urlparse(url)
    
    def parse(self, response):
        # 使用缓存的解析结果
        parsed = self.parse_url(response.url)
        # 处理逻辑
```

## I/O 优化

### 异步 I/O

```python
import aiofiles

class AsyncFilePipeline:
    async def open_spider(self, spider):
        self.file = await aiofiles.open('output.json', 'w')
    
    async def close_spider(self, spider):
        await self.file.close()
    
    async def process_item(self, item, spider):
        # 异步写入文件
        await self.file.write(json.dumps(item) + '\n')
        await self.file.flush()
        return item
```

### 内存映射文件

```python
import mmap

class MmapPipeline:
    def __init__(self, settings):
        self.file = open('output.dat', 'r+b')
        self.mmap = mmap.mmap(self.file.fileno(), 0)
    
    def close_spider(self, spider):
        self.mmap.close()
        self.file.close()
```

## 配置优化

### 性能相关配置

```python
# 高性能配置示例
PERFORMANCE_CONFIG = {
    # 并发配置
    'CONCURRENCY': 50,
    'DOWNLOAD_DELAY': 0.1,
    'DOWNLOAD_TIMEOUT': 30,
    
    # 下载器配置
    'DOWNLOADER_TYPE': 'aiohttp',
    'AIOHTTP_CONNECTOR_LIMIT': 100,
    'AIOHTTP_CONNECTOR_LIMIT_PER_HOST': 20,
    
    # 队列配置
    'SCHEDULER_MAX_QUEUE_SIZE': 100000,
    'QUEUE_PERSISTENCE': False,  # 内存队列不持久化
    
    # DNS 配置
    'DNS_CACHE_TIMEOUT': 600,
    'DNS_CACHE_SIZE': 1000,
    
    # 日志配置
    'LOG_LEVEL': 'WARNING',  # 减少日志输出
}
```

### 环境变量优化

```bash
# 设置高性能环境变量
export CRAWLO_CONCURRENCY=50
export CRAWLO_DOWNLOAD_DELAY=0.1
export CRAWLO_LOG_LEVEL=WARNING
export CRAWLO_AIOHTTP_CONNECTOR_LIMIT=100
```

## 监控和调优

### 性能监控

```python
import time
import psutil

class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()
    
    def get_stats(self):
        # 获取性能统计信息
        elapsed = time.time() - self.start_time
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        return {
            'elapsed_time': elapsed,
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'requests_per_second': self.request_count / elapsed if elapsed > 0 else 0
        }
```

### 性能分析

```python
import cProfile
import pstats

def profile_spider():
    # 性能分析
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 运行爬虫
    run_spider()
    
    profiler.disable()
    
    # 输出分析结果
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # 显示前20个最耗时的函数
```

## 最佳实践

### 1. 渐进式优化

```python
# 从基础配置开始
BASE_CONFIG = CrawloConfig.standalone(concurrency=10)

# 逐步增加并发数并监控性能
MEDIUM_CONFIG = CrawloConfig.standalone(concurrency=20)
HIGH_CONFIG = CrawloConfig.standalone(concurrency=50)

# 根据监控结果选择最优配置
```

### 2. 负载测试

```python
# 使用不同配置进行负载测试
def load_test(config, duration=60):
    start_time = time.time()
    request_count = 0
    
    # 运行指定时间
    while time.time() - start_time < duration:
        run_crawler(config)
        request_count += config.CONCURRENCY
    
    # 计算性能指标
    rps = request_count / duration
    return rps
```

### 3. 资源限制

```python
# 设置资源限制
import resource

def set_resource_limits():
    # 限制内存使用（1GB）
    resource.setrlimit(resource.RLIMIT_AS, (1024*1024*1024, 1024*1024*1024))
    
    # 限制 CPU 时间（1小时）
    resource.setrlimit(resource.RLIMIT_CPU, (3600, 3600))
```

通过以上性能优化策略，可以显著提升 Crawlo 爬虫的性能和效率。建议根据具体应用场景选择合适的优化方案，并通过监控和测试来验证优化效果。