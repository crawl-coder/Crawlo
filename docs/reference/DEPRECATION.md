# Crawlo Deprecation 周期记录

> 规则：任何公开符号的移除，必须满足
> ① 已宣布 deprecation（本文档 + DeprecationWarning）；
> ② 宣布后至少经过 **2 个 minor 版本**；
> ③ 测试中无未预期的 DeprecationWarning。
>
> 当前版本：**1.7.3**（2026-08-10 盘点基线）。
> 权威符号清单见 [api-surface.md](api-surface.md)。

## 进行中的 deprecation（移除日期未到）

| 旧路径/符号 | 新路径/符号 | 宣布版本 | 计划移除版本 | 现状 |
|---|---|---|---|---|
| `crawlo.crawler_process` | `crawlo.crawler.CrawlerProcess` | 1.7.x | ≥ 2.0 | sys.modules 重定向 |
| `crawlo.framework` | `crawlo.crawler.CrawloFramework` | 1.7.x | ≥ 2.0 | sys.modules 重定向 |
| `crawlo.container` | `crawlo.core.application.ApplicationContext` | 1.7.x | ≥ 2.0 | sys.modules 重定向 |
| `crawlo/crawler.py` 扁平模块 | `crawlo.crawler` 子包 | 1.7.x | ≥ 1.9 | re-export + DeprecationWarning |

### 2026-08-10 修复：bot shim 子模块身份一致性

> **2026-08-10 后续**：`crawlo.bot` 已在 1.7.4 提前移除（项目决策），本节历史留档。

当时发现并修复旧路径子模块导入产生重复类对象的问题：

- **问题**：`from crawlo.bot.utils.deduplicator import MessageDeduplicator` 与
  `from crawlo.extensions.notifications.utils.deduplicator import MessageDeduplicator`
  不是同一个类（`isinstance` 静默失效）。
- **根因**：父包 `sys.modules` alias 后，子模块导入走父包 `__path__` 路径查找，
  重新执行源文件产生第二份类对象。
- **修复**：`crawlo/bot/__init__.py` 保持真实包身份，walk 新包全部子模块并
  预注册到旧路径 `sys.modules`；子包/符号经 `__getattr__` 转发。
- **守护**：`tests/arch/test_deprecation_shims.py::test_bot_submodule_identity`。

## 历史移除记录

| 符号 | 移除版本 | 替代方案 | 备注 |
|---|---|---|---|
| `crawlo.bot`（含 channels/core/monitoring/templates/utils 子包） | **1.7.4（提前）** | `crawlo.extensions.notifications.*` | 项目决策：不再等待 v2.0，直接移除。属刻意 breaking change，所有旧路径导入将抛 ModuleNotFoundError |

## 评审待办（1.0 前）

以下符号在 api-surface.md 中标注 `experimental` 或 `internal`，1.0 前需逐项决定：转 frozen / 转 internal / 走 deprecation：

- `crawlo.core.component_base` / `component_registry` / `factories` / `interfaces`（组件基类层）
- `crawlo.core.scheduling.TaskManager`（定时任务，v0.x 演进中）
- `crawlo.utils._compat.*`（Python 版本兼容层）
- `crawlo.downloader.stealth_scripts.*`（内部脚本资源）

## 强制规则（P0-A2 验收）

- [x] `pyproject.toml` 增加 `filterwarnings = ["error::DeprecationWarning"]`（全量生效）；
- [x] 上述"进行中"条目全部有测试守护（`tests/arch/test_deprecation_shims.py`：警告 + 对象身份）；
- [x] 框架内部 40+ 处旧路径引用迁移到新路径（container→core.application、crawler_process→crawler）；
- [x] 全量测试（2491 passed）在全局 DeprecationWarning=error 下通过；
- [x] 顺带修复：redis-py 5.x `close()`→`aclose()` 废弃迁移（stream/priority/filter/pool/cluster/pipeline 共 6 处）；
- [ ] 本文件不允许出现"过期条目"（移除版本已过但仍未移除）。
