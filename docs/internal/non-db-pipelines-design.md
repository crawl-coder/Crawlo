# 非数据库 Pipeline 优化方案

> 版本：v1.1  
> 日期：2026-05-25  
> 状态：设计中  
> 变更记录：v1.0 → v1.1 修正 8 项问题（见 §5.3）  
> 关联文档：[db-pipelines-design.md](./db-pipelines-design.md) — 数据库管道统一设计方案

## 一、背景与目标

### 1.1 现状问题

扫描 `crawlo/pipelines/` 下全部非数据库管道（9 个文件），发现以下结构性问题：

1. **文件型 Pipeline 继承体系断裂**：`CsvPipeline`、`CsvDictPipeline`、`CsvBatchPipeline`、`JsonPipeline`、`JsonLinesPipeline`、`JsonArrayPipeline` 共 6 个类**全部直接继承 `object`**，手动实现了 `from_crawler`、`process_item`、`spider_closed` 等生命周期方法。但 `base_pipeline.py` 中已有精心设计的 `FileBasedPipeline`（含 `_get_file_path`、`_open_file`、`_close_file`、aiofiles 智能回退、资源注册），这 6 个类完全绕过了它，导致约 300 行重复代码。

2. **去重管道 `close_spider` / `_cleanup_resources` 双路径 bug**：`MemoryDedupPipeline`、`RedisDedupPipeline`、`BloomDedupPipeline` 三个类把统计输出逻辑放在 `close_spider` 中，但 `PipelineManager.close()` **优先调用 `_cleanup_resources`**（仅当方法不存在时才回退到 `close_spider`），导致统计信息可能静默丢失。

3. **去重管道日志重复初始化**：`BloomDedupPipeline`、`DatabaseDedupPipeline`、`MemoryDedupPipeline`、`RedisDedupPipeline` 四个类在 `__init__` 中先调用 `super().__init__(crawler)`（父类已创建 `self.logger`），然后又 `self.logger = get_logger(...)` 覆盖，纯属冗余。

4. **去重管道空壳重写**：`_initialize_resources` 和 `_cleanup_resources` 在大多数去重子类中仅调用 `super()`，无实际逻辑但子类仍然做了重写。`DedupPipeline` 本身已提供具体实现（覆盖了 `ResourceManagedPipeline` 的 `@abstractmethod`），子类完全可以不重写直接继承，当前是**非必要的冗余重写**。

5. **JSON/CSV 内部高度重复**：
   - `JsonPipeline` 和 `JsonLinesPipeline` 功能相似（都是 JSON Lines 逐行写入），但存在以下差异：

     | 差异点 | `JsonPipeline` | `JsonLinesPipeline` |
     |--------|---------------|---------------------|
     | 序列化格式 | `json.dumps(indent=None)`（含空格） | `json.dumps(separators=(',', ':'))`（紧凑） |
     | 元数据 | 无 | `_crawl_time`, `_spider_name`（可选） |
     | 计数/日志 | 无 | `items_count` + 每 100 条日志 |
     | 统计 key | `json_pipeline/items_written` | `jsonlines_pipeline/items_written` |

     合并时需统一行为：保留紧凑格式（`separators`）+ 可选的元数据开关 + 计数功能。

   - `JsonArrayPipeline` 使用同步 `open()` / `json.load()` 在异步上下文中阻塞事件循环（`_flush_to_temp_file` 和 `spider_closed` 共 4 处同步调用）
   - 6 个文件类的 `_get_file_path` / `_ensure_file_open` 模式重复了 6 次

### 1.2 改造目标

- 文件型 Pipeline 消除重复代码 ~300 行，统一继承 `FileBasedPipeline`
- 文件型 Pipeline 清理路径从事件驱动（`subscriber.subscribe`）统一迁移到 `_cleanup_resources`（`PipelineManager.close()` 驱动），避免双重关闭
- 修复去重管道统计信息静默丢失的 bug
- 去重管道样板代码减少 ~40 行
- `JsonPipeline` + `JsonLinesPipeline` 合并为一个类（保留紧凑格式 + 可选元数据 + 计数）
- `JsonArrayPipeline` 的同步 I/O 改为 aiofiles 异步（覆盖全部 4 处同步调用）

## 二、架构设计

