# MySQL 连接池优化方案

## 问题描述

在运行多个爬虫时，每个爬虫的 MySQL Pipeline 都会创建独立的数据库连接池，导致：

1. **资源浪费**：每个连接池维护 3-10 个连接
2. **性能问题**：过多连接导致数据库压力增大
3. **连接数限制**：可能达到 MySQL 的 max_connections 限制

### 问题示例

**优化前：**
```
运行 3 个爬虫
├── 爬虫 A
│   └── MySQL Pipeline → 连接池 A (3-10 个连接)
├── 爬虫 B
│   └── MySQL Pipeline → 连接池 B (3-10 个连接)
└── 爬虫 C
    └── MySQL Pipeline → 连接池 C (3-10 个连接)

总连接数：9~30 个数据库连接
```

## 解决方案

使用**单例模式的连接池管理器**，让所有爬虫共享同一个 MySQL 连接池。

### 优化后架构

```
运行 3 个爬虫
├── 爬虫 A ──┐
├── 爬虫 B ──┼──→ 全局共享连接池 (3-10 个连接)
└── 爬虫 C ──┘

总连接数：3~10 个数据库连接（节省 60-70%）
```

## 核心实现

### 1. MySQLConnectionPoolManager（单例连接池管理器）

```python
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

# 自动使用单例模式，相同配置返回同一个连接池
pool = await MySQLConnectionPoolManager.get_pool(
    pool_type='asyncmy',  # 或 'aiomysql'
    host='localhost',
    port=3306,
    user='root',
    password='',
    db='crawlo',
    minsize=3,
    maxsize=10
)
```

### 2. 特性

#### ✅ 单例模式
- 相同数据库配置只创建一个连接池
- 不同数据库配置创建不同的连接池
- 连接池通过 `{pool_type}:{host}:{port}:{db}` 唯一标识

#### ✅ 线程安全
- 使用异步锁保护初始化过程
- 支持并发访问
- 避免竞争条件

#### ✅ 配置隔离
- 支持连接到不同的数据库
- 每个数据库使用独立的连接池
- 自动识别和复用相同配置

#### ✅ 资源管理
- 统一的连接池清理接口
- 支持查看所有连接池状态
- 优雅关闭和资源释放

## 使用方式

### 在 Pipeline 中使用（自动）

MySQL Pipeline 已经自动集成了单例连接池管理器，**无需修改代码**：

```python
# 在 settings.py 中配置
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# 运行多个爬虫时，会自动共享连接池
# 无需额外配置
```

### 手动使用连接池管理器

如果需要在其他地方使用 MySQL 连接：

```python
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

class CustomService:
    async def init_db(self):
        # 获取连接池（自动单例）
        self.pool = await MySQLConnectionPoolManager.get_pool(
            pool_type='asyncmy',
            host='localhost',
            port=3306,
            user='root',
            password='password',
            db='my_database',
            minsize=5,
            maxsize=20
        )
    
    async def query(self, sql):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql)
                return await cursor.fetchall()
```

### 查看连接池状态

```python
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

# 获取所有连接池的统计信息
stats = MySQLConnectionPoolManager.get_pool_stats()
print(stats)

# 输出示例：
{
    'total_pools': 2,
    'pools': {
        'asyncmy:localhost:3306:crawlo': {
            'type': 'asyncmy',
            'size': 5,
            'minsize': 3,
            'maxsize': 10,
            'host': 'localhost',
            'db': 'crawlo'
        },
        'asyncmy:127.0.0.1:3306:test_db': {
            'type': 'asyncmy',
            'size': 3,
            'minsize': 2,
            'maxsize': 8,
            'host': '127.0.0.1',
            'db': 'test_db'
        }
    }
}
```

### 清理所有连接池

在程序退出时：

```python
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

# 关闭所有连接池
await MySQLConnectionPoolManager.close_all_pools()
```

## 配置参数

### 连接池参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pool_type` | str | 'asyncmy' | 连接池类型：'asyncmy' 或 'aiomysql' |
| `host` | str | 'localhost' | 数据库主机地址 |
| `port` | int | 3306 | 数据库端口 |
| `user` | str | 'root' | 数据库用户名 |
| `password` | str | '' | 数据库密码 |
| `db` | str | 'crawlo' | 数据库名称 |
| `minsize` | int | 3 | 最小连接数 |
| `maxsize` | int | 10 | 最大连接数 |

### Settings 配置

```python
# settings.py

# MySQL 基础配置
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'your_database'

# 连接池配置
MYSQL_POOL_MIN = 3   # 最小连接数
MYSQL_POOL_MAX = 10  # 最大连接数

# 使用 AsyncmyMySQLPipeline（推荐）
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# 或使用 AiomysqlMySQLPipeline
# PIPELINES = [
#     'crawlo.pipelines.mysql_pipeline.AiomysqlMySQLPipeline',
# ]
```

## 性能对比

### 优化前
```
场景：3 个爬虫同时运行
- 每个爬虫创建独立连接池
- 每个连接池：minsize=3, maxsize=10
- 总连接数：9~30 个
- 内存占用：约 30-100MB
```

