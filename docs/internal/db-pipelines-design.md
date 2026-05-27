# 数据库管道统一设计方案

> 版本：v1.3  
> 日期：2026-05-25  
> 状态：设计中  
> 变更记录：v1.0 → v1.1 修正 10 项问题（见 §8.2），v1.1 → v1.2 修正 5 项问题（见 §8.3），v1.2 → v1.3 修正 7 项问题（见 §8.4）

## 一、背景与目标

### 1.1 现状问题

当前 Crawlo Pipeline 架构存在以下问题：

1. **MySQLPipeline 把通用逻辑和 MySQL 专属逻辑耦合在一起**（400+ 行），用户编写新的数据库管道需复制粘贴约 200+ 行样板代码
2. **`DatabasePipeline` 和 `ConnectablePipeline` 是空壳**，只抽象了 pool 创建/关闭，没有提取批处理、重试、降级、事务等通用逻辑，且当前已无人继承使用（见 §8.1 废弃说明）
3. **`MongoPipeline` 完全孤立**，不继承任何基类，破坏了架构一致性
4. **没有文档型数据库基类**，MongoDB/Elasticsearch 无法共享 upsert/bulk_write 逻辑

### 1.2 改造目标

- 用户编写新数据库 Pipeline 只需 **40~120 行**（当前需 600+ 行）
- 统一的基类设计，覆盖 SQL 关系型、文档型、列式、宽列式数据库
- MongoDB/Elasticsearch 等文档型数据库共享 `GenericDocumentPipeline` 基类
- 各 Pipeline 配置前缀统一为 `_{PREFIX}_`，模板配置开箱即用
- 引入 `SQLDialect` 模式，进一步减少 SQL 类型子类代码量

> 📎 **关联文档**：[non-db-pipelines-design.md](./non-db-pipelines-design.md) — 文件型/去重型 Pipeline 优化方案（文件型继承断裂修复、去重管道双路径 bug 修复等）。两者共享 `base_pipeline.py` 基类体系，应统筹评审。

## 二、架构设计

### 2.1 基类层次结构

```
ResourceManagedPipeline          ← 批量缓冲区 + 资源管理 + DCL初始化
├── GenericSQLPipeline           ← SQL 数据库通用基类（批处理、重试、降级、事务）
│   ├── MySQLPipeline            ← 已完成重构
│   ├── SQLitePipeline           ← 🆕
│   ├── PostgreSQLPipeline       ← 🆕
│   └── ClickHousePipeline       ← 🆕
├── GenericDocumentPipeline      ← 文档型数据库通用基类（重试、降级、统计、失败保存）
│   ├── MongoPipeline            ← ✏️ 重构（⚠️ breaking change，见 §3.5）
│   └── ElasticsearchPipeline    ← 🆕
└── HBasePipeline                ← 宽列式，直接继承 ResourceManagedPipeline
```

**已废弃**（见 §8.1）：

```
DatabasePipeline                 ← @deprecated，v2.0 删除
└── ConnectablePipeline          ← @deprecated，v2.0 删除
```

### 2.2 接口清单

#### GenericSQLPipeline — 子类必须实现（8 个）

| # | 方法 | 用途 | 示例（MySQL） |
|---|------|------|-------------|
| 1 | `_PREFIX` 属性 | 配置前缀 | `'MYSQL'` → 读取 `MYSQL_TABLE` 等 |
| 2 | `_initialize_pool()` | 创建连接池 | `await MySQLConnectionPoolManager.get_pool(...)` |
| 3 | `_create_helper()` ✜ | 创建 DB Helper（可选重写） | `await MySQLHelper.get_instance(settings)` |
| 4 | `_close_pool(pool)` | 关闭连接池 | `pool.close(); await pool.wait_closed()` |
| 5 | `_do_insert(data)` | 单条插入 | `await self._helper.insert(table=..., data=data, ...)` |
| 6 | `_do_batch_insert(batch)` | 批量事务插入 | `async with self._helper.transaction() as cur: ...` |
| 7 | `_do_batch_insert_no_tx(batch)` | 批量无事务插入 | `await self._helper.insert_many(table=..., datas=batch, ...)` |
| 8 | `_check_table_exists()` | 表存在性检查 | `SELECT 1 FROM information_schema.tables WHERE ...` |