### 2.1 当前 vs 目标继承层次

**当前架构**（断裂）：

```
BasePipeline(ABC)
├── ResourceManagedPipeline         ← 定义了批量缓冲 + 资源管理
│   ├── DedupPipeline               ← 定义了统一指纹去重逻辑
│   │   ├── MemoryDedupPipeline     ← 仅实现 _check/_record
│   │   ├── RedisDedupPipeline      ← 手动 DCL 连接管理
│   │   ├── BloomDedupPipeline      ← 含 fallback 实现
│   │   └── DatabaseDedupPipeline   ← 手工 aiomysql 池管理
│   └── FileBasedPipeline           ← 定义了文件路径 + aiofiles 回退
│         (无人继承！)               ← 6 个文件类全部绕过
└── ConsolePipeline                 ← 直接继承 BasePipeline

object                               ← 6 个文件类直接继承！
├── CsvPipeline
├── CsvDictPipeline
├── CsvBatchPipeline
├── JsonPipeline
├── JsonLinesPipeline
└── JsonArrayPipeline
```

**目标架构**（统一）：

```
BasePipeline(ABC)
├── ResourceManagedPipeline
│   ├── DedupPipeline ✏️              ← 已提供默认实现，消除子类非必要空壳重写
│   │   ├── MemoryDedupPipeline ✏️    ← 统计迁移到 _cleanup_resources
│   │   ├── RedisDedupPipeline ✏️     ← 统计迁移 + 连接管理讨论(见 §3.6.1)
│   │   ├── BloomDedupPipeline ✏️     ← 去重日志初始化
│   │   └── DatabaseDedupPipeline ✏️  ← 考虑通用化/更名
│   ├── FileBasedPipeline             ← 保持不变
│   │   ├── CsvPipeline ✏️            ← 重构继承，合并 CsvBatchPipeline
│   │   ├── CsvDictPipeline ✏️        ← 重构继承
│   │   ├── JsonLinesPipeline ✏️      ← 合并 JsonPipeline，重写
│   │   └── JsonArrayPipeline ✏️      ← 重构继承 + aiofiles 异步化
│   ├── GenericSQLPipeline            ← 数据库管道体系（见 db-pipelines-design.md）
│   └── GenericDocumentPipeline       ← 数据库管道体系
└── ConsolePipeline                   ← 保持不变
```

## 三、各项优化详细设计

### 3.1 P0-1：文件型 Pipeline 重构继承 `FileBasedPipeline`

**当前状态**：6 个文件型类全部直接继承 `object`，各自实现了：
- `from_crawler()` — 创建实例
- `_get_file_path()` — 三级优先级路径查找（settings → spider attr → default）
- `_ensure_file_open()` — aiofiles 检查 + 回退 + 打开
- `spider_closed()` — 关闭文件 + 清理

**改后**：统一继承 `FileBasedPipeline`，只保留各类的**写入格式差异**。

#### 重构后 CsvPipeline（合并 CsvBatchPipeline）

`CsvBatchPipeline` 的批量缓冲逻辑实际上就是 `ResourceManagedPipeline.process_item_batched()` 的翻版，无需独立类。

```python
class CsvPipeline(FileBasedPipeline):
    """CSV 文件输出管道，支持批量缓冲"""

    _PREFIX = 'CSV'

    def __init__(self, crawler):
        super().__init__(crawler)
        self.writer = None
        self.buffer_enabled = self.settings.get_bool('CSV_USE_BUFFER', False)
        self.buffer = [] if self.buffer_enabled else None

    # ── 配置 ──
    @property
    def _file_path_config(self):
        return self._get_file_path('CSV_FILE', 'data', 'csv')

    # ── 生命周期 ──
    async def _initialize_resources(self):
        self.file_path = self._file_path_config
        await self._open_file('w', newline='', encoding='utf-8')
        # ⚠️ csv.writer 要求同步文件对象（write() 返回 int），
        # aiofiles 的 write() 返回协程，两者不兼容。
        # 解决方案：CSV 管道始终使用同步 I/O（aiofiles=False），
        # 写入操作通过 run_in_executor 执行以避免阻塞事件循环。
        self.writer = csv.writer(self.file_handle)  # 仅同步模式

    async def _cleanup_resources(self):
        if self.writer and hasattr(self.writer, '_file'):
            self.writer = None
        # flush buffer before close
        if self.buffer:
            await self._flush_buffer()
        # FileBasedPipeline 的资源管理器会自动关闭文件句柄

    # ── 核心写入 ──
    async def process_item(self, item, spider):
        row = self._prepare_headers_and_row(item)
        if self.buffer_enabled:
            return await self.process_item_batched(item, spider, self._write_batch)
        self.writer.writerow(row.values())
        return item

    def _prepare_headers_and_row(self, item):
        # 保留原有的表头检测 + 动态写入逻辑
        ...

    async def _write_batch(self, rows):
        self.writer.writerows(rows)
```

