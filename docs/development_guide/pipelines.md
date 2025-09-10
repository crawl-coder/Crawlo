# 管道

管道是 Crawlo 框架中用于处理抓取到的数据项的组件。每个管道可以对数据项进行处理、转换或存储。

## 管道管理器

[PipelineManager](file:///d%3A/dowell/projects/Crawlo/crawlo/pipelines/pipeline_manager.py#L12-L55) 负责管理所有管道组件，并协调它们的执行。

### 类: PipelineManager

```python
class PipelineManager(object):
    def __init__(self, crawler, pipeline_classes):
        # Initialize the pipeline manager
        pass
    
    async def process_item(self, item, spider):
        # Process an item through all pipelines
        pass
```

#### 参数

- `crawler` (Crawler): 与管道管理器关联的爬虫实例
- `pipeline_classes` (list): 要加载的管道类路径列表

#### 方法

##### `__init__(self, crawler, pipeline_classes)`

使用爬虫和管道类初始化管道管理器。

**参数:**
- `crawler` (Crawler): 与管道管理器关联的爬虫实例
- `pipeline_classes` (list): 要加载的管道类路径列表

##### `process_item(self, item, spider)`

通过所有管道顺序处理数据项。

**参数:**
- `item` (Item): 要处理的数据项
- `spider` (Spider): 生成数据项的爬虫

**返回:**
- `Coroutine`: 解析为处理后的数据项的协程

## 基础管道类

所有管道都应该继承 [BasePipeline](file:///d%3A/dowell/projects/Crawlo/crawlo/pipelines/__init__.py#L6-L15) 类。

### 类: BasePipeline

```python
class BasePipeline:
    def process_item(self, item: Item, spider):
        raise NotImplementedError

    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

#### 方法

##### `process_item(self, item, spider)`

处理数据项的核心方法。

**参数:**
- `item` (Item): 要处理的数据项
- `spider` (Spider): 当前爬虫实例

**返回:**
- 处理后的数据项，或者 None（表示丢弃该数据项）

##### `create_instance(cls, crawler)`

创建管道实例的类方法。

**参数:**
- `crawler` (Crawler): 爬虫实例

**返回:**
- 管道实例

## 内置管道

Crawlo 提供了多种内置管道：

### 控制台管道 (ConsolePipeline)

将数据项输出到控制台。

### JSON 管道 (JsonPipeline)

将数据项保存为 JSON 格式文件。

### CSV 管道 (CsvPipeline)

将数据项保存为 CSV 格式文件。

### MySQL 管道 (AsyncmyMySQLPipeline)

将数据项存储到 MySQL 数据库。

### MongoDB 管道 (MongoPipeline)

将数据项存储到 MongoDB 数据库。

### 内存去重管道 (MemoryDedupPipeline)

使用内存集合进行数据项去重。

### Redis 去重管道 (RedisDedupPipeline)

使用 Redis 集合进行数据项去重。

### Bloom Filter 去重管道 (BloomDedupPipeline)

使用 Bloom Filter 进行数据项去重。

### 数据库去重管道 (DatabaseDedupPipeline)

使用数据库进行数据项去重。

## 创建自定义管道

要创建自定义管道，需要继承 [BasePipeline](file:///d%3A/dowell/projects/Crawlo/crawlo/pipelines/__init__.py#L6-L15) 类并实现 [process_item](file:///d%3A/dowell/projects/Crawlo/crawlo/pipelines/pipeline_manager.py#L49-L55) 方法。

### 示例：数据清洗管道

```python
from crawlo.pipelines import BasePipeline
from crawlo.items import Item

class DataCleaningPipeline(BasePipeline):
    def process_item(self, item: Item, spider):
        # 清洗数据项
        # 移除字符串两端的空白字符
        for key, value in item.items():
            if isinstance(value, str):
                item[key] = value.strip()
        
        # 验证必填字段
        required_fields = ['title', 'price']
        for field in required_fields:
            if not item.get(field):
                spider.logger.warning(f"Missing required field: {field}")
                return None  # 丢弃数据项
        
        # 转换价格字段为浮点数
        if 'price' in item:
            try:
                item['price'] = float(item['price'])
            except ValueError:
                spider.logger.warning(f"Invalid price value: {item['price']}")
                return None  # 丢弃数据项
        
        return item
    
    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

### 示例：数据验证管道

```python
from crawlo.pipelines import BasePipeline
from crawlo.items import Item
import re

class DataValidationPipeline(BasePipeline):
    def process_item(self, item: Item, spider):
        # 验证邮箱格式
        if 'email' in item:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, item['email']):
                spider.logger.warning(f"Invalid email format: {item['email']}")
                return None  # 丢弃数据项
        
        # 验证电话号码格式
        if 'phone' in item:
            phone_pattern = r'^\+?1?-?\.?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})$'
            if not re.match(phone_pattern, item['phone']):
                spider.logger.warning(f"Invalid phone format: {item['phone']}")
                return None  # 丢弃数据项
        
        # 验证价格范围
        if 'price' in item:
            price = item['price']
            if price < 0 or price > 1000000:
                spider.logger.warning(f"Price out of range: {price}")
                return None  # 丢弃数据项
        
        return item
    
    @classmethod
    def create_instance(cls, crawler):
        return cls()
```

### 示例：数据库存储管道

```python
from crawlo.pipelines import BasePipeline
from crawlo.items import Item
import aiomysql

class DatabaseStoragePipeline(BasePipeline):
    def __init__(self, crawler):
        self.crawler = crawler
        self.pool = None
    
    async def open_spider(self, spider):
        # 爬虫启动时创建数据库连接池
        self.pool = await aiomysql.create_pool(
            host=self.crawler.settings.get('DB_HOST', 'localhost'),
            port=self.crawler.settings.get_int('DB_PORT', 3306),
            user=self.crawler.settings.get('DB_USER', 'root'),
            password=self.crawler.settings.get('DB_PASSWORD', ''),
            db=self.crawler.settings.get('DB_NAME', 'crawler'),
            loop=self.crawler.loop
        )
        spider.logger.info("Database connection pool created")
    
    async def close_spider(self, spider):
        # 爬虫关闭时关闭数据库连接池
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            spider.logger.info("Database connection pool closed")
    
    async def process_item(self, item: Item, spider):
        # 将数据项存储到数据库
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # 插入数据
                    sql = """
                        INSERT INTO products (title, price, description)
                        VALUES (%s, %s, %s)
                    """
                    await cursor.execute(sql, (
                        item.get('title'),
                        item.get('price'),
                        item.get('description')
                    ))
                    await conn.commit()
                    spider.logger.info(f"Item stored in database: {item.get('title')}")
                except Exception as e:
                    spider.logger.error(f"Database error: {e}")
                    await conn.rollback()
        
        return item
    
    @classmethod
    def create_instance(cls, crawler):
        return cls(crawler)
```

## 配置管道

在 [settings.py](file:///d%3A/dowell/projects/Crawlo/examples/telecom_licenses_distributed/telecom_licenses_distributed/settings.py) 中配置管道：

```python
PIPELINES = [
    # 数据清洗管道
    'myproject.pipelines.DataCleaningPipeline',
    
    # 数据验证管道
    'myproject.pipelines.DataValidationPipeline',
    
    # 控制台输出管道
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    
    # JSON 文件存储管道
    'crawlo.pipelines.json_pipeline.JsonPipeline',
    
    # 数据库存储管道
    'myproject.pipelines.DatabaseStoragePipeline',
]
```

## 管道执行顺序

管道按照在 [PIPELINES](file:///d%3A/dowell/projects/Crawlo/crawlo/settings/default_settings.py#L104-L104) 列表中的顺序执行。每个管道的 [process_item](file:///d%3A/dowell/projects/Crawlo/crawlo/pipelines/pipeline_manager.py#L49-L55) 方法都会被调用，除非某个管道返回 None（表示丢弃数据项）。

## 最佳实践

1. **单一职责**：每个管道应该有明确的单一职责
2. **异常处理**：在管道中妥善处理异常，避免影响整个爬虫
3. **资源管理**：正确管理数据库连接等资源
4. **性能考虑**：避免在管道中执行耗时操作，可以考虑异步处理
5. **日志记录**：适当记录管道的操作日志
6. **配置管理**：通过设置文件配置管道行为
7. **测试**：为管道编写单元测试
8. **数据验证**：在管道中验证数据的完整性和正确性