> ✜ `_create_helper()` 默认实现为 `pass`，仅 MySQL 等需要 Helper 层的数据库才需重写。PostgreSQL、SQLite 等可直接使用连接池的子类无需实现。

#### GenericDocumentPipeline — 子类必须实现（4 个）

| # | 方法 | 用途 |
|---|------|------|
| 1 | `_do_upsert(doc)` | 单文档插入/更新 |
| 2 | `_do_batch_upsert(docs)` | 批量插入/更新 |
| 3 | `_check_collection_exists()` | 集合/索引存在性检查 |
| 4 | `_close_client(client)` | 关闭客户端连接 |

#### GenericDocumentPipeline — 抽象方法 vs 基类模板方法

`GenericDocumentPipeline` 采用与 `GenericSQLPipeline` 完全对称的模板方法模式。子类只需实现 4 个与具体数据库打交道的抽象方法，基类提供完整的重试、降级、统计等横切逻辑。

**子类必须实现的抽象方法**（见上表）：

| 抽象方法 | 职责 |
|----------|------|
| `_do_upsert(doc)` | 执行单条 upsert 写入 |
| `_do_batch_upsert(docs)` | 执行批量 upsert 写入 |
| `_check_collection_exists()` | 验证集合/索引存在性 |
| `_close_client(client)` | 关闭数据库客户端连接 |

**基类提供的模板方法**（调用上述抽象方法，封装横切逻辑）：

| 基类模板方法 | 内部调用链 | 与 GenericSQLPipeline 对应关系 |
|-------------|-----------|------------------------------|
| `_add_to_batch(doc)` | — | 同 GenericSQLPipeline |
| `_flush_batch()` | → `_do_batch_upsert()` | 同 GenericSQLPipeline |
| `_insert_single(doc)` | → `_do_upsert()` + 重试 + 统计 | 同 `GenericSQLPipeline._insert_single()` |
| `_fallback_upsert(docs)` | → 逐条 `_do_upsert()` + 错误处理 | 同 `GenericSQLPipeline._fallback_insert()` |
| `_record_success()` | — | 同 GenericSQLPipeline |
| `_record_failure(error)` | — | 同 GenericSQLPipeline |
| `_save_failed_batch(docs, error)` | — | 同 GenericSQLPipeline |
| `_before_insert(item)` / `_after_insert(item, rowcount)` | — | 钩子（可选重写） |

> **关键设计**：`_insert_single()` 和 `_flush_batch()` 是基类实现的模板方法，它们封装了重试、错误分类（`ErrorClassifier`）、统计计数等通用逻辑，然后调用子类的 `_do_upsert()` / `_do_batch_upsert()` 执行实际的数据库写入。这与 GenericSQLPipeline 中 `_insert_single()` → `_do_insert()` 的模式完全一致。

### 2.3 钩子方法（可选重写）

| 方法 | 默认行为 | 用途 |
|------|---------|------|
| `_before_insert(item)` | 返回 `dict(item)` | 插入前数据清洗/字段映射 |
| `_after_insert(item, rowcount)` | 无操作 | 插入后回调（如触发通知） |
| `_init_config()` | 从 `{PREFIX}_*` 读取配置 | 自定义配置解析 |

### 2.4 SQLDialect 模式（新增）

为减少 SQL 类型子类的 SQL 构建代码量，引入 `SQLDialect` 接口。子类只需声明方言，无需重复构建 SQL 语句：

```python
class SQLDialect:
    """SQL 方言描述器，子类通过声明式配置减少 SQL 构建代码"""
    placeholder: str          # 参数占位符: MySQL='%s', PostgreSQL='${i}', SQLite='?'
    quote_char: str           # 标识符引号: MySQL='`', PostgreSQL='"', SQLite='"'
    upsert_template: str      # UPSERT 语法模板
    insert_ignore_template: str  # INSERT IGNORE 语法模板
    replace_template: str     # REPLACE 语法模板

class MySQLDialect(SQLDialect):
    placeholder = '%s'
    quote_char = '`'
    upsert_template = 'INSERT INTO {table} ({cols}) VALUES ({vals}) ON DUPLICATE KEY UPDATE {updates}'
    insert_ignore_template = 'INSERT IGNORE INTO {table} ({cols}) VALUES ({vals})'
    replace_template = 'REPLACE INTO {table} ({cols}) VALUES ({vals})'

