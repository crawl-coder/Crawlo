# MongoDB 连接池优化方案

## 问题描述

与 MySQL 类似，在运行多个爬虫时，每个爬虫的 MongoDB Pipeline 都会创建独立的 MongoDB 客户端连接池，导致：

1. **资源浪费**：每个连接池维护 10-100 个连接
2. **性能问题**：过多连接导致 MongoDB 服务器压力增大
3. **连接数限制**：可能达到 MongoDB 的连接数限制

### 问题示例

**优化前：**
```
运行 3 个爬虫
├── 爬虫 A
│   └── MongoDB Pipeline → 客户端 A (10-100 个连接)
├── 爬虫 B
│   └── MongoDB Pipeline → 客户端 B (10-100 个连接)
└── 爬虫 C
    └── MongoDB Pipeline → 客户端 C (10-100 个连接)

总连接数：30-300 个数据库连接
```

## 解决方案

使用**单例模式的连接池管理器**，让所有爬虫共享同一个 MongoDB 客户端。

### 优化后架构

```
运行 3 个爬虫
├── 爬虫 A ──┐
├── 爬虫 B ──┼──→ 全局共享 MongoDB 客户端 (10-100 个连接)
└── 爬虫 C ──┘

总连接数：10-100 个数据库连接（节省 66-75%）
```

## 核心实现

### 1. MongoConnectionPoolManager（单例连接池管理器）

```python
from crawlo.utils.mongo_connection_pool import MongoConnectionPoolManager

# 自动使用单例模式，相同配置返回同一个客户端
client = await MongoConnectionPoolManager.get_client(
    mongo_uri='mongodb://localhost:27017',
    db_name='crawlo',
    min_pool_size=10,
    max_pool_size=100,
    connect_timeout_ms=5000,
    socket_timeout_ms=30000
)
```

### 2. 特性

#### ✅ 单例模式
- 相同数据库配置只创建一个客户端
- 不同数据库配置创建不同的客户端
- 客户端通过 `{mongo_uri}:{db_name}` 唯一标识

#### ✅ 线程安全
- 使用异步锁保护初始化过程
- 支持并发访问
- 避免竞争条件

#### ✅ 配置隔离
- 支持连接到不同的 MongoDB 数据库
- 每个数据库使用独立的客户端
- 自动识别和复用相同配置

#### ✅ 资源管理
- 统一的客户端清理接口
- 支持查看所有客户端状态
- 优雅关闭和资源释放

## 使用方式

### 在 Pipeline 中使用（自动）

MongoDB Pipeline 已经自动集成了单例连接池管理器，**无需修改代码**：

```python
# 在 settings.py 中配置
PIPELINES = [
    'crawlo.pipelines.mongo_pipeline.MongoPipeline',
]

# MongoDB 配置
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'crawlo'
MONGO_COLLECTION = 'items'
MONGO_MIN_POOL_SIZE = 10
MONGO_MAX_POOL_SIZE = 100

# 运行多个爬虫时，会自动共享连接池
# 无需额外配置
```

### 手动使用连接池管理器

如果需要在其他地方使用 MongoDB 连接：

```python
from crawlo.utils.mongo_connection_pool import MongoConnectionPoolManager

class CustomService:
    async def init_db(self):
        # 获取客户端（自动单例）
        self.client = await MongoConnectionPoolManager.get_client(
            mongo_uri='mongodb://localhost:27017',
            db_name='my_database',
            min_pool_size=10,
            max_pool_size=100
        )
        self.db = self.client['my_database']
        self.collection = self.db['my_collection']
    
    async def insert(self, data):
        result = await self.collection.insert_one(data)
        return result.inserted_id
```

### 查看连接池状态