**代码量变化**：

| 类 | 重构前 | 重构后 | 减少 |
|----|:-----:|:-----:|:----:|
| CsvPipeline（合并 CsvBatchPipeline） | ~220 行 | ~80 行 | ~64% |
| CsvDictPipeline | ~80 行 | ~50 行 | ~38% |
| JsonLinesPipeline（合并 JsonPipeline） | ~140 行 | ~70 行 | ~50% |
| JsonArrayPipeline | ~110 行 | ~60 行 | ~45% |
| **合计** | **~550 行** | **~260 行** | **~53%** |

> ⚠️ **CSV + aiofiles 兼容性**：`csv.writer` 依赖同步文件对象的 `write()` 方法返回写入字节数，而 aiofiles 的 `write()` 是协程。重构时 CSV 管道应禁用 aiofiles（`FileBasedPipeline._open_file()` 传参控制），写入操作统一通过 `asyncio.get_event_loop().run_in_executor(None, sync_write_func)` 执行，避免阻塞事件循环。

### 3.2 P0-2：去重管道统迁统计到 `_cleanup_resources`

**当前问题**：`PipelineManager.close()` 的执行逻辑为：

```python
# pipeline_manager.py 约第 208-212 行
if hasattr(pipeline, '_cleanup_resources'):
    await pipeline._cleanup_resources()
elif hasattr(pipeline, 'close_spider'):
    await pipeline.close_spider()
```

去重管道的 `_cleanup_resources` 是空壳（仅 `super()`），统计输出写在 `close_spider` 中。如果 `DedupPipeline` 或其父类实现了 `_cleanup_resources`，则统计永远不会被输出。

**修正**：将统计逻辑从 `close_spider` 迁移到 `_cleanup_resources`。

```python
# MemoryDedupPipeline — 修正后
class MemoryDedupPipeline(DedupPipeline):

    async def _cleanup_resources(self):
        """清理资源 + 输出统计"""
        # 1. 清理内存
        if hasattr(self, 'seen_items') and self.seen_items:
            self.seen_items.clear()
        # 2. 输出统计（从 close_spider 迁移至此）
        self.logger.info(
            f"MemoryDedupPipeline 关闭: "
            f"处理 {self.processed_count}, 丢弃 {self.dropped_count}"
        )
        await super()._cleanup_resources()
```

同理修正 `RedisDedupPipeline._cleanup_resources`（`SCARD` 统计 + 清理）和 `BloomDedupPipeline._cleanup_resources`。

### 3.3 P1-1：去重管道去掉重复 `self.logger` 赋值

**当前**：

```python
class MemoryDedupPipeline(DedupPipeline):
    def __init__(self, crawler):
        super().__init__(crawler)          # ← 父类 ResourceManagedPipeline 已创建 self.logger
        self.logger = get_logger(...)      # ← 冗余覆盖，值完全相同
```

**修正**：删除第 2 行重复赋值。`DedupPipeline` → `ResourceManagedPipeline` → `BasePipeline` 链上的 `__init__` 已保证 `self.logger` 被正确初始化。

### 3.4 P1-2：去重子类消除非必要的空壳重写

**实际情况**（`base_pipeline.py:305-313`）：

```python
class DedupPipeline(ResourceManagedPipeline):
    # 注意：此处没有 @abstractmethod，是具体实现
    # 它覆盖了 ResourceManagedPipeline 中的抽象方法
    async def _initialize_resources(self):
        self.crawler.stats.inc_value('dedup/initialization_count')

    async def _cleanup_resources(self):
        self.crawler.stats.inc_value('dedup/cleanup_count')
```