class PostgreSQLDialect(SQLDialect):
    placeholder = '${i}'      # i 从 1 开始
    quote_char = '"'
    upsert_template = 'INSERT INTO {table} ({cols}) VALUES ({vals}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {updates}'
    insert_ignore_template = 'INSERT INTO {table} ({cols}) VALUES ({vals}) ON CONFLICT DO NOTHING'

class SQLiteDialect(SQLDialect):
    placeholder = '?'
    quote_char = '"'
    insert_ignore_template = 'INSERT OR IGNORE INTO {table} ({cols}) VALUES ({vals})'
    replace_template = 'INSERT OR REPLACE INTO {table} ({cols}) VALUES ({vals})'

class ClickHouseDialect(SQLDialect):
    placeholder = '%s'
    quote_char = '`'
    # ClickHouse 无传统 UPSERT，依赖 ReplacingMergeTree 引擎后台去重
    insert_template = 'INSERT INTO {table} ({cols}) VALUES ({vals})'
```

引入后预期代码量变化：

| Pipeline | 无 SQLDialect | 有 SQLDialect | 减少 |
|----------|:------------:|:------------:|:----:|
| PostgreSQLPipeline | ~80 行 | ~50 行 | ~38% |
| SQLitePipeline | ~60 行 | ~40 行 | ~33% |

## 三、各 Pipeline 详细设计

### 3.1 SQLitePipeline

```python
class SQLitePipeline(GenericSQLPipeline):
    _PREFIX = 'SQLITE'
```

| 维度 | 设计 |
|------|------|
| 连接 | `aiosqlite.connect(path)` — 无需连接池，单连接复用 |
| 路径 | `{SQLITE_PATH}/{SQLITE_DB}.db`，默认 `data/crawlo.db` |
| UPSERT | 默认 `INSERT OR IGNORE`（避免自增 ID 变化），配置 `AUTO_UPDATE=True` 时使用 `INSERT OR REPLACE` |
| 表检查 | `SELECT name FROM sqlite_master WHERE type='table' AND name=?` |
| 事务 | 默认关闭（SQLite 单写锁，并发下事务易超时） |
| 依赖 | `aiosqlite>=0.19.0` |

**设计点**：

1. `_initialize_pool()` 返回单个 `aiosqlite.Connection` 并赋值给 `self.pool`。虽命名为 `_pool`，但实际存储单连接对象，`GenericSQLPipeline` 的所有调用（`_close_pool(self.pool)`、`_check_table_exists()` 等）直接操作该 Connection。配置 `USE_BATCH=True` 时通过 `executemany` 批量写入。
2. **默认使用 `INSERT OR IGNORE`** 而非 `INSERT OR REPLACE`。原因：`INSERT OR REPLACE` 实质是 `DELETE + INSERT`，会导致自增 ID 变化，与 MySQL 默认 `INSERT IGNORE` 的行为不一致。需要覆盖整行时通过 `{PREFIX}_AUTO_UPDATE=True` 启用 `INSERT OR REPLACE`。

### 3.2 PostgreSQLPipeline

```python
class PostgreSQLPipeline(GenericSQLPipeline):
    _PREFIX = 'PG'
```

| 维度 | 设计 |
|------|------|
| 连接池 | `asyncpg.create_pool(...)` |
| 占位符 | `$1, $2`（非 MySQL 的 `%s`） |
| UPSERT | `INSERT INTO table VALUES (...) ON CONFLICT (conflict_cols) DO UPDATE SET ...` |
| 冲突列 | **必须配置** `{PREFIX}_CONFLICT_COLUMNS`（见下方说明） |
| 表检查 | `SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=$1` |
| 事务 | 默认开启，通过 `asyncpg` 原生事务支持 |
| 依赖 | `asyncpg>=0.29.0` |

**设计点**：

1. 由于占位符风格与 MySQL 不同，`_do_insert` 和 `_do_batch_insert` 需要构建 PostgreSQL 专有 SQL。`update_columns` 配置对应 `ON CONFLICT` 的 `DO UPDATE SET col=EXCLUDED.col` 语法。
2. **`ON CONFLICT (pk)` 必须显式指定冲突列**，与 MySQL 的 `ON DUPLICATE KEY UPDATE`（自动检测唯一键）不同。新增配置项：

```python
# PostgreSQL 特有配置
PG_CONFLICT_COLUMNS = ('id',)    # ON CONFLICT 的冲突列，必须配置
                                  # 建议设为表的主键或唯一索引列
