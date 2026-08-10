# 升级与回滚指南

> 与 [发布纪律](../reference/DEPRECATION.md) 配套的运维侧操作手册：
> 版本升级前怎么检查、升级怎么执行、出问题怎么回滚、数据怎么保兼容。

## 1. 升级前检查（发布就绪度）

每个版本发布前，仓库自带检查命令：

```bash
# 只检查发布就绪度（不跑测试）
crawlo release --dry-run

# 检查 + 跑全量测试（正式发版前）
crawlo release
```

检查项：

| 检查 | 说明 |
|---|---|
| 版本号 | `crawlo/__version__.py` 必须是合法 semver（MAJOR.MINOR.PATCH） |
| CHANGELOG | 必须存在当前版本条目（`## [x.y.z] - YYYY-MM-DD`），且无重复 |
| 发布说明 | `docs/releases/v{x.y.z}.md` 必须存在 |
| Git tag | HEAD 的 tag 必须与版本号一致 |
| 测试 | 非 dry-run 时全量测试套件必须通过 |

## 2. 升级决策：Breaking vs 兼容

升级前先读 `docs/releases/v{x.y.z}.md` 的 **Breaking Changes**章节
和 [DEPRECATION.md](../reference/DEPRECATION.md)：

| 情况 | 升级策略 |
|---|---|
| 纯兼容升级（minor/patch） | 直接升级，无需改代码 |
| 涉及 deprecated 符号 | 先按迁移指南改代码（旧路径仍在，带 DeprecationWarning） |
| 涉及 breaking change | 逐个核对迁移映射表，先改后升 |

> Crawlo 的 Deprecation 规则：公开符号移除前至少经过 **2 个 minor 版本**> 的警告期。1.7.4 起 `crawlo.bot` 属刻意提前的 breaking change
> （见 [v1.7.3 发布说明](../releases/v1.7.3.md)），升级前务必检查代码里
> 是否还有 `from crawlo.bot import ...`。

## 3. 升级步骤

### 3.1 静态代理 / 单机模式

```bash
# 1. 备份当前依赖锁定
pip freeze > requirements-backup.txt

# 2. 升级 Crawlo
pip install --upgrade crawlo

# 3. 验证导入（新版本不应产生 DeprecationWarning 异常）
python -c "import crawlo; print(crawlo.__version__)"

# 4. 跑一次冒烟爬虫（小范围）
crawlo run myspider
```

### 3.2 分布式模式

```bash
# 1. 滚动升级：先升级一半 Worker，观察队列健康
# 注意：同队列中混用版本可能导致序列化不兼容
# （QUEUE_SERIALIZATION_FORMAT 变更时务必整群升级）

# 2. 全部 Worker 升级后，验证：
# - Redis 队列无积压异常（crawlo_queue_size）
# - 无 XCLAIM 风暴（Stream Pending 数稳定）
# - 死信队列无误报
```

### 3.3 断点续爬升级

升级前若启用检查点：

```bash
# 检查点目录独立于代码，升级后自动恢复
CHECKPOINT_ENABLED=True crawlo run myspider

# 若升级涉及 item 字段结构变化，先清空旧检查点避免字段不匹配
crawlo run myspider --clean-checkpoint
```

> 检查点（`CHECKPOINT_DIR`）与去重指纹（Redis）是**跨版本数据**：
> 升级只影响代码，不影响已抓取状态；但 schema 变更时需主动清理。

## 4. 回滚方案

### 4.1 快速回滚（未涉及数据迁移）

```bash
# 回退到备份版本
pip install crawlo==<上一个版本>

# 验证
crawlo release --dry-run # 用仓库代码时
crawlo run myspider
```

### 4.2 容器化回滚（推荐）

镜像按版本打 tag，回滚即切换 tag：

```bash
# 升级：新镜像
docker compose up -d --build

# 回滚：切回旧 tag（数据卷保持不变）
docker compose up -d
# 或直接指定旧镜像
docker run my-crawler:1.7.3
```

详见 [Docker 部署](docker-deployment.md)。

### 4.3 回滚决策矩阵

| 场景 | 回滚 | 不回滚 |
|---|---|---|
| 新版本 import 报错 | ✅ 立即回滚 | |
| 吞吐/错误率异常（监控告警触发） | ✅ 回滚并保留现场 | |
| 数据 schema 已迁移 | | ⚠️ 先评估逆向迁移成本 |
| 仅指标异常但任务正常 | | 先排查，再决定 |

> **重要**：分布式模式下升级后 Redis 里的队列/指纹数据属于新版本格式时，
> 回滚到旧版本可能无法读取。升级前对关键任务做好 Redis 快照
> （`redis-cli BGSAVE` + 备份 dump.rdb）。

## 5. 升级演练清单

- [ ] `crawlo release --dry-run` 通过
- [ ] 阅读 Breaking Changes / DEPRECATION 迁移说明
- [ ] 代码中无 deprecated 导入（`rg "crawlo.bot|crawlo.network" .` 等）
- [ ] 升级前 Redis 快照 + requirements 备份
- [ ] 冒烟爬虫通过
- [ ] 监控指标正常（吞吐/错误率/队列）
- [ ] 回滚路径已确认（镜像 tag / pip 版本）
