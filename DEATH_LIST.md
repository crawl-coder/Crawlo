# Crawlo v2.0 删除清单（DEATH_LIST）

> 生效版本：**v2.0**（Phase 10 执行，不再保留任何兼容层）
> 维护时期：v1.x（当前 Phase 9.x）中，旧路径访问将统一触发 `DeprecationWarning`。
> 适用范围：所有 `crawlo/<顶层 facade>.py` 单文件入口、以及 Phase 9 中为维持向后兼容而保留的旧符号名。

---

## 1. 将被物理删除的文件

| # | 文件路径                               | 删除原因                                                                     | v1.x 兼容层类型 |
|---|----------------------------------------|------------------------------------------------------------------------------|-----------------|
| 1 | `crawlo/exceptions.py`                 | 顶层异常 facade（PEP 562 懒加载），已按领域拆分到 5 个子模块                 | PEP 562 `__getattr__` 懒加载 + `DeprecationWarning` |
| 2 | `crawlo/interfaces.py`                 | 顶层接口 facade（直接 re-export），已按领域拆分到 9 个子模块                 | 直接 re-export + 模块级 `DeprecationWarning` |
| 3 | `crawlo/config.py`                     | 顶层配置中心入口（`CrawloConfig` + 兼容常量/函数），已拆分到 `core/config_*` 4 个子模块 | `CrawloConfig` 实类驻留 + PEP 562 懒加载常量/函数 |
| 4 | `crawlo/core/scheduler.py`             | 顶层/旧调度器入口文件，核心调度逻辑已迁移至 `crawlo.scheduling` 包           | 重导出 + 警告 |
| 5 | `crawlo/utils/singleton.py`            | 旧单例工具，已迁移至 `crawlo.logging.manager`（或对应子模块内实现）          | 重导出 + 警告 |
| 6 | `crawlo/utils/request/request_utils.py`  等 utils 下已拆分的旧路径           | utils 按功能拆分后保留的顶层旧文件；具体列表见项目 `pyproject.toml` 注释   | 函数体延迟/重导出 + 警告 |

> 注：删除前需先运行一次 `grep -rE "from crawlo\.(exceptions|interfaces|config)\b" <外部代码仓库>` 确认外部用户是否已迁移。

---

## 2. 具体符号迁移指引

### 2.1 `crawlo.exceptions` → 领域子模块 exceptions

| 子模块（新路径）                       | 应迁移的符号                                                                                                                                                                                                                         |
|----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `crawlo.core.exceptions`               | `CrawloException`, `ComponentInitException`, `MiddlewareInitError`, `PipelineInitError`, `ExtensionInitError`, `ConfigException`, `NotConfigured`, `NotConfiguredError`, `ConfigValidationError`, `TransformTypeError`, `ReceiverTypeError`, `ScheduleException`, `OutputException`, `OutputError`, `InvalidOutputError`, `DetailedException`, `ErrorContext` |
| `crawlo.network.exceptions`            | `RequestException`, `RequestMethodError`, `IgnoreRequestError`, `DecodeError`, `DownloadError`, `RetryError`                                                                                                                          |
| `crawlo.spider.exceptions`             | `SpiderException`, `SpiderTypeError`, `SpiderCreationError`, `AmbiguousSpiderError`, `SpiderNameConflictWarning`                                                                                                                     |
| `crawlo.items.exceptions`              | `DataException`, `ItemInitError`, `ItemAttributeError`, `ItemValidationError`, `ItemDiscard`, `DropItem`                                                                                                                             |
| `crawlo.queue.exceptions`              | `QueueFullError`, `QueueFullTimeout`, `QueueEmptyError`, `QueueClosedError`                                                                                                                                                          |

迁移例：
```python
# ❌ v1.x 旧写法（会有 DeprecationWarning，v2.0 直接 ImportError）
from crawlo.exceptions import ItemDiscard, ScheduleException

# ✅ v2.0 新写法
from crawlo.items.exceptions import ItemDiscard
from crawlo.core.exceptions import ScheduleException
```

---

### 2.2 `crawlo.interfaces` → 领域子模块 interfaces

| 子模块（新路径）                       | 应迁移的符号             | 备注                                                                             |
|----------------------------------------|--------------------------|----------------------------------------------------------------------------------|
| `crawlo.core.interfaces`               | `IScheduler`             | 调度器接口（ABC / Protocol 同名保留）                                            |
| `crawlo.spider.interfaces`             | `ISpiderLoader`          | Spider 加载器接口                                                                |
| `crawlo.downloader.interfaces`         | `IDownloader`            | 下载器接口                                                                       |
| `crawlo.pipelines.interfaces`          | `IPipeline`              | 管道接口                                                                         |
| `crawlo.filters.interfaces`            | `IFilter`                | 请求去重过滤器接口                                                               |
| `crawlo.extension.interfaces`          | `IExtension`             | 扩展接口                                                                         |
| `crawlo.queue.interfaces`              | `IRequestQueue`, `IQueue`| **⚠️ 别名变化**：旧接口名为 `IQueue`（Protocol 版），新包对外推荐用 `IRequestQueue`（原名 ABC 版 `IQueue` 也在同目录保留，需按使用的是 ABC/Protocol 显式引入） |
| `crawlo.stats.interfaces`              | `IStatsCollector`        | 统计采集器接口                                                                   |
| `crawlo.middleware.interfaces`         | `IMiddleware`            | 中间件接口                                                                       |

