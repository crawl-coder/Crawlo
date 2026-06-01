# Crawlo Pipeline 设计：数据清洗到入库的最佳实践

> 数据爬下来只是第一步，清洗和存储才是真功夫。

---

## Pipeline 是什么？

Pipeline 是 Crawlo 的数据处理管道，负责将 Spider 产出的 Item 进行清洗、验证、去重、存储。

```
Spider yield Item → Processor → Pipeline 1 → Pipeline 2 → ... → 存储
                                  │           │
                              清洗/验证     去重/过滤
```

**核心设计**：
- 每个 Pipeline 是一个独立的处理器
- Pipeline 按优先级排序（数字越小越先执行）
- 任意 Pipeline 可丢弃 Item（返回 None）
- 批量写入优化（攒够 N 条再入库）

---

## 内置 Pipeline 全家桶

Crawlo 内置 10+ 数据管道，覆盖常见存储需求：

### 文件类

| Pipeline | 用途 | 配置 |
|----------|------|------|
| `CsvPipeline` | CSV 文件 | `CSV_FILE='output.csv'` |
| `JsonLinesPipeline` | JSON Lines 文件 | `JSON_FILE='output.jsonl'` |

### SQL 数据库

| Pipeline | 用途 | 配置 |
|----------|------|------|
| `MySQLPipeline` | MySQL | `MYSQL_HOST/PORT/DATABASE/USER/PASSWORD` |
| `PostgreSQLPipeline` | PostgreSQL | `POSTGRES_HOST/PORT/...` |
| `ClickHousePipeline` | ClickHouse | `CLICKHOUSE_HOST/PORT/...` |
| `SQLitePipeline` | SQLite | `SQLITE_DATABASE='data.db'` |

### 文档数据库

| Pipeline | 用途 | 配置 |
|----------|------|------|
| `MongoPipeline` | MongoDB | `MONGO_URI/MONGO_DATABASE` |
| `ElasticsearchPipeline` | ES | `ELASTICSEARCH_HOSTS/INDEX` |
| `HBasePipeline` | HBase | `HBASE_HOST/PORT/TABLE` |

### 去重类

| Pipeline | 用途 | 配置 |
|----------|------|------|
| `MemoryDedupPipeline` | 内存去重 | 零配置 |
| `RedisDedupPipeline` | Redis 去重 | `REDIS_URL` |

### 通用

| Pipeline | 用途 |
|----------|------|
| `GenericSQLPipeline` | 通用 SQL 管道（自动建表） |
| `GenericDocPipeline` | 通用文档数据库管道 |

---

## 使用方式

### 单个 Pipeline

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.CsvPipeline': 300,
}
CSV_FILE = 'output.csv'
```

### 多个 Pipeline 串联

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 100,   # 先去重
    'crawlo.pipelines.MySQLPipeline': 300,         # 再入库
}
```

Pipeline 按优先级数字从小到大执行：
1. RedisDedupPipeline（100）→ 检查是否重复，重复则丢弃
2. MySQLPipeline（300）→ 写入 MySQL

### 在 Spider 中指定

```python
class MySpider(crawlo.Spider):
    name = 'my'
    custom_settings = {
        'ITEM_PIPELINES': {
            'crawlo.pipelines.MongoPipeline': 300,
        },
        'MONGO_URI': 'mongodb://localhost:27017',
        'MONGO_DATABASE': 'mydb',
    }
```

---

## 自定义 Pipeline

### 最简 Pipeline

```python
# pipelines.py
from crawlo.pipelines import BasePipeline

class FilterEmptyPipeline(BasePipeline):
    """过滤空字段"""

    def process_item(self, item, spider):
        # 过滤掉值为 None 或空字符串的字段
        cleaned = {k: v for k, v in item.items() if v is not None and v != ''}
        return cleaned  # 返回处理后的 item
        # return None   # 返回 None 则丢弃该 item
```

### 异步 Pipeline

```python
class AsyncValidationPipeline(BasePipeline):
    """异步验证 Pipeline"""

    async def process_item(self, item, spider):
        # 异步验证（如调用远程 API 校验）
        is_valid = await self.validate(item)
        if not is_valid:
            return None  # 丢弃
        return item

    async def validate(self, item):
        # 调用远程验证服务
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.example.com/validate', json=item) as resp:
                return resp.status == 200
```

### 批量写入 Pipeline

```python
class BatchMySQLPipeline(BasePipeline):
    """批量写入 MySQL（性能优化）"""

    def __init__(self):
        self.buffer = []
        self.batch_size = 100

    async def process_item(self, item, spider):
        self.buffer.append(item)
        if len(self.buffer) >= self.batch_size:
            await self.flush(spider)
        return item

    async def flush(self, spider):
        if not self.buffer:
            return
        # 批量 INSERT
        await self._batch_insert(self.buffer)
        self.buffer.clear()

    async def close_spider(self, spider):
        """Spider 关闭时刷新剩余数据"""
        await self.flush(spider)
```

---

## Pipeline 最佳实践

### 1. 去重放最前面

```python
ITEM_PIPELINES = {
    'crawlo.pipelines.RedisDedupPipeline': 100,  # 优先级最低的数字
    'crawlo.pipelines.MySQLPipeline': 300,
}
```

去重应尽早执行，避免重复数据进入后续 Pipeline。

### 2. 数据清洗在存储前

```python
ITEM_PIPELINES = {
    'pipelines.CleanPipeline': 200,               # 清洗
    'pipelines.ValidatePipeline': 250,             # 验证
    'crawlo.pipelines.MySQLPipeline': 300,         # 存储
}
```

### 3. 大批量使用批量写入

内置的 MySQL/PostgreSQL/MongoDB Pipeline 都支持批量写入：

```python
MYSQL_BATCH_SIZE = 500     # 每 500 条写入一次（默认 500）
MYSQL_BATCH_TIMEOUT = 90   # 或 90 秒写入一次（取先到者）
```

### 4. 异常处理

Pipeline 中的异常不会中断整个爬虫：

```python
class SafePipeline(BasePipeline):
    async def process_item(self, item, spider):
        try:
            # 可能失败的操作
            await self.risky_operation(item)
            return item
        except Exception as e:
            spider.logger.error(f"Pipeline error: {e}")
            return None  # 丢弃出错的 item，继续处理后续
```

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