```

如果未配置 `PG_CONFLICT_COLUMNS` 且未设置 `INSERT_IGNORE=True`，Pipeline 启动时抛出 `ConfigError` 提示用户配置。

### 3.3 ClickHousePipeline

```python
class ClickHousePipeline(GenericSQLPipeline):
    _PREFIX = 'CLICKHOUSE'
```

| 维度 | 设计 |
|------|------|
| 连接 | `clickhouse-connect` 异步客户端 |
| 批量优先 | 默认 `USE_BATCH=True`, `BATCH_SIZE=10000` |
| UPSERT | 依赖 `ReplacingMergeTree` 引擎 + 直接 `INSERT`（推荐，见下方说明） |
| 事务 | 强制 `USE_TRANSACTION=False`（ClickHouse 不支持传统事务） |
| 依赖 | `clickhouse-connect>=0.7.0` |

**设计点**：

1. `_do_insert` 不推荐单独使用（会记录 WARNING）。推荐始终走 `_do_batch_insert` 路径。
2. **UPSERT 策略**：**禁止使用 `ALTER TABLE ... DELETE WHERE ...` + `INSERT`**。`ALTER DELETE` 是 ClickHouse mutation 操作，会重写整个数据分区，极其耗资源且异步执行（不会立即生效）。正确做法：

| 表引擎 | UPSERT 策略 | 说明 |
|--------|-----------|------|
| `ReplacingMergeTree`（推荐） | 直接 `INSERT` | 后台自动按 `ORDER BY` 键去重，查询时可用 `FINAL` 关键字获取最新数据 |
| `CollapsingMergeTree` | 插入取消行 + 新行 | 适用于有状态变更的场景 |
| `ReplicatedReplacingMergeTree` | 直接 `INSERT` | 分布式场景，同 ReplacingMergeTree |
| 通用兼容 | `INSERT INTO ... VALUES` | 不做显式去重，依赖引擎后台合并 |

3. 配置示例：

```python
CLICKHOUSE_UPSERT_MODE = 'replacing'   # 'replacing'(默认) | 'collapsing' | 'insert_only'
```

### 3.4 GenericDocumentPipeline（新增基类）

```python
class GenericDocumentPipeline(ResourceManagedPipeline):
    """
    文档型数据库通用基类
    
    提供与 GenericSQLPipeline 对称的完整能力：
    - 批量缓冲管理 + 刷新
    - 文档级别 upsert（单条/批量）
    - 连接生命周期管理
    - 重试 + 降级 + 统计（复用 ErrorClassifier）
    - 失败数据保存到文件
    - 钩子：_before_insert / _after_insert
    """
```

**设计的抽象方法**：

```python
@abstractmethod
async def _do_upsert(self, doc: dict) -> int:
    """单文档 upsert，返回受影响的文档数"""

@abstractmethod
async def _do_batch_upsert(self, docs: list) -> int:
    """批量文档 upsert，返回受影响的文档数"""

@abstractmethod
async def _check_collection_exists(self):
    """检查集合/索引是否存在"""

@abstractmethod
async def _close_client(self, client):
    """关闭客户端连接"""
```

**基类提供的通用方法**（与 GenericSQLPipeline 对称）：

```python
async def _add_to_batch(self, doc):     # 添加到缓冲区
async def _flush_batch(self):           # 刷新缓冲区
async def _insert_single(self, doc):    # 单文档 upsert + 重试
async def _fallback_upsert(self, docs): # 批量失败后逐条降级
def _record_success(self):              # 成功计数
def _record_failure(self, error):       # 失败分类 + 计数
async def _save_failed_batch(self, docs, error):  # 保存失败数据到文件
```

**与 GenericSQLPipeline 的主要差异**：
- 不区分 `insert`/`update` → 统一用 `upsert` 语义
- 不涉及 SQL 构建、事务管理
- 冲突处理是数据库原生行为（如 MongoDB 的 `update_one(upsert=True)`）
- 提供 `_compute_doc_id(doc) -> str` 基类默认方法（MD5 指纹），子类可重写为自定义 ID 策略

### 3.5 MongoPipeline（重构）

```python
class MongoPipeline(GenericDocumentPipeline):
    _PREFIX = 'MONGO'