迁移例：
```python
# ❌ v1.x
from crawlo.interfaces import IQueue, IPipeline

# ✅ v2.0
from crawlo.queue.interfaces import IRequestQueue   # 原 Protocol 版 IQueue
from crawlo.pipelines.interfaces import IPipeline
```

---

### 2.3 `crawlo.config` → `crawlo.core.config_*` 系列

- **核心类 `CrawloConfig`**（`CrawloConfig.standalone / .distributed / .auto / .from_env / .set / .enable_debug / .to_dict / .validate`）：
  - **v2.0 路径**：`from crawlo.core.config import CrawloConfig`
  - （`config.py` 目前同时是一个 facade 类，但未来会迁移到 `crawlo.core.config.CrawloConfig`，类 API 不变。）

- **常量**：
  | 旧路径                    | 新路径（直接从子模块 import）             |
  |---------------------------|--------------------------------------------|
  | `crawlo.config.RunMode`   | `from crawlo.core.config_base import RunMode` |
  | `crawlo.config.BASE_CONFIG`   | `from crawlo.core.config_base import BASE_CONFIG` |
  | `crawlo.config.MODE_CONFIG_MAP` | `from crawlo.core.config_base import MODE_CONFIG_MAP` |
  | `crawlo.config.ConfigValidator` | `from crawlo.core.config_validator import ConfigValidator` |

- **兼容函数（v1.x 已在 `config_compat.py` 中，v2.0 直接停用）**：
  | 旧路径                                   | v2.0 新写法（改用 `CrawloConfig` 面向对象 API） |
  |------------------------------------------|-------------------------------------------------|
  | `from crawlo.config import create_config`| `CrawloConfig.auto(**kwargs)` / `CrawloConfig.standalone(...)` 等 |
  | `from crawlo.config import validate_config`  | `CrawloConfig(settings).validate()`          |
  | `from crawlo.config import standalone_mode`  | `CrawloConfig.standalone(...).to_dict()`     |
  | `from crawlo.config import distributed_mode` | `CrawloConfig.distributed(...).to_dict()`    |
  | `from crawlo.config import auto_mode`        | `CrawloConfig.auto(...).to_dict()`           |
  | `from crawlo.config import from_env`         | `CrawloConfig.from_env().to_dict()`          |

---

### 2.4 `crawlo.core.scheduler` → `crawlo.scheduling`

| 旧路径（示例）                             | 新路径（以实际 Phase 9.1/9.2 拆分结果为准）                          |
|--------------------------------------------|-----------------------------------------------------------------------|
| `from crawlo.core.scheduler import Scheduler` | `from crawlo.scheduling.scheduler import Scheduler`                  |
| `from crawlo.core.scheduler import <具体子组件>` | `from crawlo.scheduling.<子模块> import <符号>`                    |

---

### 2.5 `crawlo.utils.singleton` / utils 旧路径

| 旧路径（示例）                             | 新路径                                                            |
|--------------------------------------------|-------------------------------------------------------------------|
| `from crawlo.utils.singleton import Singleton` / `get_singleton` | 对应子模块内置的实现（Phase 9.4 已替换，见各子模块实际 import） |
| 其他 utils 顶层别名                        | `crawlo.utils.<细分子包> import <符号>`                           |

---

## 3. 附带变更：`pyproject.toml` ignore_imports 同步清理

在 v2.0 删除上述 facade 后，`pyproject.toml` 下 `tool.linter.ignore_imports` 中以下条目需一并移除（Phase 9.5 注释中标注了 `v2.0 删除 … 后一并删除` 的所有条目）：

- `crawlo.config -> crawlo.core.config_factories`
- `crawlo.config -> crawlo.core.config_validator`
- `crawlo.interfaces -> crawlo.*`（若仍有残留）
- 其他因顶层 facade 间接链而加入的「异常共享」条目（在 v2.0 重新评估是否保留：`crawlo.*.exceptions -> crawlo.core.exceptions` 系列）

---

## 4. v2.0 前的自动检查脚本（建议在 CI 中启用）

在 v1.x 期间，可使用以下脚本扫描仓库中是否仍存在「即将被移除」的旧路径引用：

```bash
# 扫描当前仓库所有 import 语句
grep -rnE "from crawlo\.(exceptions|interfaces|config)\b|import crawlo\.(exceptions|interfaces|config)\b" \
    crawlo tests docs examples \
  | grep -v "crawlo/(exceptions|interfaces|config)\.py:"        # 忽略 facade 文件自身
  | grep -v "if TYPE_CHECKING:"                                 # 仅类型注解可酌情放宽
```

若扫描结果为 0，则表示内部代码已完全脱离旧路径，v2.0 可以「无痛」切换。
