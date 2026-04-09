# 检查点持久化 (Checkpoint)

检查点功能支持爬取过程的**持久化存储**与**断点续爬**。当爬虫被 Ctrl+C 中断或优雅关闭时，系统会自动保存当前状态（待处理请求、去重指纹、统计信息），重启时自动从断点继续。

**检查点功能默认始终启用**，无需额外配置。

## 1. 工作原理

```
爬虫运行中 ──Ctrl+C──> 保存检查点 ──重启──> 加载检查点 ──> 从断点续爬
                     (请求+指纹+统计)     (恢复队列)
```

### 保存时机

| 场景 | 是否保存检查点 | 说明 |
|------|---------------|------|
| `Ctrl+C` / 优雅关闭 | ✅ 是 | 关闭原因 = `shutdown` |
| 正常完成 | ❌ 否 | 关闭原因 = `finished`，自动清除检查点 |
| 异常崩溃 | ❌ 否 | 可通过配置启用信号保存 |

### 存储内容

- **待处理请求**：内存队列中尚未抓取的所有 Request 对象
- **去重指纹**：已抓取请求的指纹集合（用于避免重复）
- **统计信息**：下载数、错误数等运行时统计

### 与 Redis 的关系

Redis 队列模式下，请求天然持久化（已在 Redis 中）。检查点主要解决**单机模式（Memory 队列）**的持久化问题，并统一恢复指纹和统计信息。

---

## 2. 配置选项

在 `settings.py` 或 `crawlo.cfg` 中配置：

```python
# 存储后端：'json'（默认）或 'sqlite'
CHECKPOINT_STORAGE = 'json'

# 检查点存储目录（默认项目根目录下的 .crawlo_checkpoints/{project}/{spider}）
CHECKPOINT_DIR = None

# Ctrl+C 时是否自动保存（默认启用）
CHECKPOINT_SAVE_ON_SIGNAL = True
```

### 存储后端对比

| 特性 | JSON（默认） | SQLite |
|------|-------------|--------|
| 适用场景 | 小规模爬虫（< 10000 请求） | 大规模爬虫（> 10000 请求） |
| 性能 | 中等（JSON 序列化/反序列化） | 高（数据库索引） |
| 文件大小 | 较大（文本格式） | 较小（二进制） |
| 可读性 | ✅ 可直接编辑查看 | ❌ 需 SQLite 客户端 |

---

## 3. 命令行使用

### 恢复爬取（默认行为）

```bash
crawlo run myspider
```

如果存在检查点文件，自动从断点续爬。

### 从头开始（忽略检查点）

```bash
# 方式1：忽略检查点，但不删除
crawlo run myspider --fresh

# 方式2：同上，语义更明确
crawlo run myspider --no-resume
```

### 清除检查点并从头开始

```bash
crawlo run myspider --clean-checkpoint
```

会先删除检查点文件，再从头运行爬虫。

### 禁用检查点功能

检查点功能**始终启用**，无法通过配置禁用。如果不想恢复检查点，可以使用：

```bash
# 忽略检查点，从头开始（但检查点仍会保存）
crawlo run myspider --fresh
```

---

## 4. 存储路径

检查点文件的默认存储路径：

```
.crawlo_checkpoints/
└── {project_name}/
    └── {spider_name}.json    # JSON 后端
    └── {spider_name}.db      # SQLite 后端
```

示例：

```
.crawlo_checkpoints/
└── myproject/
    └── news_spider.json
```

> **注意**：检查点存储在**项目根目录**下，方便管理和版本控制（建议将 `.crawlo_checkpoints/` 加入 `.gitignore`）。

---

## 5. 编程接口

### 在代码中使用 CheckpointManager

```python
from crawlo.checkpoint import CheckpointManager

# 创建管理器
manager = CheckpointManager(spider_name='myspider', settings=settings)

# 检查是否存在检查点
if await manager.has_checkpoint():
    print("找到检查点，可以恢复")

# 保存检查点
success = await manager.save(scheduler=scheduler, stats=stats)

# 加载检查点
data = await manager.load()
if data:
    print(f"待处理请求: {data['pending_count']}")
    print(f"指纹数量: {len(data['fingerprints'])}")

# 恢复单个请求
request = manager.restore_request(data['requests'][0])

# 清除检查点
await manager.clear()
```

### 在 Spider 中手动保存

```python
class MySpider(Spider):
    async def parse(self, response):
        # ... 爬取逻辑 ...
        
        # 每处理 100 页手动保存一次
        if self.crawl_count % 100 == 0:
            await self.crawler.engine._save_checkpoint()
```

---

## 6. 注意事项

### 内存队列 vs Redis 队列

- **Memory 队列**：检查点是唯一的持久化手段，**必须启用**
- **Redis 队列**：请求已在 Redis 中持久化，检查点只保存指纹和统计信息

### 检查点一致性

- 检查点保存是**原子操作**（先写临时文件，再重命名）
- 如果保存过程中断，旧的检查点文件不会被损坏

### 版本兼容性

- 检查点文件格式可能随 Crawlo 版本变化
- 建议升级 Crawlo 后使用 `--clean-checkpoint` 清除旧检查点

### 性能影响

- JSON 后端：保存/加载时间与请求数成正比（10000 请求约 1-2 秒）
- SQLite 后端：几乎恒定时间（数据库索引优化）
- 正常完成时不保存检查点，**无性能影响**

---

## 7. 故障排查

### 检查点未保存

1. 检查关闭原因：必须是 `reason='shutdown'`（Ctrl+C）
2. 查看日志：搜索 `Checkpoint saved` 关键字

### 检查点未恢复

1. 确认检查点文件存在：`ls .crawlo_checkpoints/{project}/{spider}.json`
2. 检查 `--fresh` 或 `--no-resume` 参数是否误用
3. 查看日志：搜索 `Checkpoint loaded` 关键字

### 检查点文件过大

1. 切换到 SQLite 后端：`CHECKPOINT_STORAGE = 'sqlite'`
2. 正常完成后检查点会自动清除
3. 手动清理：`crawlo run myspider --clean-checkpoint`