```

| 维度 | 设计 |
|------|------|
| 客户端 | `motor.motor_asyncio.AsyncIOMotorClient`（单例，通过 `MongoConnectionPoolManager.get_client()`） |
| 数据库 | `{MONGO_DB}` → `client[{MONGO_DB}]` |
| 集合 | `{MONGO_COLLECTION}` |
| Upsert | `update_one({'_id': doc_hash}, {'$set': doc}, upsert=True)` |
| 批量 | `bulk_write([UpdateOne({'_id': h}, {'$set': d}, upsert=True) ...])` |
| 依赖 | `motor>=3.3.0` |

> ⚠️ **Breaking Change**：当前 `MongoPipeline` 使用 `insert_one`（重复时抛 `DuplicateKeyError`，错误被捕获后跳过），重构后改为 `update_one(upsert=True)`（重复时覆盖）。这是**语义变更**：
> - 旧行为：重复数据报错/跳过
> - 新行为：重复数据覆盖
>
> 为保证向后兼容，新增配置开关：
> ```python
> MONGO_DEDUPLICATE_MODE = 'upsert'   # 'upsert'(默认，覆盖) | 'insert'(旧行为，重复跳过)
> ```
> 当 `MONGO_DEDUPLICATE_MODE='insert'` 时，使用 `insert_one` 并捕获 `DuplicateKeyError`。

### 3.6 ElasticsearchPipeline

```python
class ElasticsearchPipeline(GenericDocumentPipeline):
    _PREFIX = 'ELASTICSEARCH'
```

| 维度 | 设计 |
|------|------|
| 客户端 | `elasticsearch.AsyncElasticsearch` |
| 索引 | `{ELASTICSEARCH_INDEX}` → 默认 `{project_name}` |
| 文档 ID | 确定性 MD5 指纹（见下方说明） |
| 写入 | `client.index(index=..., id=doc_id, document=doc)` |
| 批量 | `elasticsearch.helpers.async_bulk(client, actions)` |
| 依赖 | `elasticsearch>=8.0.0` |

**设计点**：

1. **配置前缀改为 `ELASTICSEARCH_`**（非 `ES_`）。原因：`ES_HOSTS`、`ES_INDEX` 等短前缀与 Elasticsearch 官方环境变量命名重叠（如 `ES_JAVA_OPTS`），易造成混淆。
2. **文档 ID 必须使用确定性指纹**，禁止使用 `hash(item)`：

```python
import hashlib
import json

def _compute_doc_id(self, doc: dict) -> str:
    """计算文档确定性 ID，用作 ES _id 实现去重"""
    return hashlib.md5(
        json.dumps(doc, sort_keys=True, ensure_ascii=False).encode('utf-8')
    ).hexdigest()
```

原因：Python `hash()` 函数在不同进程间不保证确定性（受 `PYTHONHASHSEED` 影响），且 dict 的 hash 受 key 顺序影响。`md5(json.dumps(sort_keys=True))` 保证相同内容始终生成相同 ID。

### 3.7 HBasePipeline

```python
class HBasePipeline(ResourceManagedPipeline):
    """
    直接继承 ResourceManagedPipeline（不继承 GenericSQLPipeline）
    
    原因：HBase 不是 SQL/文档模型，API 完全不同
    """
```

| 维度 | 设计 |
|------|------|
| 客户端 | `happybase.Connection`（同步，通过 `run_in_executor` 异步化） |
| Rowkey | `_build_rowkey(item)` → 钩子，子类自定义 |
| 列族 | `{HBASE_COLUMN_FAMILY}` → 默认 `'cf'` |
| 写入 | `table.put(rowkey, {f'{cf}:{col}': val for col, val in item.items()})` |
| 批量 | `table.batch()` 上下文管理器 |
| 依赖 | `happybase>=1.2.0`（同步库，需要 `run_in_executor` 包装） |

**设计点**：HBase 没有通用 upsert 语义，子类必须实现完整的 `process_item()` 方法，但可以复用 `ResourceManagedPipeline` 的缓冲区机制。

## 四、配置规范

### 4.1 统一前缀命名

```python
# SQLite
SQLITE_PATH = 'data'                    # 数据库文件目录
SQLITE_DB = 'crawlo'                    # 数据库文件名（不含 .db）
SQLITE_AUTO_UPDATE = False              # INSERT OR REPLACE（默认 INSERT OR IGNORE）

