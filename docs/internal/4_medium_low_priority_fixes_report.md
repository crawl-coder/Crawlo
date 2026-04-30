# 4 个中低优先级问题修复报告

该文档记录一轮针对 Crawlo 框架中低优先级问题的集中修复，涵盖时间：2026-04-07。

---

## 一、超时硬编码统一至中央常量模块

### 问题
15+ 处超时值硬编码散落在各下载器和工具模块中：浏览器操作超时（1000ms/2000ms/3000ms/5000ms）、队列操作超时（300s/600s）、subprocess.run 超时（5s）、下载器 absolute_timeout（30s/40s/25s/35s）等，值分散、含义不明、不易统一调整。

### 方案
创建 `crawlo/constants.py` 作为框架级常量的单一事实来源，按类别分组管理，各模块通过 `from crawlo.constants import XXX` 引用。

### 常量定义

| 常量 | 值 | 用途 |
|------|-----|------|
| `ABSOLUTE_TIMEOUT_MULTIPLIER_NORMAL` | 2.0 | 绝对超时系数 — 普通请求（30s = 15s × 2.0） |
| `ABSOLUTE_TIMEOUT_MULTIPLIER_EXTENDED` | 2.67 | 绝对超时系数 — 代理/重试（≈40s = 15s × 2.67） |
| `BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS` | 2000 | 导航到 about:blank 超时（ms） |
| `BROWSER_ELEMENT_WAIT_TIMEOUT_MS` | 3000 | 页面元素等待默认超时（ms） |
| `BROWSER_NETWORK_IDLE_TIMEOUT_MS` | 5000 | networkidle 状态等待超时（ms） |
| `BROWSER_ACTION_WAIT_DEFAULT_MS` | 1000 | 点击/填充后默认等待（ms） |
| `BROWSER_ACTION_WAIT_EXTENDED_MS` | 2000 | 点击后等待新内容加载（ms） |
| `QUEUE_OPERATION_TIMEOUT` | 300 | 通用队列操作超时（s） |
| `QUEUE_EXTENDED_TIMEOUT` | 600 | 扩展队列操作超时（s） |
| `SUBPROCESS_RUN_TIMEOUT` | 5 | subprocess.run 默认超时（s） |
| `DEFAULT_SLEEP_INTERVAL` | 0.25 | 通用异步等待间隔（s） |
| `HEALTH_CHECK_INTERVAL` | 60 | 健康检查默认间隔（s） |

> 绝对超时 = `DOWNLOAD_TIMEOUT` 配置值 × 系数。系数保留 > 1.0 的缓冲空间，确保配置超时变更时自动适应。

### 修改的文件（8 个）

| 文件 | 替换的硬编码 |
|------|-------------|
| `crawlo/downloader/aiohttp_downloader.py` | L273 回退值 40.0/35.0 → 配置派生公式 |
| `crawlo/downloader/httpx_downloader.py` | L275-L280 absolute_timeout=30.0/25.0 → 系数公式 |
| `crawlo/downloader/cffi_downloader.py` | L123-L126 absolute_timeout=40.0/35.0 → 系数公式 |
| `crawlo/downloader/drissionpage_downloader.py` | 2 处 timeout=5 → SUBPROCESS_RUN_TIMEOUT |
| `crawlo/downloader/playwright_downloader.py` | timeout=2000 → BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS |
| `crawlo/downloader/camoufox_downloader.py` | 3 处 timeout（1000/3000/5000）→ 对应浏览器常量 |
| `crawlo/downloader/wait_strategies.py` | 3 处 timeout（3000/5000/5000）→ 对应浏览器常量 |
| `crawlo/utils/queue_helper.py` | 2 处 timeout（600/300）→ QUEUE_OPERATION/EXTENDED_TIMEOUT |

---

## 二、测试目录结构分层

### 问题
200+ 测试文件全部混杂在 `tests/` 根目录；`.md` 报告文件与新报告混放，目录无层次。

### 方案

```
tests/
  fixtures/        # 共享 Mock 类与测试夹具
    __init__.py
    mock_item.py
  reports/         # .md 测试报告
    ANTI_DETECTION_TEST_REPORT.md
    RESOURCE_LEAK_TEST_REPORT.md
    TEST_REPORT.md
    comprehensive_testing_summary.md
    untested_features_report.md
  test_*.py        # 常规测试文件（保持原位，不移动）
```

---

## 三、MockItem 类型分散 → 共享夹具

