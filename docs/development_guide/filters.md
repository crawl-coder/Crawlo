# 过滤器

过滤器是 Crawlo 框架中用于请求去重的组件。它们可以防止爬虫重复抓取相同的 URL，提高爬虫效率并减少服务器负载。

## 基础过滤器类

所有过滤器都应该继承 [BaseFilter](file:///d%3A/dowell/projects/Crawlo/crawlo/filters/__init__.py#L18-L87) 类。

### 类: BaseFilter

```python
class BaseFilter(ABC):
    def __init__(self, logger, stats, debug: bool = False):
        # Initialize the base filter
        pass
    
    async def request_seen(self, request):
        # Check if a request has been seen before
        pass
    
    async def mark_request_seen(self, request):
        # Mark a request as seen
        pass
    
    async def clear(self):
        # Clear the filter
        pass
```

#### 参数

- `logger`: 日志器实例
- `stats`: 统计信息存储
- `debug` (bool): 是否启用调试模式

#### 方法

##### `__init__(self, logger, stats, debug)`

使用日志器、统计信息和调试模式初始化基础过滤器。

**参数:**
- `logger`: 日志器实例
- `stats`: 统计信息存储
- `debug` (bool): 是否启用调试模式

##### `request_seen(self, request)`

检查请求是否已经被处理过。

**参数:**
- `request` (Request): 要检查的请求

**返回:**
- `Coroutine`: 解析为布尔值的协程，表示请求是否已经被处理过

##### `mark_request_seen(self, request)`

标记请求为已处理。

**参数:**
- `request` (Request): 要标记的请求

**返回:**
- `Coroutine`: 当请求被标记为已处理时解析的协程

##### `clear(self)`

清空过滤器中的所有数据。

**返回:**
- `Coroutine`: 当过滤器被清空时解析的协程

## 内存过滤器

### 类: MemoryFilter

基于内存的高效请求去重过滤器，适用于单机爬虫。

```python
class MemoryFilter(BaseFilter):
    def __init__(self, crawler):
        # Initialize the memory filter
        pass
```

#### 特点

- 高性能: 基于 Python set() 的 O(1) 查找效率
- 内存优化: 支持弱引用临时存储
- 统计信息: 提供详细的性能统计
- 线程安全: 支持多线程并发访问

#### 适用场景

- 单机爬虫
- 中小规模数据集
- 对性能要求较高的场景

#### 配置参数

```python
# 内存过滤器最大容量
MEMORY_FILTER_MAX_CAPACITY = 1000000

# 内存过滤器清理阈值
MEMORY_FILTER_CLEANUP_THRESHOLD = 0.8
```

## Redis 过滤器

### 类: AioRedisFilter

基于 Redis 集合实现的异步请求去重过滤器，适用于分布式爬虫。

```python
class AioRedisFilter(BaseFilter):
    def __init__(self, crawler, module_name="default"):
        # Initialize the Redis filter
        pass
    
    async def request_seen(self, request):
        # Check if a request has been seen before using Redis
        pass
    
    async def mark_request_seen(self, request):
        # Mark a request as seen using Redis
        pass
    
    async def clear(self):
        # Clear the Redis filter
        pass
```

#### 参数

- `crawler` (Crawler): 与过滤器关联的爬虫实例
- `module_name` (str, optional): 用于 Redis 键生成的模块名称。默认为 "default"

#### 特点

- 分布式支持: 多节点共享去重数据
- TTL 支持: 自动过期清理
- 高性能: 使用 Redis pipeline 优化
- 容错设计: 网络异常自动重试

#### 适用场景

- 分布式爬虫系统
- 大规模数据处理
- 需要持久化去重的场景

#### 配置参数

```python
# Redis 配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Redis 过滤器配置
REDIS_TTL = 86400  # 指纹过期时间（秒）
CLEANUP_FP = False  # 关闭时是否清理指纹
```

## 过滤器管理器

### 类: FilterManager

用于管理不同类型的过滤器实现。

```python
class FilterManager(object):
    def __init__(self, crawler):
        # Initialize the filter manager
        pass
    
    def create_filter(self, filter_type, *args, **kwargs):
        # Create a filter of the specified type
        pass
    
    async def request_seen(self, request):
        # Check if a request has been seen by the active filter
        pass
    
    async def mark_request_seen(self, request):
        # Mark a request as seen by the active filter
        pass
```

#### 方法

##### `__init__(self, crawler)`

使用爬虫实例初始化过滤器管理器。

**参数:**
- `crawler` (Crawler): 与过滤器管理器关联的爬虫实例

##### `create_filter(self, filter_type, *args, **kwargs)`

创建指定类型的过滤器。

**参数:**
- `filter_type` (str): 要创建的过滤器类型 ('memory' 或 'redis')
- `*args`: 传递给过滤器构造函数的位置参数
- `**kwargs`: 传递给过滤器构造函数的关键字参数

**返回:**
- `BaseFilter`: 指定类型的过滤器实例

##### `request_seen(self, request)`

检查请求是否已被活动过滤器处理过。

**参数:**
- `request` (Request): 要检查的请求

**返回:**
- `Coroutine`: 解析为布尔值的协程，表示请求是否已经被处理过

##### `mark_request_seen(self, request)`

标记请求为已被活动过滤器处理。

**参数:**
- `request` (Request): 要标记的请求

**返回:**
- `Coroutine`: 当请求被标记为已处理时解析的协程

## 配置过滤器

在 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 中配置过滤器：

### 单机模式

```python
# 使用内存过滤器
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFilter'

# 或使用内存+文件持久化过滤器
FILTER_CLASS = 'crawlo.filters.memory_filter.MemoryFileFilter'

# 过滤器调试模式
FILTER_DEBUG = False
```

### 分布式模式

```python
# 使用 Redis 过滤器
FILTER_CLASS = 'crawlo.filters.aioredis_filter.AioRedisFilter'

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 2
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Redis 过滤器配置
REDIS_TTL = 86400  # 24小时
CLEANUP_FP = False  # 关闭后保留指纹
```

## 创建自定义过滤器

要创建自定义过滤器，需要继承 [BaseFilter](file:///d%3A/dowell/projects/Crawlo/crawlo/filters/__init__.py#L18-L87) 类并实现必要的方法。

### 示例：数据库过滤器

```python
from crawlo.filters import BaseFilter
import aiomysql

class DatabaseFilter(BaseFilter):
    def __init__(self, crawler):
        # 初始化日志和统计
        debug = crawler.settings.get_bool('FILTER_DEBUG', False)
        logger = get_logger(
            self.__class__.__name__,
            crawler.settings.get('LOG_LEVEL', 'INFO')
        )
        super().__init__(logger, crawler.stats, debug)
        
        # 初始化数据库连接
        self.pool = None
        self.table_name = crawler.settings.get('FILTER_TABLE_NAME', 'request_fingerprints')
    
    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)
    
    async def _get_db_pool(self):
        """获取数据库连接池"""
        if self.pool is None:
            self.pool = await aiomysql.create_pool(
                host=self.crawler.settings.get('DB_HOST', 'localhost'),
                port=self.crawler.settings.get_int('DB_PORT', 3306),
                user=self.crawler.settings.get('DB_USER', 'root'),
                password=self.crawler.settings.get('DB_PASSWORD', ''),
                db=self.crawler.settings.get('DB_NAME', 'crawler'),
                loop=self.crawler.loop
            )
        return self.pool
    
    async def add_fingerprint(self, fp: str) -> None:
        """添加请求指纹到数据库"""
        pool = await self._get_db_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    sql = f"""
                        INSERT IGNORE INTO {self.table_name} (fingerprint, created_at)
                        VALUES (%s, NOW())
                    """
                    await cursor.execute(sql, (fp,))
                    await conn.commit()
                except Exception as e:
                    self.logger.error(f"添加指纹失败: {e}")
                    await conn.rollback()
    
    async def __contains__(self, item: str) -> bool:
        """检查指纹是否存在于数据库中"""
        pool = await self._get_db_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    sql = f"SELECT 1 FROM {self.table_name} WHERE fingerprint = %s LIMIT 1"
                    await cursor.execute(sql, (item,))
                    result = await cursor.fetchone()
                    return result is not None
                except Exception as e:
                    self.logger.error(f"检查指纹失败: {e}")
                    return False
    
    async def clear(self) -> None:
        """清空数据库中的所有指纹"""
        pool = await self._get_db_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    sql = f"TRUNCATE TABLE {self.table_name}"
                    await cursor.execute(sql)
                    await conn.commit()
                    self.logger.info("已清空所有指纹")
                except Exception as e:
                    self.logger.error(f"清空指纹失败: {e}")
                    await conn.rollback()
    
    async def close(self) -> None:
        """关闭过滤器并清理资源"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
```

## 最佳实践

1. **选择合适的过滤器类型**：
   - 单机爬虫使用 MemoryFilter
   - 分布式爬虫使用 AioRedisFilter
   - 需要持久化的场景考虑 MemoryFileFilter 或自定义数据库过滤器

2. **合理配置参数**：
   - 根据数据规模调整内存过滤器容量
   - 为 Redis 过滤器设置合适的 TTL
   - 启用调试模式进行问题排查

3. **性能优化**：
   - 使用 Redis pipeline 批量操作
   - 合理设置连接池大小
   - 避免频繁的网络请求

4. **错误处理**：
   - 妥善处理网络异常
   - 在异常情况下避免丢失请求
   - 记录详细的错误日志

5. **资源管理**：
   - 正确关闭数据库连接和 Redis 连接
   - 定期清理过期数据
   - 监控内存和存储使用情况

6. **监控和统计**：
   - 启用统计信息收集
   - 定期检查重复率
   - 监控过滤器性能