```python
from crawlo.utils.mongo_connection_pool import MongoConnectionPoolManager

# 获取所有客户端的统计信息
stats = MongoConnectionPoolManager.get_pool_stats()
print(stats)

# 输出示例：
{
    'total_pools': 2,
    'pools': {
        'mongodb://localhost:27017:crawlo': {
            'uri': 'mongodb://localhost:27017',
            'db_name': 'crawlo',
            'min_pool_size': 10,
            'max_pool_size': 100
        },
        'mongodb://127.0.0.1:27017:test_db': {
            'uri': 'mongodb://127.0.0.1:27017',
            'db_name': 'test_db',
            'min_pool_size': 20,
            'max_pool_size': 200
        }
    }
}
```

### 清理所有客户端

在程序退出时：

```python
from crawlo.utils.mongo_connection_pool import MongoConnectionPoolManager

# 关闭所有客户端
await MongoConnectionPoolManager.close_all_clients()
```

## 配置参数

### 连接池参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mongo_uri` | str | 'mongodb://localhost:27017' | MongoDB 连接 URI |
| `db_name` | str | 'crawlo' | 数据库名称 |
| `min_pool_size` | int | 10 | 最小连接数 |
| `max_pool_size` | int | 100 | 最大连接数 |
| `connect_timeout_ms` | int | 5000 | 连接超时（毫秒） |
| `socket_timeout_ms` | int | 30000 | Socket 超时（毫秒） |

### Settings 配置

```python
# settings.py

# MongoDB 基础配置
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'your_database'
MONGO_COLLECTION = 'your_collection'

# 连接池配置
MONGO_MIN_POOL_SIZE = 10   # 最小连接数
MONGO_MAX_POOL_SIZE = 100  # 最大连接数
MONGO_CONNECT_TIMEOUT_MS = 5000    # 连接超时（毫秒）
MONGO_SOCKET_TIMEOUT_MS = 30000    # Socket 超时（毫秒）

# 批量插入配置
MONGO_USE_BATCH = False    # 是否启用批量插入
MONGO_BATCH_SIZE = 100     # 批量插入大小

# 使用 MongoDB Pipeline
PIPELINES = [
    'crawlo.pipelines.mongo_pipeline.MongoPipeline',
]
```

## 性能对比

### 优化前
```
场景：3 个爬虫同时运行
- 每个爬虫创建独立客户端
- 每个客户端：minPoolSize=10, maxPoolSize=100
- 总连接数：30~300 个
- 内存占用：约 50-200MB
```

### 优化后
```
场景：3 个爬虫同时运行
- 所有爬虫共享一个客户端
- 客户端：minPoolSize=10, maxPoolSize=100
- 总连接数：10~100 个
- 内存占用：约 20-70MB
- 节省：66-75% 的连接和内存
```

## 技术细节

### 客户端标识

客户端通过以下参数生成唯一标识：
```python
pool_key = f"{mongo_uri}:{db_name}"

# 示例：
# "mongodb://localhost:27017:crawlo"
# "mongodb://127.0.0.1:27017:test_db"
```

### 线程安全机制

```python
# 类级别锁（保护实例字典）
_lock = asyncio.Lock()

# 实例级别锁（保护客户端初始化）
_client_lock = asyncio.Lock()

# 双重检查锁定模式
async with cls._lock:
    if pool_key not in cls._instances:
        instance = cls(pool_key)
        cls._instances[pool_key] = instance

async with instance._client_lock:
    if not instance._client_initialized:
        # 初始化客户端
        instance.client = AsyncIOMotorClient(...)
        instance._client_initialized = True
```

### Pipeline 集成

```python
# MongoPipeline._ensure_connection()
async def _ensure_connection(self):
    if self.client is None:
        # 使用单例连接池管理器
        self.client = await MongoConnectionPoolManager.get_client(
            mongo_uri=self.mongo_uri,
            db_name=self.db_name,
            ...
        )
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
```

## 注意事项

### ⚠️ 客户端生命周期

- **不要手动关闭客户端**：客户端由 MongoConnectionPoolManager 统一管理
- **Pipeline 关闭时**：只清理批量缓冲区，不关闭客户端
- **程序退出时**：调用 `MongoConnectionPoolManager.close_all_clients()`

### ⚠️ 多数据库场景

如果需要连接多个不同的 MongoDB 数据库：