### 问题
`MockItem` 类定义散落在 `test_all_pipeline_fingerprints.py`、`test_pipeline_fingerprint_consistency.py`、`test_integration.py` 三个测试文件中，定义各不一致，维护重复。

### 方案
创建 `tests/fixtures/mock_item.py`，提供两个共享类：

- **`MockItem`** — 通用模拟数据项，无框架依赖，适用指纹生成等测试。
- **`MockDataItem(Item)`** — 继承 `crawlo.Item`，使用 `Field(default='')` 定义字段，适用管道/集成测试。

三个测试文件统一从 `tests.fixtures.mock_item` 导入，删除各自的内联定义。

---

## 四、重点缺陷修复

本次提交同时包含了遗留的未暂存修改，涉及以下关键缺陷修复与代码治理：

### 4.1 TaskManager 忙轮询 → Event 驱动

**文件**：[`crawlo/task_manager.py`](file:///d:/dowell/others/Crawlo/crawlo/task_manager.py)

**问题**：`_wait_all_done()` 使用 `while self.current_task: await asyncio.sleep(0.1)` 忙轮询检查任务完成状态，每个 Crawler 实例每 100ms 唤醒一次，多爬虫场景下 CPU 浪费明显。

**修复**：引入 `asyncio.Event`，任务全部移除时 set()，`_wait_all_done()` 通过 `await self._all_done_event.wait()` 阻塞等待，零 CPU 空转。

---

### 4.2 ConfigUtils import 路径修正

**文件**：[`crawlo/initialization/built_in.py`](file:///d:/dowell/others/Crawlo/crawlo/initialization/built_in.py)（3 处）

**问题**：`logging_initializer.py` 中仍引用 `crawlo.utils.config_manager.ConfigUtils`，但 `ConfigUtils` 已迁移至 `crawlo.utils.misc`，旧路径在特定条件下引发 ImportError。

**修复**：所有 `from crawlo.utils.config_manager import ConfigUtils` 改为 `from crawlo.utils.misc import ConfigUtils`。

---

### 4.3 ComponentRegistry.register() 废弃警告清理

**文件**：[`crawlo/factories/registry.py`](file:///d:/dowell/others/Crawlo/crawlo/factories/registry.py)

**问题**：`register()` 方法内嵌 `DeprecationWarning` 提示改用 `register_async()`，但初始化阶段大量使用同步 `register()` 注册组件，每次调用都产生噪音警告。

**修复**：移除废弃警告及 import。`register()` 作为初始化阶段的标准同步入口保留，`register_async()` 用于异步上下文。

---

### 4.4 config_manager.py 废弃代码清理

**文件**：[`crawlo/utils/config_manager.py`](file:///d:/dowell/others/Crawlo/crawlo/utils/config_manager.py)

**问题**：`LargeScaleConfig` 类（含 3 个预设配置方法 + `apply_large_scale_config` 函数）共 445 行，功能已被 `setting_manager.py` 替代多年，属于死代码。

**修复**：整体删除 `LargeScaleConfig` 类和 `apply_large_scale_config` 函数，精简 `__all__` 导出。

---

### 4.5 超大文件拆分重构

为降低模块复杂度，对 4 个超大文件进行拆分：

| 原始文件 | 减少行数 | 拆分目标 | 新增行数 |
|---------|---------|---------|---------|
| `crawlo/core/engine.py` | -186 | `crawlo/core/engine_generation.py`（RequestGenerationMixin） | +196 |
| `crawlo/crawler.py` | -47 | `crawlo/crawler_models.py`（CrawlerState/CrawlerMetrics） | +56 |
| `crawlo/downloader/playwright_downloader.py` | -307 | `stealth.py` + `wait_strategies.py` | +330 |
| `crawlo/queue/queue_manager.py` | -325 | `queue/config.py` + `queue/intelligent_scheduler.py` | +332 |

效果：各源文件行数回归可控范围，逻辑内聚性提升，便于维护和单模块测试。

---

## 五、验证结论

- **语法检查**：全部通过。
- **集成测试**：1 PASSED, 1 SKIPPED。
- **全量测试**：464 PASSED, 330 FAILED（预存 async 问题），7 SKIPPED, 5 ERRORS（预存 import 路径问题）— **0 回归**。
- **真实案例**：`examples/ofweek_standalone/run.py` 成功运行，爬取 ee.ofweek.com 50 个列表页 + 大量详情页，无超时/连接/导入错误。