### 优化后
```
场景：3 个爬虫同时运行
- 所有爬虫共享一个连接池
- 连接池：minsize=3, maxsize=10
- 总连接数：3~10 个
- 内存占用：约 10-35MB
- 节省：60-70% 的连接和内存
```

## 技术细节

### 连接池标识

连接池通过以下参数生成唯一标识：
```python
pool_key = f"{pool_type}:{host}:{port}:{db}"

# 示例：
# "asyncmy:localhost:3306:crawlo"
# "aiomysql:127.0.0.1:3306:test_db"
```

### 线程安全机制

```python
# 类级别锁（保护实例字典）
_lock = asyncio.Lock()

# 实例级别锁（保护连接池初始化）
_pool_lock = asyncio.Lock()

# 双重检查锁定模式
async with cls._lock:
    if pool_key not in cls._instances:
        instance = cls(pool_key)
        cls._instances[pool_key] = instance

async with instance._pool_lock:
    if not instance._pool_initialized:
        # 初始化连接池
        instance.pool = await create_pool(...)
        instance._pool_initialized = True
```

### Pipeline 集成

```python
# AsyncmyMySQLPipeline._ensure_pool()
async def _ensure_pool(self):
    if self._pool_initialized and self.pool:
        return
    
    async with self._pool_lock:
        if not self._pool_initialized:
            # 使用单例连接池管理器
            self.pool = await MySQLConnectionPoolManager.get_pool(
                pool_type='asyncmy',
                host=self.settings.get('MYSQL_HOST'),
                ...
            )
            self._pool_initialized = True
```

## 注意事项

### ⚠️ 连接池生命周期

- **不要手动关闭连接池**：连接池由 MySQLConnectionPoolManager 统一管理
- **Pipeline 关闭时**：只清理批量缓冲区，不关闭连接池
- **程序退出时**：调用 `MySQLConnectionPoolManager.close_all_pools()`

### ⚠️ 多数据库场景

如果需要连接多个不同的数据库：

```python
# 数据库 A
pool_a = await MySQLConnectionPoolManager.get_pool(
    host='db_host_a',
    db='database_a',
    ...
)

# 数据库 B（会创建新的连接池）
pool_b = await MySQLConnectionPoolManager.get_pool(
    host='db_host_b',
    db='database_b',
    ...
)

# 相同配置（复用已有连接池）
pool_a2 = await MySQLConnectionPoolManager.get_pool(
    host='db_host_a',
    db='database_a',
    ...
)
# pool_a2 is pool_a  # True
```

### ⚠️ 连接池大小建议

```python
# 少量爬虫（1-3个）
MYSQL_POOL_MIN = 3
MYSQL_POOL_MAX = 10

# 中等规模（4-10个爬虫）
MYSQL_POOL_MIN = 5
MYSQL_POOL_MAX = 20

# 大规模（10+个爬虫）
MYSQL_POOL_MIN = 10
MYSQL_POOL_MAX = 50
```

## 迁移指南

### 从旧版本迁移

**无需任何修改！**

旧代码会自动使用新的单例连接池：

```python
# 旧代码（仍然有效）
PIPELINES = [
    'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',
]

# 自动获得优化效果：
# - 多个爬虫自动共享连接池
# - 减少数据库连接数
# - 降低资源消耗
```

## 日志输出

启用优化后，会看到如下日志：

```
[INFO] MySQLPool.asyncmy:localhost:3306:crawlo: 创建新的连接池管理器 (type=asyncmy, minsize=3, maxsize=10)
[INFO] MySQLPool.asyncmy:localhost:3306:crawlo: 连接池初始化成功 (minsize=3, maxsize=10)
[INFO] AsyncmyMySQLPipeline: MySQL连接池初始化完成（表: items, 使用全局共享连接池）
[INFO] AsyncmyMySQLPipeline: MySQL Pipeline 关闭，但保留全局共享连接池以供其他爬虫使用
[INFO] MySQLPool: 开始关闭所有连接池，共 1 个
[INFO] MySQLPool: 关闭连接池: asyncmy:localhost:3306:crawlo
[INFO] MySQLPool: 连接池已关闭: asyncmy:localhost:3306:crawlo
[INFO] MySQLPool: 所有连接池已关闭
```

## 总结

### ✅ 优势

1. **自动优化**：无需修改代码，自动获得优化效果
2. **大幅节省资源**：减少 60-70% 的数据库连接
3. **提升性能**：降低数据库压力，提高吞吐量
4. **向后兼容**：完全兼容现有代码

### 📈 适用场景

- ✅ 多个爬虫同时运行
- ✅ 分布式爬虫系统
- ✅ 大规模数据采集
- ✅ 资源受限环境

### 🔍 监控建议

定期检查连接池状态：

```python
import asyncio
from crawlo.utils.mysql_connection_pool import MySQLConnectionPoolManager

async def monitor():
    while True:
        stats = MySQLConnectionPoolManager.get_pool_stats()
        print(f"活跃连接池: {stats['total_pools']}")
        for key, pool_info in stats['pools'].items():
            print(f"  {key}: {pool_info['size']}/{pool_info['maxsize']} 连接")
        await asyncio.sleep(60)  # 每分钟检查一次
```
