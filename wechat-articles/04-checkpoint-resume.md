# 爬虫跑到一半崩了怎么办？Crawlo 断点续爬实战

> 一个凌晨 3 点的故事：服务器重启了，你的爬虫进度全没了。

---

## 凌晨 3 点的噩梦

你花了 6 个小时爬了一个 100 万页的网站，爬到 80 万页的时候——

- 服务器内存溢出，进程被 OOM Killer 杀了
- 云厂商维护，机器重启了
- 你的笔记本合盖了

**20 小时的进度，归零。**

如果你用 Crawlo，可以最大程度避免数据丢失。

---

## Crawlo 断点续爬：启用即生效

Crawlo 支持检查点（Checkpoint）功能，保存爬取进度并在下次启动时自动恢复。

### 启用

```python
# settings.py
CHECKPOINT_ENABLED = True
```

### 默认行为

- **Ctrl+C（SIGINT/SIGTERM）**：自动保存检查点，包含已爬 URL 指纹 + 待爬队列 + 统计信息
- **正常完成**：自动清除检查点
- **再次启动**：检测到检查点存在，自动恢复并续爬
- **Ctrl+C 保存**由 `CHECKPOINT_SAVE_ON_SIGNAL = True`（默认）控制

---

## 检查点保存了什么？

| 保存内容 | 说明 |
|----------|------|
| 已爬 URL 指纹 | 恢复后避免重复爬取 |
| 待爬请求队列 | 完整的请求对象（含 callback、meta） |
| 爬取统计 | 已爬数量、时间戳等元信息 |

### 存储后端

支持两种存储方式：

```python
CHECKPOINT_STORAGE = 'json'    # JSON 文件（默认，适合小规模）
CHECKPOINT_STORAGE = 'sqlite'  # SQLite（适合大规模指纹集合）
```

**JSON 模式**：单个文件 `.checkpoints/{project}/{spider}.json`

**SQLite 模式**：单个文件 `.checkpoints/{project}/{spider}.db`

---

## 配置选项

```python
# settings.py

CHECKPOINT_ENABLED = True       # 是否启用检查点（默认关闭）
CHECKPOINT_STORAGE = 'json'     # 存储后端：json | sqlite
CHECKPOINT_DIR = None           # 自定义存储目录
CHECKPOINT_SAVE_ON_SIGNAL = True  # Ctrl+C 时是否保存
```

---

## 与 Scrapy Jobdir 的对比

| 特性 | Crawlo Checkpoint | Scrapy Jobdir |
|------|-------------------|---------------|
| 启用方式 | 配置 `CHECKPOINT_ENABLED=True` | 需命令行 `-s JOBDIR=xxx` |
| 保存内容 | 全量（指纹+队列+元信息） | 部分（仅队列） |
| 恢复去重 | ✅ 已爬 URL 不重爬 | ❌ 可能重复爬取 |
| 自动清理 | ✅ 正常完成后自动清除 | ❌ 需手动删除 |
| callback 恢复 | ✅ 恢复 callback/errback | ❌ 丢失 |

---

## 分布式模式的检查点

分布式模式使用 Redis 去重 + Redis 队列，检查点状态天然保存在 Redis 中，Worker 重启后自动恢复。

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