`DedupPipeline` 已提供 `_initialize_resources` 和 `_cleanup_resources` 的具体实现（仅记录统计），**没有** `@abstractmethod` 装饰器。`ResourceManagedPipeline` 的 `@abstractmethod` 约束已被 `DedupPipeline` 满足。

**问题**：多数子类仍做了无意义的空壳重写，仅调用 `super()`：

```python
# 4 个子类的当前代码（非必要）
async def _initialize_resources(self):
    await super()._initialize_resources()  # 仅 super 调用，无其他逻辑

async def _cleanup_resources(self):
    await super()._cleanup_resources()     # 仅 super 调用，无其他逻辑
```

这些重写不是被 `@abstractmethod` 强制的——子类完全可以直接继承 `DedupPipeline` 的默认实现。

**修正**：子类只需删除无额外逻辑的空壳重写。有实际逻辑的子类（如 `RedisDedupPipeline._initialize_resources` 建立连接、`MemoryDedupPipeline._cleanup_resources` 清理 `seen_items`）保留重写：

```python
class MemoryDedupPipeline(DedupPipeline):
    # _initialize_resources: 无需重写，直接继承 DedupPipeline 的统计记录
    # （删除原有的空壳重写）

    async def _cleanup_resources(self):
        # 保留：有实际清理逻辑（清空 seen_items）
        self.seen_items.clear()
        self.logger.info(
            f"MemoryDedupPipeline 关闭: 处理 {self.processed_count}, "
            f"丢弃 {self.dropped_count}"
        )
        await super()._cleanup_resources()
```

**影响**：`BloomDedupPipeline`、`MemoryDedupPipeline`（仅 `_initialize_resources`）、`DatabaseDedupPipeline`（仅 `_cleanup_resources`）可删除空壳重写，共减少约 16 行样板代码。

### 3.5 P2-1：`JsonArrayPipeline` 异步化

**当前问题**（`_flush_to_temp_file` 和 `spider_closed` 共 4 处同步 I/O）：

```python
# spider_closed 中的 3 处同步调用：
# ① json_pipeline.py:269 — 合并临时文件时同步读取
with open(temp_path, 'r', encoding='utf-8') as f:
    all_items.extend(json.load(f))

# ② json_pipeline.py:274 — 写入最终 JSON 数组文件
with open(self.file_path, 'w', encoding='utf-8') as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)

# ③ json_pipeline.py:281 — 无临时文件时直接写入
with open(self.file_path, 'w', encoding='utf-8') as f:
    json.dump(self.items, f, ensure_ascii=False, indent=2)

# _flush_to_temp_file 中还有 1 处：
# ④ json_pipeline.py:226 — 刷新到临时文件
with open(temp_path, 'w', encoding='utf-8') as f:
    json.dump(self.items, f, ensure_ascii=False, indent=2)
```

**修正**：全部 4 处改为 aiofiles 异步写入/读取，`FileBasedPipeline` 已内置 aiofiles 回退机制。

```python
# _flush_to_temp_file（异步化）
async def _flush_to_temp_file(self):
    if AIOFILES_AVAILABLE:
        import aiofiles
        async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.items, ensure_ascii=False, indent=2))
    else:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_flush_to_temp, temp_file)

# spider_closed 中的合并写入（异步化）
async def _merge_temp_files(self):
    if self.temp_files:
        all_items = []
        for temp_path in self.temp_files:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(temp_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    all_items.extend(json.loads(content))
            else:
                loop = asyncio.get_event_loop()
                items = await loop.run_in_executor(None, self._sync_read_json, temp_path)
                all_items.extend(items)
            temp_path.unlink()
        await self._async_write_json(self.file_path, all_items)

def _sync_flush_to_temp(self, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(self.items, f, ensure_ascii=False, indent=2)

def _sync_read_json(self, path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

### 3.6 P2-2：`DatabaseDedupPipeline` 更名 + 通用化

**当前问题**：类名为 `DatabaseDedupPipeline` 但硬编码了 `aiomysql`（仅支持 MySQL），命名与功能不符。且未使用 `ConnectablePipeline` 的 DCL 懒初始化。

**方案 A（推荐）**：更名为 `MySQLDedupPipeline`，后续可扩展 `PgDedupPipeline`。

```python
class MySQLDedupPipeline(DedupPipeline):
    """基于 MySQL 的分布式去重管道"""
