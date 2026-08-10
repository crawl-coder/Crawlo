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
| `crawlo.bot`（含 channels/core/monitoring/templates/utils 子包） | `crawlo.extensions.notifications.*` | 1.7.x | ≥ 2.0 | sys.modules 重定向 + DeprecationWarning |
| `crawlo.crawler_process` | `crawlo.crawler.CrawlerProcess` | 1.7.x | ≥ 2.0 | sys.modules 重定向 |
| `crawlo.framework` | `crawlo.crawler.CrawloFramework` | 1.7.x | ≥ 2.0 | sys.modules 重定向 |
| `crawlo.container` | `crawlo.core.application.ApplicationContext` | 1.7.x | ≥ 2.0 | sys.modules 重定向 |
| `crawlo/crawler.py` 扁平模块 | `crawlo.crawler` 子包 | 1.7.x | ≥ 1.9 | re-export + DeprecationWarning |

## 历史移除记录

| 符号 | 移除版本 | 替代方案 | 备注 |
|---|---|---|---|
| （暂无） | — | — | 1.0 之前不新增移除项 |

## 评审待办（1.0 前）

以下符号在 api-surface.md 中标注 `experimental` 或 `internal`，1.0 前需逐项决定：转 frozen / 转 internal / 走 deprecation：

- `crawlo.core.component_base` / `component_registry` / `factories` / `interfaces`（组件基类层）
- `crawlo.core.scheduling.TaskManager`（定时任务，v0.x 演进中）
- `crawlo.utils._compat.*`（Python 版本兼容层）
- `crawlo.downloader.stealth_scripts.*`（内部脚本资源）

## 强制规则（P0-A2 验收）

- [ ] CI 增加 `pytest -W error::DeprecationWarning`（仅 crawlo 命名空间）全量通过；
- [ ] 上述"进行中"条目全部有测试守护（import 路径 + 警告行为）；
- [ ] 本文件不允许出现"过期条目"（移除版本已过但仍未移除）。
