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

## 四、验证结论

- **语法检查**：全部通过。
- **集成测试**：1 PASSED, 1 SKIPPED。
- **全量测试**：464 PASSED, 330 FAILED（预存 async 问题），7 SKIPPED, 5 ERRORS（预存 import 路径问题）— **0 回归**。
- **真实案例**：`examples/ofweek_standalone/run.py` 成功运行，爬取 ee.ofweek.com 50 个列表页 + 大量详情页，无超时/连接/导入错误。