# PostgreSQL
PG_HOST = '127.0.0.1'
PG_PORT = 5432
PG_USER = 'postgres'
PG_PASSWORD = ''
PG_DB = 'crawlo'
PG_TABLE = 'crawlo_data'
PG_CONFLICT_COLUMNS = ('id',)           # ON CONFLICT 的冲突列（PostgreSQL 必须配置）

# ClickHouse
CLICKHOUSE_HOST = '127.0.0.1'
CLICKHOUSE_PORT = 9000
CLICKHOUSE_DB = 'crawlo'
CLICKHOUSE_TABLE = 'crawlo_data'
CLICKHOUSE_USE_BATCH = True            # 默认启用批量
CLICKHOUSE_BATCH_SIZE = 10000
CLICKHOUSE_UPSERT_MODE = 'replacing'   # 'replacing' | 'collapsing' | 'insert_only'

# MongoDB
MONGO_URI = 'mongodb://127.0.0.1:27017'
MONGO_DB = 'crawlo'
MONGO_COLLECTION = 'crawlo_data'
MONGO_DEDUPLICATE_MODE = 'upsert'      # 'upsert'(覆盖) | 'insert'(跳过)

# Elasticsearch
ELASTICSEARCH_HOSTS = ['http://127.0.0.1:9200']
ELASTICSEARCH_INDEX = 'crawlo'
ELASTICSEARCH_USE_BATCH = True
ELASTICSEARCH_BATCH_SIZE = 500

# HBase
HBASE_HOST = '127.0.0.1'
HBASE_PORT = 9090
HBASE_TABLE = 'crawlo_data'
HBASE_COLUMN_FAMILY = 'cf'
```

### 4.2 通用冲突策略（SQL 类型）

所有 SQL 类型 Pipeline 共享 `GenericSQLPipeline` 的冲突处理配置：

```python
{prefix}_UPDATE_COLUMNS = ()            # ON DUPLICATE KEY UPDATE（指定字段）
{prefix}_AUTO_UPDATE = False            # REPLACE INTO（覆盖整行）
{prefix}_INSERT_IGNORE = False          # INSERT IGNORE（忽略重复）
```

PostgreSQL 额外配置：

```python
{prefix}_CONFLICT_COLUMNS = ('id',)     # ON CONFLICT 冲突列（PostgreSQL 专用，必须配置）
```

### 4.3 连接池单例模式规范

所有 Pipeline 应遵循统一的连接池单例模式，避免同一进程内创建多个连接池：

```python
# MySQL: MySQLConnectionPoolManager.get_pool() → 单例
# MongoDB: MongoConnectionPoolManager.get_client() → 单例
# PostgreSQL: 建议新增 PgConnectionPoolManager.get_pool() → 单例
# Elasticsearch: 客户端本身是线程安全的，可直接复用实例
```

建议在 `crawlo/db/` 下提供通用 `PoolManager` 基类：

```python
class BasePoolManager:
    """连接池管理器基类，提供单例模式 + 引用计数 + 自动清理"""
    _instances = {}   # {config_key: pool}
    _ref_counts = {}  # {config_key: int}
    
    @classmethod
    async def get_pool(cls, **config):
        """获取或创建连接池（单例）"""
        
    @classmethod
    async def release_pool(cls, **config):
        """释放引用，引用计数归零时关闭连接池"""
```

## 五、依赖管理

```ini
# setup.cfg
[options.extras_require]
sqlite = aiosqlite>=0.19.0
postgresql = asyncpg>=0.29.0
clickhouse = clickhouse-connect>=0.7.0
mongodb = motor>=3.3.0
elasticsearch = elasticsearch>=8.0.0,<9.0.0
hbase = happybase>=1.2.0
db-all = 
    aiosqlite>=0.19.0
    asyncpg>=0.29.0
    clickhouse-connect>=0.7.0
    motor>=3.3.0
    elasticsearch>=8.0.0,<9.0.0
    happybase>=1.2.0