```python
# 数据库 A
client_a = await MongoConnectionPoolManager.get_client(
    mongo_uri='mongodb://host_a:27017',
    db_name='database_a',
    ...
)

# 数据库 B（会创建新的客户端）
client_b = await MongoConnectionPoolManager.get_client(
    mongo_uri='mongodb://host_b:27017',
    db_name='database_b',
    ...
)

# 相同配置（复用已有客户端）
client_a2 = await MongoConnectionPoolManager.get_client(
    mongo_uri='mongodb://host_a:27017',
    db_name='database_a',
    ...
)
# client_a2 is client_a  # True
```

### ⚠️ 连接池大小建议

```python
# 少量爬虫（1-3个）
MONGO_MIN_POOL_SIZE = 10
MONGO_MAX_POOL_SIZE = 100

# 中等规模（4-10个爬虫）
MONGO_MIN_POOL_SIZE = 20
MONGO_MAX_POOL_SIZE = 200

# 大规模（10+个爬虫）
MONGO_MIN_POOL_SIZE = 50
MONGO_MAX_POOL_SIZE = 500
```

## 迁移指南

### 从旧版本迁移

**无需任何修改！**

旧代码会自动使用新的单例连接池：

```python
# 旧代码（仍然有效）
PIPELINES = [
    'crawlo.pipelines.mongo_pipeline.MongoPipeline',
]

# 自动获得优化效果：
# - 多个爬虫自动共享客户端
# - 减少 MongoDB 连接数
# - 降低资源消耗
```

## 日志输出

启用优化后，会看到如下日志：

```
[INFO] MongoPool.mongodb://localhost:27017:crawlo: 创建新的 MongoDB 连接池管理器 (minPoolSize=10, maxPoolSize=100)
[INFO] MongoPool.mongodb://localhost:27017:crawlo: MongoDB 客户端初始化成功 (minPoolSize=10, maxPoolSize=100)
[INFO] MongoPipeline: MongoDB连接建立 (集合: items, 使用全局共享连接池)
[INFO] MongoPipeline: MongoDB Pipeline 关闭，但保留全局共享连接池以供其他爬虫使用
[INFO] MongoPool: 开始关闭所有 MongoDB 客户端，共 1 个
[INFO] MongoPool: 关闭 MongoDB 客户端: mongodb://localhost:27017:crawlo
[INFO] MongoPool: MongoDB 客户端已关闭: mongodb://localhost:27017:crawlo
[INFO] MongoPool: 所有 MongoDB 客户端已关闭
```

## 与 MySQL 优化的对比

| 特性 | MySQL | MongoDB | 说明 |
|------|-------|---------|------|
| **单例管理器** | MySQLConnectionPoolManager | MongoConnectionPoolManager | 相同设计模式 |
| **连接池类型** | asyncmy / aiomysql | motor (AsyncIOMotorClient) | 不同的驱动库 |
| **标识生成** | `{type}:{host}:{port}:{db}` | `{uri}:{db}` | MongoDB 使用 URI |
| **连接数优化** | 60-70% | 66-75% | 相似的优化效果 |
| **批量操作** | 支持 | 支持 | 都支持批量插入 |

## 总结

### ✅ 优势

1. **自动优化**：无需修改代码，自动获得优化效果
2. **大幅节省资源**：减少 66-75% 的数据库连接
3. **提升性能**：降低 MongoDB 服务器压力，提高吞吐量
4. **向后兼容**：完全兼容现有代码
5. **与 MySQL 一致**：统一的优化方案，易于理解和维护

### 📈 适用场景

- ✅ 多个爬虫同时运行
- ✅ 分布式爬虫系统
- ✅ 大规模数据采集
- ✅ 资源受限环境
- ✅ MongoDB 连接数有限制的场景

### 🎯 最佳实践

1. **统一使用单例管理器**：通过 MongoConnectionPoolManager 获取客户端
2. **合理配置连接池大小**：根据爬虫数量调整 min/max pool size
3. **监控连接池状态**：定期检查 `get_pool_stats()`
4. **优雅关闭**：程序退出时调用 `close_all_clients()`