```

**方案 B**：抽象化为通用类，通过 `_ensure_pool` 和 DB 方言配置支持多种数据库。但工作量大，且与 `db-pipelines-design.md` 中的 `GenericSQLPipeline` 有重叠风险，暂不推荐。

### 3.6.1 补充：`RedisDedupPipeline` DCL 复用问题

文档初版建议"复用 `CacheBasedPipeline` 的 DCL"，但存在架构障碍：`CacheBasedPipeline` 和 `DedupPipeline` 都继承自 `ResourceManagedPipeline`，若 `RedisDedupPipeline` 同时继承两者会引发菱形 MRO 冲突。

**方案 A（推荐）**：放弃 DCL 懒加载。`RedisDedupPipeline` 已在 `_initialize_resources` 中完成连接建立并注册到 `ResourceManager`，无需额外 DCL 层。`_ensure_redis_connection` 改为内部辅助方法，不追求复用 `CacheBasedPipeline`。

**方案 B**：将 DCL 懒初始化提取为独立 mixin（`lazy_init_mixin.py`），`CacheBasedPipeline` 和 `RedisDedupPipeline` 各自通过 mixin 获得 `_ensure_lazy_init` 能力，避免多重继承冲突。改动范围较大，暂不推荐。

### 3.7 其他小修正

| 项 | 内容 |
|----|------|
| `BloomDedupPipeline` fallback `BloomFilter` | 与 `MemoryDedupPipeline` 功能重叠，改为一层别名包装即可 |
| `DatabaseDedupPipeline` 冗余索引 | `fingerprint UNIQUE` 已自带索引，删除 `idx_fingerprint` |
| `ConsolePipeline.__init__` | 当前手动赋值（`self.crawler`/`self.settings`/`self.logger`），`BasePipeline` 无 `__init__` 故无法调用 `super().__init__(crawler)`。保持现状即可；若后续 `BasePipeline` 添加 `__init__`，再改为 `super().__init__(crawler)` |
| 函数签名统一 | `process_item` 签名统一为 `async def process_item(self, item: Item, spider: Spider, **kwargs) -> Optional[Item]` |

### 3.8 关键设计说明：文件型 Pipeline 清理路径变更

当前 6 个文件型 Pipeline 通过以下模式注册清理回调：

```python
# 当前代码（csv_pipeline.py / json_pipeline.py 均有）
crawler.subscriber.subscribe(self.spider_closed, event='spider_closed'
```

清理由**事件系统**驱动（`spider_closed` 事件触发 → `self.spider_closed()` 关闭文件）。由于它们不继承 `ResourceManagedPipeline`，`PipelineManager.close()` 不处理它们。

重构继承 `FileBasedPipeline`（→ `ResourceManagedPipeline`）后，清理路径将变更为**PipelineManager 驱动**：

```python
# PipelineManager.close() → _cleanup_resources() → ResourceManager.cleanup_all()
```

**重构时注意事项**：
1. **移除**所有 `crawler.subscriber.subscribe(self.spider_closed, event='spider_closed')` 注册
2. **删除** `spider_closed()` 方法，将关闭逻辑迁移到 `_cleanup_resources()`
3. 文件句柄通过 `_resource_manager.register()` 管理，由 `ResourceManager.cleanup_all()` 自动关闭
4. 避免事件系统 + PipelineManager 双重关闭（会导致重复 close 报错）

## 四、实施计划

| 阶段 | 内容 | 文件 | 预计行数变化 |
|:--:|------|------|:----------:|
| 1 | `DedupPipeline` 无需改动（已有默认实现），子类删除非必要空壳重写 | `base_pipeline.py` | 0 行 |
| 2 | 4 个去重管道：删除空壳方法 + 删除重复 logger + 统计迁移 | 4 个 dedup 文件 | -40 行 |
| 3 | 重构 `CsvPipeline`（合并 `CsvBatchPipeline`）→ 继承 `FileBasedPipeline` | `csv_pipeline.py` | -140 行 |
| 4 | 重构 `CsvDictPipeline` → 继承 `FileBasedPipeline` | `csv_pipeline.py` | -30 行 |
| 5 | 合并 `JsonPipeline` + `JsonLinesPipeline` + 重构继承 `FileBasedPipeline` | `json_pipeline.py` | -70 行 |
| 6 | 重构 `JsonArrayPipeline`（继承 + aiofiles） | `json_pipeline.py` | -50 行 |
| 7 | `DatabaseDedupPipeline` 更名 `MySQLDedupPipeline` + 删除冗余索引 | `database_dedup_pipeline.py` | ~5 行 |
| 8 | `ConsolePipeline.__init__` 保持现状（`BasePipeline` 无 `__init__`，无法调用 `super()`） | `console_pipeline.py` | 0 行 |
| 9 | 函数签名统一 | 多处 | ~5 行 |
| 10 | 单元测试 | `tests/` | 每个 ~80 |

**总计代码量变化**：6 个文件型类从 ~550 行缩减到 ~260 行，去重管道减少 ~40 行样板，净删约 **~330 行**。

## 五、附录

### 5.1 各文件当前代码量

| 文件 | 行数 | 类数 | 继承 |
|------|:---:|:---:|------|
| `base_pipeline.py` | 624 | 7 | — |
| `dedup/bloom.py` | 100 | 1 | `DedupPipeline` ✅ |
| `console.py` | 59 | 1 | `BasePipeline` 🟡 |
| `file/csv.py` | 180 | 2 | `FileBasedPipeline` ✅ |
| `dedup/mysql.py` | 141 | 1 | `DedupPipeline` ✅ |
| `file/json.py` | 210 | 3 | `FileBasedPipeline` ✅ |
| `dedup/memory.py` | 89 | 1 | `DedupPipeline` ✅ |
| `manager.py` | 214 | 1 | `object` |
| `dedup/redis.py` | 144 | 1 | `DedupPipeline` ✅ |

### 5.2 与 db-pipelines-design.md 的分工

| 关注点 | db-pipelines-design.md | 本文档 |
|--------|:---:|:---:|
| SQL 数据库 Pipeline | ✅ | — |
| 文档型数据库 Pipeline | ✅ | — |
| SQLDialect / PoolManager | ✅ | — |
| 文件型 Pipeline | — | ✅ |
| 去重 Pipeline | — | ✅ |
| 基类层次优化 | ✅（SQL 侧） | ✅（Dedup/File 侧） |
| ConsolePipeline | — | ✅ |

### 5.3 v1.0 → v1.1 修正记录

| # | 问题 | 修正内容 |
|---|------|---------|
| 1 | §3.4 错误声称 `DedupPipeline` 使用 `@abstractmethod` | 重写 §3.4：实际无 `@abstractmethod`（`DedupPipeline` 是具体实现），子类空壳是**非必要的冗余重写**而非 abstractmethod 强制 |
| 2 | §3.2 使用 `_fingerprints` 而非实际属性名 | `_fingerprints` → `seen_items`，与 `memory_dedup_pipeline.py:37` 保持一致 |
| 3 | §3.1 csv.writer + aiofiles 不兼容未说明 | 在代码注释 + 说明框补充：csv.writer 要求同步 `write()`，CSV 管道应禁用 aiofiles 或通过 `run_in_executor` 执行 |
| 4 | §3.7 `ConsolePipeline.__init__` super() 不可行 | 修正为"保持现状"，因 `BasePipeline` 无 `__init__`，`super().__init__(crawler)` 会报错 |
| 5 | RedisDedupPipeline DCL 复用方案缺失 | 新增 §3.6.1：分析 MRO 菱形冲突，推荐在 `_initialize_resources` 中完成连接建立，不追求复用 `CacheBasedPipeline` |
| 6 | §3.5 仅修复 `_flush_to_temp_file`，遗漏 spider_closed 3 处同步 I/O | 列出全部 4 处同步调用（含行号），补充 `_merge_temp_files` 异步化代码 |
| 7 | §1.1 过度简化 JSON 管道差异 | 替换为完整差异表（序列化格式/元数据/计数/统计 key），明确合并策略 |
| 8 | 文件型 Pipeline 清理路径变更未说明 | 新增 §3.8 + §1.2：说明从事件驱动迁移到 PipelineManager 驱动的注意事项（移除 subscribe、删除 spider_closed、避免双重关闭） |