```

## 六、实施计划

| 阶段 | 内容 | 文件 | 预计行数 |
|:--:|------|------|------|
| 0 | 已有 `GenericSQLPipeline` | `generic_sql.py` | 212 |
| 0.5 | 新增 `SQLDialect` + `BasePoolManager` | `db/dialect.py`, `db/pool_manager.py` | ~80 |
| 1 | SQLitePipeline | `sql/sqlite.py` | ~40 |
| 2 | PostgreSQLPipeline | `sql/postgresql.py` | ~50 |
| 3 | `GenericDocumentPipeline` 基类 | `generic_doc.py` | ~250 |
| 4 | MongoPipeline 重构 | `doc/mongo.py` | ~60 |
| 5 | ElasticsearchPipeline | `doc/elasticsearch.py` | ~80 |
| 6 | ClickHousePipeline | `sql/clickhouse.py` | ~70 |
| 7 | HBasePipeline | `hbase.py` | ~120 |
| 8 | 模板配置 + 导出更新 | `settings.py.tmpl`, `__init__.py` | ~35 |
| 9 | 单元测试 | `tests/` | 每个 ~100 |
| 10 | 废弃标记 `DatabasePipeline` / `ConnectablePipeline` | `base_pipeline.py` | ~5 |

## 七、用户使用示例

### 7.1 自定义 PostgreSQL Pipeline

```python
from crawlo.pipelines.generic_sql import GenericSQLPipeline
from crawlo.db.dialect import PostgreSQLDialect
import asyncpg

class PgPipeline(GenericSQLPipeline):
    _PREFIX = 'PG'
    dialect = PostgreSQLDialect  # 声明方言后，_do_insert/_do_batch_insert 等 SQL 构建由基类完成

    async def _initialize_pool(self):
        self.pool = await asyncpg.create_pool(
            host=self.settings.get('PG_HOST', 'localhost'),
            port=self.settings.get_int('PG_PORT', 5432),
            user=self.settings.get('PG_USER', 'postgres'),
            password=self.settings.get('PG_PASSWORD', ''),
            database=self.settings.get('PG_DB', 'crawlo'),
            min_size=2, max_size=10
        )

    # _create_helper() 使用基类默认实现（pass），PG 无需 Helper 层

    async def _close_pool(self, pool):
        await pool.close()

    async def _do_insert(self, data):
        sql, params = self.dialect.build_upsert(table=self.table_name, data=data,
                                                  conflict_cols=self.conflict_cols,
                                                  update_cols=self.update_columns)
        async with self.pool.acquire() as conn:
            return await conn.execute(sql, *params)

    async def _do_batch_insert(self, batch):
        # SQLDialect 同样提供 build_batch_upsert() 模板方法
        ...

    # _do_batch_insert_no_tx, _check_table_exists 类似
```
```python"># 对比：不使用 SQLDialect 需手动拼 SQL（不推荐，仅对比）
#     async def _do_insert(self, data):
#         keys = list(data.keys())
#         cols = ', '.join(f'"{k}"' for k in keys)
#         vals = ', '.join(f'${i+1}' for i in range(len(keys)))
#         sql = f'INSERT INTO "{self.table_name}" ({cols}) VALUES ({vals}) ON CONFLICT (...) ...'
#         ...
```


### 7.2 自定义 MongoDB Pipeline

```python
from crawlo.pipelines.generic_doc import GenericDocumentPipeline
from motor.motor_asyncio import AsyncIOMotorClient
from hashlib import md5
import json

class MyMongoPipeline(GenericDocumentPipeline):
    _PREFIX = 'MONGO'
    
    def _compute_doc_id(self, doc):
        return md5(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    
    async def _do_upsert(self, doc):
        doc_id = self._compute_doc_id(doc)
        result = await self._collection.update_one(
            {'_id': doc_id}, {'$set': doc}, upsert=True
        )
        return 1
    
    # _do_batch_upsert, _check_collection_exists, _close_client 等约 50~60 行即可完成
```

## 八、附录

### 8.1 废弃说明：DatabasePipeline / ConnectablePipeline

`base_pipeline.py` 中的 `DatabasePipeline` 和 `ConnectablePipeline` 当前无人继承使用。`GenericSQLPipeline` 直接继承 `ResourceManagedPipeline`，跳过了这两个中间层。

处理方案：
1. **v1.x**：添加 `@deprecated` 装饰器 + 文档标注，保留不删
2. **v2.0**：正式删除，同时将 `ResourceManagedPipeline` 重命名为 `BasePipeline`

```python
import warnings

@deprecated("Use GenericSQLPipeline or GenericDocumentPipeline instead. Will be removed in v2.0.")
class DatabasePipeline(ResourceManagedPipeline):
    ...

@deprecated("Use GenericSQLPipeline or GenericDocumentPipeline instead. Will be removed in v2.0.")
class ConnectablePipeline(DatabasePipeline):
    ...
```

