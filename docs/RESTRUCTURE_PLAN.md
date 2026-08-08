# Crawlo 框架包结构重构方案

> **版本**: v1.0
> **日期**: 2026-08-08
> **作者**: 资深爬虫开发工程师视角
> **状态**: 待评审

---

## 目录

- [1. 背景与动机](#1-背景与动机)
- [2. 现状分析](#2-现状分析)
- [3. 对标框架研究](#3-对标框架研究)
- [4. 问题清单](#4-问题清单)
- [5. 重构目标](#5-重构目标)
- [6. 详细方案](#6-详细方案)
  - [6.1 Phase 1：低风险合并与迁移](#61-phase-1低风险合并与迁移)
  - [6.2 Phase 2：core 拆分与分布式收敛](#62-phase-2core-拆分与分布式收敛)
  - [6.3 Phase 3：生命周期收敛与降级](#63-phase-3生命周期收敛与降级)
- [7. 目标结构总览](#7-目标结构总览)
- [8. 零破坏迁移策略](#8-零破坏迁移策略)
- [9. 测试与验证](#9-测试与验证)
- [10. 风险评估](#10-风险评估)
- [11. 时间线建议](#11-时间线建议)
- [附录 A：完整迁移对照表](#附录-a完整迁移对照表)
- [附录 B：包间依赖关系图](#附录-b包间依赖关系图)

---

## 1. 背景与动机

Crawlo 经过多轮迭代，从单机爬虫发展到支持分布式、多队列后端、多下载器的全功能框架。但功能的快速叠加导致了包结构的无序膨胀：

- 顶层子包从最初的 ~10 个增长到 **27 个**
- `utils/` 沦为"什么都能往里扔"的垃圾场（39 文件 / 7,476 行）
- 生命周期管理散落在 **6 个不同位置**
- 分布式协调逻辑分裂在 `cluster/` 和 `core/engine_cluster.py` 两处
- `helpers/` 与 `utils/` 职责重叠，开发者不确定新代码归属

这些问题不影响功能正确性，但严重影响：
1. **开源用户的学习曲线**——包结构是用户的第一印象
2. **贡献者的代码归属判断**——不知道新功能该放哪个包
3. **维护者的认知负载**——改一个功能要跨多个包
4. **框架的专业度感知**——27 个子包的框架看起来像"拼凑"而非"设计"

---

## 2. 现状分析

### 2.1 量化数据

| 指标 | 数值 |
|------|------|
| 顶层子包数 | 27 |
| 顶层 .py 文件 | 10 |
| 总 .py 文件数 | ~288 |
| 总代码行数 | ~58,000 |
| 最大子包 | `utils/`（39 文件 / 7,476 行） |
| 最小子包 | `shell/`（2 文件 / 604 行） |

### 2.2 各子包规模

| 子包 | 文件数 | 代码行数 | 关注点 |
|------|--------|----------|--------|
| `utils/` | 39 | 7,476 | 混合：DB/Redis/编码/请求/异步/进程… |
| `core/` | 20 | 5,426 | 混合：Engine/Config/Task/Error/基础设施 |
| `pipelines/` | 24 | 4,089 | 数据管道（结构良好，有子包） |
| `bot/` | 21 | 3,871 | 通知机器人（过度工程化） |
| `downloader/` | 19 | 5,863 | 7 种下载器后端平铺 |
| `middleware/` | 16 | 3,173 | 16 个中间件（基本合理） |
| `queue/` | 15 | 5,612 | 4 种队列后端 + 管理/背压/类型 |
| `extension/` | 14 | 1,969 | 扩展（monitor 子目录已有） |
| `commands/` | 13 | 2,797 | CLI 命令 |
| `cluster/` | 10 | 2,066 | 分布式集群协调 |
| `helpers/` | 9 | 2,336 | 辅助工具（与 utils 重叠） |
| `initialization/` | 7 | 1,283 | 框架初始化系统 |
| `scheduling/` | 7 | 895 | 任务调度（含 daemon/） |
| `backpressure/` | 6 | 1,655 | 背压控制 |
| `spider/` | 6 | 1,521 | 爬虫基类与注册 |
| `stats/` | 5 | 1,070 | 统计收集 |
| `network/` | 5 | 1,848 | Request/Response 封装 |
| `items/` | 5 | 333 | Item/Field 数据模型 |
| `factories/` | 5 | 551 | 组件工厂 |
| `filters/` | 4 | 1,106 | 去重过滤器 |
| `logging/` | 4 | 652 | 日志系统 |
| `checkpoint/` | 3 | 849 | 检查点 |
| `db/` | 3 | 347 | 数据库方言与连接池 |
| `mcp/` | 3 | 1,172 | MCP 服务 |
| `settings/` | 3 | 1,471 | 配置管理 |
| `shell/` | 2 | 604 | 交互式 Shell |
| `templates/` | 0 | 0 | 项目模板（.tmpl 文件） |

### 2.3 跨包依赖热度

以下数据表示"该包被多少个外部文件 import"（热度越高说明越基础）：

| 包 | 被引用次数 | 角色 |
|----|-----------|------|
| `utils/` | 56 | 基础工具层 |
| `core/` | 48 | 核心引擎 |
| `network/` | 31 | 领域对象（Request/Response） |
| `items/` | 13 | 数据模型 |
| `settings/` | 14 | 配置 |
| `spider/` | 11 | 爬虫基类 |
| `initialization/` | 8 | 框架初始化 |
| `queue/` | 5 | 队列管理 |
| `backpressure/` | 4 | 背压控制 |
| `stats/` | 3 | 统计 |
| `extension/` | 3 | 扩展 |
| `filters/` | 0 | 去重（仅通过 Scheduler 间接使用） |

---

## 3. 对标框架研究

### 3.1 Scrapy（Python 爬虫标杆）

```
scrapy/
├── __init__.py
├── cmdline.py           # CLI 入口
├── crawler.py           # Crawler + CrawlerProcess（2 个类，1 个文件）
├── engine.py            # 引擎（1 个文件，不是 4 个）
├── extensions.py        # 扩展（1 个文件，后期拆为 extensions/）
├── http/                # Request/Response（命名清晰）
├── spider/              # 爬虫基类
├── downloader/          # 下载器
├── middleware/          # 中间件
├── pipelines/           # 管道
├── core/                # 调度器/爬虫队列
├── commands/            # CLI 命令
├── settings/            # 配置
├── stats/               # 统计
├── utils/               # 通用工具（只有 misc 函数，不是垃圾场）
├── linkextractors/      # 链接提取
├── loader/              # Item Loader
├── selector/            # 选择器
├── signals/             # 信号（事件）
├── templates/           # 模板
└── logformatter.py      # 日志格式
```

**Scrapy 的设计原则**：
- 生命周期管理集中在 `crawler.py` 一个文件（`Crawler` + `CrawlerProcess`）
- `utils/` 只放通用辅助函数（`python.py`、`url.py`、`log.py`、`misc.py`），不混入 DB/Redis/请求等领域工具
- 引擎只有一个 `engine.py`，不需要拆 4 个文件
- Request/Response 放在 `http/` 下，语义清晰
- 扩展（extensions）是平级概念，不会比核心引擎还大

### 3.2 Crawlee（新一代 Python 爬虫）

```
crawlee/
├── __init__.py
├── _autoscaling/        # 自动伸缩
├── _utils/              # 内部工具（下划线前缀表示内部）
├── statistics/          # 统计
├── storage_client/      # 存储客户端
├── http_clients/        # HTTP 客户端
├── processors/          # 数据处理
├── strategies/          # 策略（重试、会话等）
├── sessions/            # 会话管理
├── proxy/               # 代理
├── browsers/            # 浏览器自动化
├── crawlers/            # 爬虫类型
└── configuration.py     # 配置
```

**Crawlee 的设计原则**：
- 内部工具用 `_utils/` 下划线前缀，与公共 API 明确区分
- 每个"能力域"一个包，不混入其他域的工具
- 没有 `core/` 这个大杂烩，引擎逻辑在 `crawlers/` 下

### 3.3 对标结论

| 维度 | Scrapy | Crawlee | Crawlo（现状） | Crawlo（目标） |
|------|--------|---------|---------------|---------------|
| 子包数 | ~15 | ~12 | 27 | 15 |
| 生命周期管理位置 | 1 处 | 1 处 | 6 处 | 1 处 |
| utils 是否含领域工具 | 否 | 否（有 `_utils`） | 是（DB/Redis/请求） | 否 |
| Engine 文件数 | 1 | 1-2 | 4 | 1（+子包） |
| Request/Response 位置 | `http/` | 内嵌 | `network/` | `http/` |
| 通知系统 | 扩展的一部分 | 无 | 独立大包（21 文件） | 扩展子模块 |

---

## 4. 问题清单

### 4.1 结构性硬伤（高优先级）

#### P0-1: `utils/` 是垃圾场

**现状**: 39 个文件，包含 DB 连接池、Redis 工具、编码检测、请求序列化、fingerprint、curl 解析、异步锁、进程工具等完全不同领域的代码。

**影响**: 新贡献者不知道新工具该放 `utils/` 还是 `helpers/`；查找特定工具需要在两个包中搜索；`utils/` 的 import 链过长，任何模块 import `utils/` 都会触发不必要的依赖加载。

**对比**: Scrapy 的 `utils/` 只有 `python.py`、`url.py`、`log.py`、`misc.py` 等通用函数；Crawlee 用 `_utils/` 明确标记为内部工具。

#### P0-2: 生命周期管理散落 6 处

**现状**:

| 位置 | 文件数 | 职责 |
|------|--------|------|
| `crawler.py` | 1 | Crawler 核心控制器 |
| `crawler_process.py` | 1 | 进程管理器 |
| `framework.py` | 1 | 框架门面（Facade） |
| `container.py` | 1 | 依赖注入容器 |
| `initialization/` | 7 | 框架初始化系统 |
| `factories/` | 5 | 组件工厂 |

共 **6 处 / 16 文件**管理框架的启动、组件注册、依赖注入。

**影响**: 理解框架启动流程需要跨 6 个位置追踪；`framework.py` 和 `crawler_process.py` 职责模糊（都是"运行爬虫"的入口）；`container.py` 和 `initialization/` 都管"组件注册"但方式不同。

**对比**: Scrapy 只有 `crawler.py` 一个文件（`Crawler` + `CrawlerProcess`），一切初始化在 `Crawler._bootstrap()` 内完成。

#### P0-3: 分布式逻辑分裂两处

**现状**:
- `cluster/`（10 文件）：registry / heartbeat / failover / lock / messaging / monitor / progress / rate_limiter / config
- `core/engine_cluster.py`（760 行）：种子锁 / Leader 选举 / Coordinated Shutdown / Worker 注册

**影响**: 修改分布式协调逻辑需要同时改两个包；`engine_cluster.py` 本质上是 `ClusterMixin`，混在 `core/` 中既不属于 Engine 核心也不属于 Config，分类不清；种子锁的 Lua 脚本在 `core/` 里，但锁的 Redis key 结构在 `cluster/` 里。

### 4.2 中优先级问题

#### P1-1: `helpers/` 与 `utils/` 职责重叠

`helpers/` 有 `text_cleaner`、`time_utils`、`mysql_exists_checker`、`file_downloader`、`adaptive_selector`；`utils/` 也有 `encoding/`、`parsing/`、`db/` 等类似功能。两个"工具"包并存，开发者不知道该往哪放新代码。

#### P1-2: `bot/` 过度工程化

21 个文件 / 3,871 行做通知系统（钉钉/飞书/邮件/短信/企微），比核心引擎（`core/` 5,426 行）少不了多少。在 Scrapy 中这只是 extensions 的一个子模块。

#### P1-3: `backpressure/` 与 `queue/` 耦合但分离

背压逻辑（6 文件）与队列管理（15 文件）紧密耦合——`queue_backpressure.py` 在 `queue/` 里，`strategies/` 和 `interfaces.py` 在 `backpressure/` 里。改背压策略要跨两个包。

#### P1-4: `network/` 太薄且位置不对

只有 5 个文件（Request / Response / response_adaptive / exceptions / __init__），但 Request/Response 是框架的核心领域对象，不应放在一个叫"network"的边缘包里。Scrapy 把它们直接放在 `scrapy.http/` 下。

### 4.3 低优先级问题

#### P2-1: `scheduling/` 与 `commands/` 职责重叠

`scheduling/daemon/` 做 cron 调度，`commands/` 也有 `schedule.py` 和 `job_executor.py`。任务调度的入口分散在两个包里。

#### P2-2: `mcp/` 不属于核心框架

MCP server（3 文件 / 1,172 行）是一个独立工具，不是爬虫框架的核心能力。应拆为独立插件或独立仓库。

#### P2-3: `shell/` 只有一个命令

`shell/`（2 文件 / 604 行）本质上只是一个 CLI 命令，不需要独立包。应合入 `commands/shell.py`。

#### P2-4: 命名不一致

- `pipelines/`（复数）vs `extension/`（单数）——应对齐为复数
- `network/` ——语义不如 `http/` 清晰（对齐 Scrapy）

---

## 5. 重构目标

### 5.1 核心原则

1. **一个关注点只在一个地方**——分布式逻辑不再分裂 core/cluster 两处；生命周期管理不再散落 6 个位置
2. **工具包按领域内聚**——helpers 合入 utils，db 合入 utils/db，不再有"不知道往哪放"的困惑
3. **对齐主流框架命名**——http/pipeline/extensions 与 Scrapy 对齐，降低开源用户学习成本
4. **零破坏迁移**——通过 `__init__.py` re-export 保持 `from crawlo.xxx import Yyy` 的外部路径不变

### 5.2 量化目标

| 指标 | 现状 | 目标 |
|------|------|------|
| 顶层子包数 | 27 | 15 |
| 生命周期管理位置 | 6 处 | 1 处 |
| utils 文件数 | 39 | ~25（合并 helpers 后，但清理域工具归属） |
| core 文件数（顶层） | 20 | 7（含子包） |
| 分布式逻辑位置 | 2 处 | 1 处 |

---

## 6. 详细方案

### 6.1 Phase 1：低风险合并与迁移

> **风险等级**: 低
> **影响范围**: 边缘包，不触及核心引擎逻辑
> **可独立提交**: 是

#### 6.1.1 `helpers/` → `utils/`

**操作**: 将 `helpers/` 的所有文件合并入 `utils/`，保留 `helpers/` 目录但只留 `__init__.py` 做 re-export。

**文件映射**:

| 源文件 | 目标位置 | 说明 |
|--------|---------|------|
| `helpers/text_cleaner.py` | `utils/text/cleaner.py` | 新建 `utils/text/` 子包 |
| `helpers/time_utils.py` | `utils/time_utils.py` | 时间工具属于通用工具 |
| `helpers/mysql_exists_checker.py` | `utils/db/mysql_exists_checker.py` | DB 相关工具归入 `utils/db/` |
| `helpers/file_downloader.py` | `utils/file_downloader.py` | 文件下载属于通用工具 |
| `helpers/adaptive_selector/` | `utils/adaptive_selector/` | 整个子目录迁移 |

**兼容层** (`helpers/__init__.py`):
```python
# deprecated: use crawlo.utils instead
from crawlo.utils.text.cleaner import *
from crawlo.utils.time_utils import *
# ...
import warnings
warnings.warn("crawlo.helpers is deprecated, use crawlo.utils", DeprecationWarning, stacklevel=2)
```

#### 6.1.2 `db/` → `utils/db/`

**操作**: 将独立的 `db/` 包（3 文件：dialect.py / pool_manager.py / __init__.py）合入已有的 `utils/db/`。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `db/dialect.py` | `utils/db/dialect.py` |
| `db/pool_manager.py` | `utils/db/pool_manager.py` |

**兼容层** (`db/__init__.py`): re-export from `utils.db`。

#### 6.1.3 `shell/` → `commands/shell.py`

**操作**: 将 `shell/` 的 `core.py` 内容合入 `commands/shell.py`，删除 `shell/` 包。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `shell/core.py` | `commands/shell.py`（合并） |

**兼容层** (`shell/__init__.py`): re-export from `crawlo.commands.shell`。

#### 6.1.4 `backpressure/` → `queue/backpressure/`

**操作**: 将 `backpressure/` 整个包移入 `queue/` 作为子包。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `backpressure/strategies.py` | `queue/backpressure/strategies.py` |
| `backpressure/intelligent_calculator.py` | `queue/backpressure/calculator.py` |
| `backpressure/metrics_collector.py` | `queue/backpressure/metrics.py` |
| `backpressure/monitor.py` | `queue/backpressure/monitor.py` |
| `backpressure/interfaces.py` | `queue/backpressure/interfaces.py` |

**兼容层** (`backpressure/__init__.py`): re-export from `crawlo.queue.backpressure`。

#### 6.1.5 Phase 1 验证清单

- [ ] `from crawlo.helpers.text_cleaner import TextCleaner` 仍可工作
- [ ] `from crawlo.db.dialect import Dialect` 仍可工作
- [ ] `from crawlo.shell.core import Shell` 仍可工作
- [ ] `from crawlo.backpressure.strategies import QueueSizeStrategy` 仍可工作
- [ ] `crawlo run` CLI 命令正常执行
- [ ] 10 Worker 分布式测试正常执行
- [ ] `pytest tests/` 全部通过

---

### 6.2 Phase 2：core 拆分与分布式收敛

> **风险等级**: 中
> **影响范围**: core/ 内部结构 + cluster/ + network/
> **可独立提交**: 是（但需要在 Phase 1 之后）

#### 6.2.1 `core/` 内部拆子包

**操作**: 将 `core/` 的 20 个文件按关注点拆为 4 个顶层文件 + 3 个子包。

**文件映射**:

| 源文件 | 目标位置 | 说明 |
|--------|---------|------|
| `core/engine.py` | `core/engine.py` | 保持 |
| `core/application.py` | `core/application.py` | 保持 |
| `core/processor.py` | `core/processor.py` | 保持 |
| `core/interfaces.py` | `core/interfaces.py` | 保持 |
| `core/singleton.py` | `core/singleton.py` | 保持 |
| `core/error_types.py` + `core/exceptions.py` + `core/failure.py` | `core/errors.py` | 3 文件合并为 1 |
| `core/engine_cluster.py` | `cluster/coordinator.py` | 移入 cluster/（见 6.2.4） |
| `core/engine_generation.py` | `core/engine/generation.py` | 移入 engine/ 子包 |
| `core/engine_helpers.py` | `core/engine/helpers.py` | 移入 engine/ 子包 |
| `core/config.py` | `core/config/__init__.py` | 移入 config/ 子包 |
| `core/config_base.py` | `core/config/base.py` | |
| `core/config_compat.py` | `core/config/compat.py` | |
| `core/config_factories.py` | `core/config/factories.py` | |
| `core/config_validator.py` | `core/config/validator.py` | |
| `core/task_manager.py` | `core/scheduling/task_manager.py` | 移入 scheduling/ 子包 |
| `core/task_scheduler.py` | `core/scheduling/task_scheduler.py` | |
| `core/checkpoint_coordinator.py` | `core/checkpoint_coordinator.py` | 保持（薄协调器） |

**新结构**:
```
core/
├── __init__.py                 # public API (不变)
├── application.py              # 应用上下文
├── engine.py                   # 引擎核心
├── processor.py                # 处理器
├── interfaces.py               # 接口定义
├── singleton.py                # 单例模式
├── errors.py                   # 合并 error_types + exceptions + failure
├── checkpoint_coordinator.py   # 检查点协调器
├── engine/                     # Engine 家族
│   ├── __init__.py             # re-export Engine, ClusterMixin 等
│   ├── generation.py           # was engine_generation.py
│   └── helpers.py              # was engine_helpers.py
├── config/                     # Config 家族
│   ├── __init__.py             # re-export CrawloConfig, ConfigBase 等
│   ├── base.py                 # was config_base.py
│   ├── factories.py            # was config_factories.py + config.py
│   ├── compat.py               # was config_compat.py
│   └── validator.py            # was config_validator.py
└── scheduling/                 # Task 家族
    ├── __init__.py
    ├── task_manager.py
    └── task_scheduler.py
```

**兼容层**: `core/__init__.py` 中 re-export 所有旧路径：
```python
# 向后兼容：旧 import 路径仍可用
from crawlo.core.engine.generation import *  # was crawlo.core.engine_generation
from crawlo.core.engine.helpers import *     # was crawlo.core.engine_helpers
from crawlo.core.config.base import *        # was crawlo.core.config_base
from crawlo.core.config.factories import *   # was crawlo.core.config_factories
from crawlo.core.config.compat import *      # was crawlo.core.config_compat
from crawlo.core.config.validator import *   # was crawlo.core.config_validator
from crawlo.core.scheduling.task_manager import *    # was crawlo.core.task_manager
from crawlo.core.scheduling.task_scheduler import *  # was crawlo.core.task_scheduler
```

#### 6.2.2 `network/` → `http/`

**操作**: 重命名 `network/` 为 `http/`，对齐 Scrapy 命名。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `network/request.py` | `http/request.py` |
| `network/response.py` | `http/response.py` |
| `network/response_adaptive.py` | `http/response_adaptive.py` |
| `network/exceptions.py` | `http/exceptions.py` |

**兼容层** (`network/__init__.py`): re-export from `crawlo.http`。

#### 6.2.3 队列后端拆分

**操作**: 将 `queue/` 中的 4 种队列后端实现移入 `backends/` 子包。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `queue/memory_queue.py` | `queue/backends/memory.py` |
| `queue/disk_queue.py` | `queue/backends/disk.py` |
| `queue/redis_priority_queue.py` | `queue/backends/redis_priority.py` |
| `queue/redis_stream_queue.py` | `queue/backends/redis_stream.py` |

**保留在 `queue/` 顶层的**：`queue_manager.py`、`queue_backpressure.py`、`queue_helper.py`、`queue_status.py`、`queue_types.py`、`priority_calculator.py`、`task_tracker.py`、`config.py`、`exceptions.py`、`interfaces.py`。

**兼容层**: `queue/__init__.py` 中 re-export 旧路径。

#### 6.2.4 `core/engine_cluster.py` → `cluster/coordinator.py`

**操作**: 将 `core/engine_cluster.py` 的 `ClusterMixin` 类移入 `cluster/` 包，重命名为 `ClusterCoordinator`。

**设计变更**:
```python
# 旧设计: Engine 通过 Mixin 继承获得集群能力
class Engine(EngineGeneration, ClusterMixin, ...):
    ...

# 新设计: Engine 通过组合使用集群协调器
class Engine:
    def __init__(self, ...):
        self._cluster = ClusterCoordinator(self) if distributed else None
```

**注意**: 这是本阶段风险最高的改动，因为需要修改 `Engine` 的类继承结构。需要确保：
1. `ClusterCoordinator` 持有 Engine 的引用（或需要的属性）
2. 所有 `self._cluster_state` 访问改为 `self._cluster.state`
3. `__init__` 和 `_init_cluster` 的调用链正确

#### 6.2.5 Phase 2 验证清单

- [ ] `from crawlo.core.engine import Engine` 仍可工作
- [ ] `from crawlo.core.config_factories import CrawloConfig` 仍可工作
- [ ] `from crawlo.core.task_scheduler import TaskScheduler` 仍可工作
- [ ] `from crawlo.network.request import Request` 仍可工作
- [ ] `from crawlo.queue.redis_stream_queue import RedisStreamQueue` 仍可工作
- [ ] `from crawlo.core.engine_cluster import ClusterMixin` 仍可工作（re-export）
- [ ] standalone 模式运行正常
- [ ] auto 模式运行正常（2 次验证 Redis 去重）
- [ ] distributed 模式运行正常
- [ ] 10 Worker 分布式测试种子锁正确（仅 1 个 Worker 生成 seed）
- [ ] `pytest tests/` 全部通过

---

### 6.3 Phase 3：生命周期收敛与降级

> **风险等级**: 高
> **影响范围**: 框架启动流程 + 通知系统
> **可独立提交**: 是（但需要在 Phase 2 之后）

#### 6.3.1 生命周期管理收敛

**操作**: 将 `framework.py`、`crawler_process.py`、`container.py`、`initialization/`、`factories/` 的核心逻辑收敛到 `core/application.py` + `crawler.py`。

**目标结构**:

```
crawlo/
├── crawler.py           # 合并: Crawler + CrawlerProcess + CrawloFramework
└── core/
    ├── application.py   # 合并: container + initialization + factories
    ├── ...
```

**文件映射**:

| 源文件 | 目标位置 | 说明 |
|--------|---------|------|
| `crawler.py` | `crawler.py`（保持文件名） | Crawler 核心控制器 |
| `crawler_process.py` | `crawler.py`（合并为 `CrawlerProcess` 类） | 进程管理器合入 |
| `framework.py` | `crawler.py`（合并为便捷函数） | Facade 模式的入口函数保留 |
| `container.py` | `core/application.py`（合并为 `DIContainer` 类） | 依赖注入容器 |
| `initialization/core.py` | `core/application.py`（合并为 `CoreInitializer` 类） | 核心初始化器 |
| `initialization/built_in.py` | `core/application.py`（合并为 `_register_built_in_components`） | 内置组件注册 |
| `initialization/context.py` | `core/application.py`（合并为 `ApplicationContext` 增强） | 应用上下文 |
| `initialization/phases.py` | `core/application.py`（合并为初始化阶段函数） | 分阶段初始化 |
| `initialization/registry.py` | `core/application.py`（合并为 `ComponentRegistry`） | 组件注册表 |
| `initialization/utils.py` | `core/application.py`（合并为辅助函数） | 初始化工具 |
| `factories/base.py` | `core/factories.py`（新文件） | 工厂基类 |
| `factories/crawler.py` | `core/factories.py`（合并） | Crawler 工厂 |
| `factories/registry.py` | `core/factories.py`（合并） | 工厂注册表 |
| `factories/utils.py` | `core/factories.py`（合并） | 工厂工具 |

**`crawler.py` 的目标结构**:
```python
class Crawler:
    """单爬虫控制器——引擎的拥有者和生命周期管理者"""
    ...

class CrawlerProcess:
    """多爬虫进程管理器——编排多个 Crawler 的并发执行"""
    ...

# 便捷函数（原 framework.py 的 Facade API）
def run_spider(spider_cls_or_name, **kwargs):
    """运行单个爬虫的便捷函数"""
    ...

def run_spiders(spider_classes_or_names, **kwargs):
    """运行多个爬虫的便捷函数"""
    ...

def create_crawler(spider_cls, **kwargs):
    """创建 Crawler 实例的便捷函数"""
    ...
```

**`core/application.py` 的目标结构**:
```python
class DIContainer:
    """依赖注入容器（原 container.py）"""
    ...

class ApplicationContext:
    """应用上下文——框架运行时的全局状态"""
    ...

class CoreInitializer:
    """核心初始化器（原 initialization/core.py）"""
    ...

class ComponentRegistry:
    """组件注册表（原 initialization/registry.py）"""
    ...

def initialize_framework(custom_settings=None):
    """框架初始化入口"""
    ...

def get_framework_initializer():
    """获取框架初始化器（lazy facade）"""
    ...
```

**兼容层**:
- `crawler_process.py`: re-export `CrawlerProcess` from `crawlo.crawler`
- `framework.py`: re-export 便捷函数 from `crawlo.crawler`
- `container.py`: re-export `DIContainer` from `crawlo.core.application`
- `initialization/__init__.py`: re-export `initialize_framework` 等 from `crawlo.core.application`
- `factories/__init__.py`: re-export from `crawlo.core.factories`

#### 6.3.2 `bot/` → `extensions/notifications/`

**操作**: 将 `bot/`（21 文件）降级为 `extensions/notifications/` 子包。

**文件映射**:

| 源目录 | 目标位置 |
|--------|---------|
| `bot/channels/` | `extensions/notifications/channels/` |
| `bot/core/` | `extensions/notifications/core/` |
| `bot/monitoring/` | `extensions/notifications/monitoring/` |
| `bot/templates/` | `extensions/notifications/templates/` |
| `bot/utils/` | `extensions/notifications/utils/` |

**兼容层** (`bot/__init__.py`): re-export from `crawlo.extensions.notifications`。

#### 6.3.3 `extension/` → `extensions/` + 重组

**操作**: 重命名 `extension/` 为 `extensions/`（复数对齐 Scrapy），同时将 `monitor/` 下的文件与外层的 `*_monitor.py` 统一。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `extension/memory_monitor.py` | `extensions/monitor/memory.py` |
| `extension/mysql_monitor.py` | `extensions/monitor/mysql.py` |
| `extension/redis_monitor.py` | `extensions/monitor/redis.py` |
| `extension/health_check.py` | `extensions/health_check.py` |
| `extension/log_stats.py` | `extensions/log_stats.py` |
| `extension/log_interval.py` | `extensions/log_interval.py` |
| `extension/logging_extension.py` | `extensions/logging.py` |
| `extension/request_recorder.py` | `extensions/request_recorder.py` |

#### 6.3.4 `pipelines/` → `pipeline/`（可选）

**操作**: 重命名为单数 `pipeline/`（对齐 Scrapy 的 `scrapy.pipelines`）。

> **注意**: Scrapy 实际用复数 `pipelines`。此处保持复数即可，不做重命名。仅在文档中标注"已对齐 Scrapy"。

#### 6.3.5 `mcp/` → 独立插件（可选）

**操作**: 将 `mcp/` 移出 `crawlo/` 核心包，作为独立插件 `crawlo-mcp` 发布。

**迁移方式**:
1. 将 `crawlo/mcp/` 移到 `plugins/crawlo-mcp/`
2. 在 `pyproject.toml` 中添加 `crawlo-mcp` 作为可选依赖
3. 更新 `crawlo/__init__.py` 移除 mcp 相关导入

#### 6.3.6 `scheduling/daemon/` → `commands/`

**操作**: 将 `scheduling/daemon/` 的调度逻辑合入 `commands/`。

**文件映射**:

| 源文件 | 目标位置 |
|--------|---------|
| `scheduling/daemon/scheduler.py` | `commands/scheduler.py` |
| `scheduling/daemon/cleanup.py` | `commands/cleanup.py` |
| `scheduling/job.py` | `commands/job.py` |
| `scheduling/registry.py` | `commands/registry.py` |
| `scheduling/trigger.py` | `commands/trigger.py` |

**保留** `scheduling/__init__.py` 作为兼容层 re-export。

#### 6.3.7 Phase 3 验证清单

- [ ] `from crawlo.crawler_process import CrawlerProcess` 仍可工作
- [ ] `from crawlo.framework import run_spider` 仍可工作
- [ ] `from crawlo.container import DIContainer` 仍可工作
- [ ] `from crawlo.initialization import initialize_framework` 仍可工作
- [ ] `from crawlo.factories import CrawlerComponentFactory` 仍可工作
- [ ] `from crawlo.bot.channels.feishu import FeishuChannel` 仍可工作
- [ ] `from crawlo.extension.memory_monitor import MemoryMonitor` 仍可工作
- [ ] standalone / auto / distributed 三种模式全部运行正常
- [ ] 10 Worker 分布式测试正常
- [ ] `pytest tests/` 全部通过
- [ ] `crawlo startproject` 创建的新项目结构正确

---

## 7. 目标结构总览

```
crawlo/                          # 15 个子包（从 27 个收敛）
├── __init__.py                  # public API（不变）
├── cli.py                       # CLI 入口（不变）
├── crawler.py                   # 合并: Crawler + CrawlerProcess + Facade API
├── event.py                     # 事件总线（不变）
├── project.py                   # 项目配置（不变）
├── constants.py                 # 常量（不变）
│
├── core/                        # 核心引擎（7 entries，从 20 收敛）
│   ├── __init__.py              # public API + lazy import
│   ├── application.py           # 合并: container + initialization + factories
│   ├── engine.py                # 引擎核心
│   ├── processor.py             # 处理器
│   ├── interfaces.py            # 接口定义
│   ├── singleton.py             # 单例模式
│   ├── errors.py                # 合并: error_types + exceptions + failure
│   ├── checkpoint_coordinator.py
│   ├── factories.py             # 合并: factories/ 5 files
│   ├── engine/                  # Engine 家族子包
│   │   ├── __init__.py
│   │   ├── generation.py
│   │   └── helpers.py
│   ├── config/                  # Config 家族子包
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── factories.py
│   │   ├── compat.py
│   │   └── validator.py
│   └── scheduling/              # Task 家族子包
│       ├── __init__.py
│       ├── task_manager.py
│       └── task_scheduler.py
│
├── http/                        # was network/ — Request/Response（对齐 Scrapy）
├── spider/                      # 爬虫基类（不变）
├── items/                       # 数据模型（不变）
├── downloader/                  # 下载器 + backends/ 子包
├── middleware/                  # 中间件（不变）
├── pipeline/                    # 数据管道（已有良好子包结构）
│   ├── dedup/
│   ├── doc/
│   ├── file/
│   └── sql/
├── queue/                       # 队列管理 + backends/ + backpressure/
│   ├── backends/
│   └── backpressure/
├── filters/                     # 去重过滤器（不变）
├── cluster/                     # 分布式集群（合并 engine_cluster 逻辑）
├── extensions/                  # was extension/ + bot/ → notifications/
│   ├── monitor/
│   └── notifications/
├── stats/                       # 统计（不变）
├── settings/                    # 配置（不变）
├── commands/                    # CLI 命令 + shell + scheduling
├── utils/                       # 合并 helpers + db，内部已有子包结构
│   ├── _compat/
│   ├── batch/
│   ├── concurrency/
│   ├── db/
│   ├── encoding/
│   ├── errors/
│   ├── parsing/
│   ├── redis/
│   ├── request/
│   ├── text/                    # 新: 合并 helpers/text_cleaner
│   └── adaptive_selector/       # 新: 合并 helpers/adaptive_selector
├── checkpoint/                  # 检查点（不变）
├── logging/                     # 日志（不变）
└── templates/                   # 模板（不变）
```

**删除的顶层包**（通过兼容层 re-export 保持向后兼容）:

| 包 | 去向 |
|----|------|
| `network/` | → `http/` |
| `helpers/` | → `utils/` |
| `db/` | → `utils/db/` |
| `backpressure/` | → `queue/backpressure/` |
| `initialization/` | → `core/application.py` |
| `factories/` | → `core/factories.py` |
| `bot/` | → `extensions/notifications/` |
| `shell/` | → `commands/shell.py` |
| `scheduling/` | → `commands/` + `core/scheduling/` |
| `framework.py` | → `crawler.py` |
| `crawler_process.py` | → `crawler.py` |
| `container.py` | → `core/application.py` |
| `mcp/` | → 独立插件（可选） |

---

## 8. 零破坏迁移策略

### 8.1 核心原则

所有迁移通过 **`__init__.py` re-export** 保持外部 import 路径不变：

```python
# 例: network/__init__.py 重命名为 http/__init__.py 后
# 在 network/__init__.py（保留为兼容层）中:
"""Deprecated: use crawlo.http instead."""
from crawlo.http.request import Request
from crawlo.http.response import Response
from crawlo.http.exceptions import *

import warnings
warnings.warn(
    "crawlo.network is deprecated, use crawlo.http",
    DeprecationWarning,
    stacklevel=2,
)
```

### 8.2 兼容层生命周期

| 阶段 | 兼容层状态 | 弃用警告 |
|------|-----------|---------|
| 重构后 v2.1 | 全部兼容层启用 | `DeprecationWarning` |
| v2.2 | 兼容层保留 | `PendingDeprecationWarning` |
| v3.0 | 删除兼容层 | - |

### 8.3 `__all__` 导出不变

`crawlo/__init__.py` 的 `__all__` 和 `__getattr__` 完全不变，用户代码中的 `from crawlo import Spider, Request, Response` 等无需修改。

---

## 9. 测试与验证

### 9.1 测试矩阵

每个 Phase 完成后需通过以下全部测试：

| 测试类别 | 测试内容 | 命令 |
|---------|---------|------|
| 单元测试 | `tests/unit/` 全部 | `pytest tests/unit/ -v` |
| 集成测试 | `tests/integration/` 全部 | `pytest tests/integration/ -v` |
| 架构测试 | `tests/arch/` 全部 | `pytest tests/arch/ -v` |
| Standalone 模式 | 单机运行 ofweek_standalone | `python examples/ofweek_standalone/run.py` |
| Auto 模式 ×2 | 自动检测运行 2 次 | 修改 config 后运行 2 次，验证 Redis 去重 |
| Distributed 模式 | 分布式运行 | `python examples/ofweek_distributed/run.py` |
| 10 Worker 分布式 | 10 节点协同 | `python examples/ofweek_distributed/run_10_workers.py` |
| 兼容性验证 | 旧 import 路径 | 编写脚本验证所有旧路径仍可 import |

### 9.2 兼容性验证脚本

```python
# scripts/verify_compat.py
"""验证所有旧 import 路径在重构后仍可用"""
OLD_IMPORTS = [
    "from crawlo.helpers.text_cleaner import TextCleaner",
    "from crawlo.helpers.time_utils import TimeUtils",
    "from crawlo.db.dialect import Dialect",
    "from crawlo.shell.core import Shell",
    "from crawlo.backpressure.strategies import QueueSizeStrategy",
    "from crawlo.core.engine_cluster import ClusterMixin",
    "from crawlo.core.engine_generation import EngineGeneration",
    "from crawlo.core.engine_helpers import EngineHelpers",
    "from crawlo.core.config_base import ConfigBase",
    "from crawlo.core.config_factories import CrawloConfig",
    "from crawlo.core.config_compat import ConfigCompat",
    "from crawlo.core.config_validator import ConfigValidator",
    "from crawlo.core.task_manager import TaskManager",
    "from crawlo.core.task_scheduler import TaskScheduler",
    "from crawlo.network.request import Request",
    "from crawlo.network.response import Response",
    "from crawlo.queue.redis_stream_queue import RedisStreamQueue",
    "from crawlo.queue.memory_queue import MemoryQueue",
    "from crawlo.crawler_process import CrawlerProcess",
    "from crawlo.framework import run_spider",
    "from crawlo.container import DIContainer",
    "from crawlo.initialization import initialize_framework",
    "from crawlo.factories import CrawlerComponentFactory",
    "from crawlo.bot.channels.feishu import FeishuChannel",
    "from crawlo.extension.memory_monitor import MemoryMonitor",
]

for stmt in OLD_IMPORTS:
    try:
        exec(stmt)
        print(f"  ✅ {stmt}")
    except Exception as e:
        print(f"  ❌ {stmt} -> {e}")
```

---

## 10. 风险评估

### 10.1 风险矩阵

| Phase | 风险等级 | 主要风险 | 缓解措施 |
|-------|---------|---------|---------|
| Phase 1 | 低 | 兼容层 re-export 遗漏 | 兼容性验证脚本 |
| Phase 2 | 中 | Engine 继承结构变更（Mixin → 组合） | 保留 Mixin 兼容层，渐进迁移 |
| Phase 3 | 高 | 生命周期合并导致启动顺序变化 | 逐步合并，每步运行全套测试 |

### 10.2 高风险点详细分析

#### 风险点 1: `ClusterMixin` → `ClusterCoordinator`（Phase 2.4）

**风险**: Engine 的类继承结构变更可能导致 `self._cluster_state`、`self._try_acquire_seed_lock_atomic` 等方法的 `self` 上下文丢失。

**缓解**: 
1. 第一版保留 `ClusterMixin` 作为兼容层，内部委托给 `ClusterCoordinator`
2. `ClusterCoordinator.__init__` 接收 Engine 引用
3. 逐步将 `self.xxx` 访问改为 `self._engine.xxx`

#### 风险点 2: 生命周期合并（Phase 3.1）

**风险**: `framework.py` → `crawler.py` 合并时，`CrawloFramework` 的初始化顺序（加载项目配置 → 初始化框架 → 创建 CrawlerProcess）可能被打乱。

**缓解**:
1. 先合并 `crawler_process.py` → `crawler.py`（最简单）
2. 再合并 `container.py` → `core/application.py`（中等）
3. 最后合并 `initialization/` → `core/application.py`（最复杂）
4. 每步后运行全套模式测试

#### 风险点 3: 循环依赖（全局）

**风险**: 大规模文件移动可能引入新的循环依赖。

**缓解**:
1. 每次移动后运行 `python -c "import crawlo"` 验证
2. 运行 `python -X importtime -c "import crawlo"` 检查 import 链
3. 保留所有 PEP 562 `__getattr__` 延迟导入机制

---

## 11. 时间线建议

| 阶段 | 内容 | 依赖 |
|------|------|------|
| Phase 1 | helpers→utils, db→utils/db, shell→commands, backpressure→queue | 无 |
| Phase 2 | core 拆子包, network→http, queue backends, engine_cluster→cluster | Phase 1 |
| Phase 3 | 生命周期收敛, bot→extensions, scheduling→commands, mcp 拆出 | Phase 2 |

---

## 附录 A：完整迁移对照表

| # | 操作 | 源 | 目标 | Phase |
|---|------|----|------|-------|
| 1 | 合并 | `helpers/text_cleaner.py` | `utils/text/cleaner.py` | 1 |
| 2 | 合并 | `helpers/time_utils.py` | `utils/time_utils.py` | 1 |
| 3 | 合并 | `helpers/mysql_exists_checker.py` | `utils/db/mysql_exists_checker.py` | 1 |
| 4 | 合并 | `helpers/file_downloader.py` | `utils/file_downloader.py` | 1 |
| 5 | 合并 | `helpers/adaptive_selector/` | `utils/adaptive_selector/` | 1 |
| 6 | 合并 | `db/dialect.py` | `utils/db/dialect.py` | 1 |
| 7 | 合并 | `db/pool_manager.py` | `utils/db/pool_manager.py` | 1 |
| 8 | 合并 | `shell/core.py` | `commands/shell.py` | 1 |
| 9 | 合并 | `backpressure/` (6 files) | `queue/backpressure/` | 1 |
| 10 | 合并 | `core/error_types.py` + `exceptions.py` + `failure.py` | `core/errors.py` | 2 |
| 11 | 移动 | `core/engine_generation.py` | `core/engine/generation.py` | 2 |
| 12 | 移动 | `core/engine_helpers.py` | `core/engine/helpers.py` | 2 |
| 13 | 移动 | `core/config.py` | `core/config/__init__.py` | 2 |
| 14 | 移动 | `core/config_base.py` | `core/config/base.py` | 2 |
| 15 | 移动 | `core/config_compat.py` | `core/config/compat.py` | 2 |
| 16 | 移动 | `core/config_factories.py` | `core/config/factories.py` | 2 |
| 17 | 移动 | `core/config_validator.py` | `core/config/validator.py` | 2 |
| 18 | 移动 | `core/task_manager.py` | `core/scheduling/task_manager.py` | 2 |
| 19 | 移动 | `core/task_scheduler.py` | `core/scheduling/task_scheduler.py` | 2 |
| 20 | 重命名 | `network/` | `http/` | 2 |
| 21 | 移动 | `queue/memory_queue.py` | `queue/backends/memory.py` | 2 |
| 22 | 移动 | `queue/disk_queue.py` | `queue/backends/disk.py` | 2 |
| 23 | 移动 | `queue/redis_priority_queue.py` | `queue/backends/redis_priority.py` | 2 |
| 24 | 移动 | `queue/redis_stream_queue.py` | `queue/backends/redis_stream.py` | 2 |
| 25 | 移动 | `core/engine_cluster.py` | `cluster/coordinator.py` | 2 |
| 26 | 合并 | `crawler_process.py` | `crawler.py` | 3 |
| 27 | 合并 | `framework.py` | `crawler.py` | 3 |
| 28 | 合并 | `container.py` | `core/application.py` | 3 |
| 29 | 合并 | `initialization/` (7 files) | `core/application.py` | 3 |
| 30 | 合并 | `factories/` (5 files) | `core/factories.py` | 3 |
| 31 | 降级 | `bot/` (21 files) | `extensions/notifications/` | 3 |
| 32 | 重命名 | `extension/` | `extensions/` | 3 |
| 33 | 移动 | `extension/*_monitor.py` | `extensions/monitor/` | 3 |
| 34 | 合并 | `scheduling/daemon/` | `commands/` | 3 |
| 35 | 移动 | `scheduling/*.py` | `commands/` | 3 |
| 36 | 拆出 | `mcp/` | 独立插件 | 3 (可选) |

---

## 附录 B：包间依赖关系图

### B.1 重构前（27 子包）

```
                        ┌──────────┐
                        │ logging  │  ← 最底层基础包
                        └────┬─────┘
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
        ┌─────────┐    ┌─────────┐    ┌──────────┐
        │  core   │    │  utils  │    │ settings │
        │ (20files)│   │ (39files)│   └──────────┘
        └────┬────┘    └────┬────┘
             │              │
    ┌────────┼────────┐    │
    ▼        ▼        ▼    │
┌──────┐ ┌──────┐ ┌──────┐│
│queue │ │down- │ │spider││
│(15f) │ │loader│ │ (6f) ││
└──┬───┘ │(13f) │ └──────┘│
   │     └──┬───┘         │
   │        ▼             │
   │   ┌──────────┐       │
   │   │middleware│       │
   │   │  (16f)   │       │
   │   └──────────┘       │
   │                      │
┌──┴───────┐  ┌───────────┴──┐  ┌──────────┐
│backpres- │  │   helpers    │  │  network │ ← 太薄
│sure(6f)  │  │   (9f)       │  │  (5f)    │
└──────────┘  └──────────────┘  └──────────┘

┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ cluster  │  │  bot     │  │  init    │  │ factories│
│ (10f)    │  │ (21f)    │  │ (7f)     │  │ (5f)     │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
    ↑ 生命周期管理散落 6 处 ↑                ↑
    
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│framework │  │crawler_  │  │container │  │   mcp    │
│  .py     │  │process.py│  │  .py     │  │ (3f)     │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### B.2 重构后（15 子包）

```
                        ┌──────────┐
                        │ logging  │
                        └────┬─────┘
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
        ┌─────────┐    ┌─────────┐    ┌──────────┐
        │  core   │    │  utils  │    │ settings │
        │ (7entries)│  │(25files)│    └──────────┘
        └────┬────┘    └────┬────┘
             │              │
    ┌────────┼────────┐    │
    ▼        ▼        ▼    │
┌──────┐ ┌──────┐ ┌──────┐│
│queue │ │down- │ │spider││
│+back │ │loader│ │      ││
│+backends│└──┬───┘ └──────┘│
└──────┘   │                 │
           ▼                 │
      ┌──────────┐           │
      │middleware│           │
      └──────────┘           │
                             │
┌──────────┐  ┌──────────────┴──┐  ┌──────────┐
│ cluster  │  │     http        │  │  items   │
│(+coord)  │  │  (was network)  │  └──────────┘
└──────────┘  └─────────────────┘
    
┌──────────┐  ┌──────────┐  ┌──────────┐
│extensions│  │ pipeline │  │ commands │
│+notific. │  │          │  │+shell    │
│+monitor  │  │          │  │+scheduling│
└──────────┘  └──────────┘  └──────────┘

┌──────────┐  ┌──────────┐  ┌──────────┐
│ filters  │  │  stats   │  │checkpoint│
└──────────┘  └──────────┘  └──────────┘
```

---

## 附录 C：命名规范约定

对齐 Scrapy 的命名规范：

| 概念 | Scrapy | Crawlo（现状） | Crawlo（目标） |
|------|--------|---------------|---------------|
| Request/Response 包 | `scrapy.http` | `crawlo.network` | `crawlo.http` |
| 管道包 | `scrapy.pipelines` | `crawlo.pipelines` | `crawlo.pipelines`（保持） |
| 扩展包 | `scrapy.extensions` | `crawlo.extension` | `crawlo.extensions` |
| 引擎 | `scrapy.engine` | `crawlo.core.engine` | `crawlo.core.engine`（保持） |
| Crawler+Process | `scrapy.crawler` | 6 处分散 | `crawlo.crawler`（1 处） |
| CLI 入口 | `scrapy.cmdline` | `crawlo.cli` | `crawlo.cli`（保持） |

---

*本文档将随重构进展持续更新。*
