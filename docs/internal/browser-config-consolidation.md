# 浏览器下载器配置参数整合开发文档

> 版本：v1.1  
> 日期：2026-05-12  
> 状态：已实现

---

## 一、背景与目标

### 1.1 现状问题

Crawlo 框架目前有 4 个浏览器下载器：Playwright、Camoufox、CloakBrowser、DrissionPage。每个下载器拥有独立前缀的配置参数，导致：

- **大量重复**：约 30+ 个参数语义相同、默认值相同，但前缀不同
- **配置冗余**：用户切换下载器时需重新配置一套几乎相同的参数
- **维护负担**：修改共同逻辑时需同步修改 4 处
- **认知成本**：新用户需理解 4 套前缀命名规则

### 1.2 整合目标

1. 新增 `BROWSER_*` 通用配置层，覆盖 4 个浏览器下载器的共同参数
2. 保留各下载器特有前缀参数，用于覆盖通用配置
3. 100% 向后兼容，旧配置继续生效
4. 降低新用户配置复杂度

---

## 二、参数分类与对照

### 2.1 可整合参数（15 个）

以下参数在 3~4 个浏览器下载器中语义相同、默认值相同或近似：

| # | 语义 | 建议统一名 | 默认值 | Playwright | Camoufox | CloakBrowser | DrissionPage |
|---|------|-----------|--------|-----------|----------|--------------|-------------|
| 1 | 无头模式 | `BROWSER_HEADLESS` | `True` | ✅ `PLAYWRIGHT_HEADLESS` | ✅ `CAMOUFOX_HEADLESS` | ✅ `CLOAKBROWSER_HEADLESS` | ✅ `DRISSIONPAGE_HEADLESS` |
| 2 | 超时时间 | `BROWSER_TIMEOUT` | `30000` (ms) | ✅ 30000ms | ✅ 30000ms | ✅ 30000ms | ⚠️ `DRISSIONPAGE_TIMEOUT`=30s |
| 3 | 加载超时 | `BROWSER_LOAD_TIMEOUT` | `10000` (ms) | ✅ `PLAYWRIGHT_LOAD_TIMEOUT` | ✅ `CAMOUFOX_LOAD_TIMEOUT` | ✅ `CLOAKBROWSER_LOAD_TIMEOUT` | ❌ 无此配置 |
| 4 | 视口宽度 | `BROWSER_VIEWPORT_WIDTH` | `1280` | ✅ | ✅ | ✅ | ❌ 无此配置 |
| 5 | 视口高度 | `BROWSER_VIEWPORT_HEIGHT` | `720` | ✅ | ✅ | ✅ | ❌ 无此配置 |
| 6 | 最大页面数 | `BROWSER_MAX_PAGES` | `10` | ✅ `MAX_PAGES_PER_BROWSER` | ✅ `MAX_PAGES` | ✅ `MAX_PAGES` | ✅ `MAX_PAGES` |
| 7 | 代理设置 | `BROWSER_PROXY` | `None` | ✅ | ✅ | ✅ | ✅ |
| 8 | 屏蔽资源 | `BROWSER_BLOCK_RESOURCES` | `["image","font","media"]` | ✅ | ✅ | ✅ | ❌ 无此配置 |
| 9 | 自动滚动 | `BROWSER_AUTO_SCROLL` | `False` | ✅ | ✅ | ✅ | ✅ |
| 10 | 滚动延迟 | `BROWSER_SCROLL_DELAY` | `500` (ms) | ✅ 500ms | ✅ 500ms | ✅ 500ms | ⚠️ `DRISSIONPAGE_SCROLL_DELAY`=1s |
| 11 | 等待策略 | `BROWSER_WAIT_STRATEGY` | `"auto"` | ✅ | ✅ | ✅ | ❌ 无此配置 |
| 12 | 等待超时 | `BROWSER_WAIT_TIMEOUT` | `10000` (ms) | ✅ | ✅ | ✅ | ❌ 无此配置 |
| 13 | 等待元素 | `BROWSER_WAIT_FOR_ELEMENT` | `None` | ✅ | ✅ | ✅ | ❌ 无此配置 |
| 14 | 反检测级别 | `BROWSER_STEALTH_LEVEL` | `"basic"` | ✅ | ❌（内置） | ❌（内置） | ✅ |
| 15 | 拟人化行为 | `BROWSER_HUMANIZE` | `False` | ❌ 无此配置 | ✅ `True` | ✅ `False` | ❌ 无此配置 |

> ⚠️ 表示默认值或单位不同，整合时需统一处理。

### 2.2 单位不一致问题

| 参数 | Playwright / Camoufox / CloakBrowser | DrissionPage | 整合方案 |
|------|--------------------------------------|-------------|---------|
| 超时时间 | 毫秒（30000） | 秒（30） | 统一为毫秒，DrissionPage 内部转换 |
| 滚动延迟 | 毫秒（500） | 秒（1） | 统一为毫秒，DrissionPage 内部转换 |

### 2.3 默认值不一致问题

| 参数 | Camoufox | CloakBrowser | 整合方案 |
|------|----------|-------------|---------|
| `BROWSER_HUMANIZE` | `True` | `False` | 统一为 `False`，Camoufox 用户需显式开启 |

### 2.4 不可整合参数（各下载器特有）

| 下载器 | 特有参数 | 说明 |
|--------|---------|------|
| **Playwright** | `PLAYWRIGHT_BROWSER_TYPE`, `PLAYWRIGHT_SINGLE_BROWSER_MODE`, `PLAYWRIGHT_BLOCK_ADS`, `PLAYWRIGHT_BLOCK_WEBRTC`, `PLAYWRIGHT_HIDE_CANVAS`, `PLAYWRIGHT_ALLOW_WEBGL`, `PLAYWRIGHT_REAL_CHROME`, `PLAYWRIGHT_GOOGLE_REFERER`, `PLAYWRIGHT_IGNORE_HTTPS_ERRORS` | Chromium 级细粒度控制 |
| **DrissionPage** | `DRISSIONPAGE_BROWSER_PATH`, `DRISSIONPAGE_USER_DATA_PATH`, `DRISSIONPAGE_LOAD_IMAGES` | DrissionPage 特有的浏览器管理方式 |
| **Camoufox** | `CAMOUFOX_SOLVE_CLOUDFLARE` | Camoufox 核心能力，自动解决 Cloudflare Turnstile |
| **CloakBrowser** | `CLOAKBROWSER_HUMAN_PRESET`, `CLOAKBROWSER_HUMAN_CONFIG`, `CLOAKBROWSER_GEOIP`, `CLOAKBROWSER_TIMEZONE`, `CLOAKBROWSER_LOCALE`, `CLOAKBROWSER_BACKEND`, `CLOAKBROWSER_STEALTH_ARGS`, `CLOAKBROWSER_FINGERPRINT`, `CLOAKBROWSER_FINGERPRINT_PLATFORM`, `CLOAKBROWSER_ARGS`, `CLOAKBROWSER_PERSISTENT_CONTEXT`, `CLOAKBROWSER_USER_DATA_DIR` | CloakBrowser 独有的指纹体系和持久化方案 |

---

## 三、整合方案设计

### 3.1 配置层级（三级优先级）

```
下载器特有配置（最高优先级）
    ↓ 未设置时回退
浏览器通用配置（BROWSER_*）
    ↓ 未设置时回退
硬编码默认值（最低优先级）
```

读取逻辑：

```python
# 工具函数：优先读取下载器特有配置，回退到 BROWSER_* 通用配置
# 位置：crawlo/utils/misc.py

def get_browser_config(settings, prefix: str, key: str, default: Any = None) -> Any:
    """
    三级优先级读取浏览器配置：
    1. {PREFIX}_{KEY}  如 PLAYWRIGHT_HEADLESS（用户显式覆盖）
    2. BROWSER_{KEY}   如 BROWSER_HEADLESS（浏览器通用配置）
    3. default（硬编码默认值）
    
    前提：{PREFIX}_{KEY} 必须从 default_settings.py 中删除，
    否则 SettingManager.get() 永远返回默认值，永不回退到 BROWSER_*。
    """
    # 1. 下载器特有配置（用户显式覆盖，None 表示未设置 → 回退）
    specific_key = f"{prefix}_{key}"
    value = settings.get(specific_key, None)
    if value is not None:
        return value

    # 2. 浏览器通用配置
    common_key = f"BROWSER_{key}"
    value = settings.get(common_key, None)
    if value is not None:
        return value

    # 3. 硬编码默认值
    return default
```

### 3.2 新增通用配置定义

在 `default_settings.py` 的 **3.1 下载器通用配置** 和 **3.5 Playwright 配置** 之间，新增 **3.X 浏览器下载器通用配置**：

```python
# ----- 3.X 浏览器下载器通用配置 -----
# 以下配置适用于所有浏览器下载器（Playwright / Camoufox / CloakBrowser / DrissionPage）
# 各下载器可通过自身前缀的配置覆盖通用配置（如 CLOAKBROWSER_HEADLESS 覆盖 BROWSER_HEADLESS）

BROWSER_HEADLESS = True              # 无头模式
BROWSER_TIMEOUT = 30000              # 超时时间（毫秒）
BROWSER_LOAD_TIMEOUT = 10000         # 页面加载超时（毫秒）
BROWSER_VIEWPORT_WIDTH = 1280        # 视口宽度
BROWSER_VIEWPORT_HEIGHT = 720        # 视口高度
BROWSER_MAX_PAGES = 10               # 单浏览器最大页面数
BROWSER_PROXY = None                 # 代理设置
BROWSER_BLOCK_RESOURCES = ["image", "font", "media"]  # 屏蔽的资源类型
BROWSER_AUTO_SCROLL = False          # 是否自动滚动加载更多内容
BROWSER_SCROLL_DELAY = 500           # 滚动延迟（毫秒）
BROWSER_WAIT_STRATEGY = "auto"       # 等待策略: auto, networkidle, domcontentloaded, element
BROWSER_WAIT_TIMEOUT = 10000         # 智能等待超时时间（毫秒）
BROWSER_WAIT_FOR_ELEMENT = None      # 等待特定元素选择器
BROWSER_STEALTH_LEVEL = 'basic'      # 反检测级别: none, basic, advanced
BROWSER_HUMANIZE = False             # 是否启用拟人化行为模拟
```

### 3.3 各下载器配置精简

整合后，各下载器只保留**特有参数**：

```python
# ----- Playwright 配置 -----
# 通用配置由 BROWSER_* 提供，以下仅保留 Playwright 特有参数
PLAYWRIGHT_BROWSER_TYPE = "chromium"       # 浏览器类型（Playwright 特有）
PLAYWRIGHT_SINGLE_BROWSER_MODE = True       # 单浏览器多标签页模式（Playwright 特有）
PLAYWRIGHT_BLOCK_ADS = True                 # 是否屏蔽广告（Playwright 特有）
PLAYWRIGHT_BLOCK_WEBRTC = False             # 是否阻止 WebRTC 泄露（Playwright 特有）
PLAYWRIGHT_HIDE_CANVAS = False              # 是否为 Canvas 添加随机噪声（Playwright 特有）
PLAYWRIGHT_ALLOW_WEBGL = True               # 是否启用 WebGL（Playwright 特有）
PLAYWRIGHT_REAL_CHROME = False              # 是否使用本地 Chrome（Playwright 特有）
PLAYWRIGHT_GOOGLE_REFERER = True            # 是否自动添加 Google Referer（Playwright 特有）
PLAYWRIGHT_IGNORE_HTTPS_ERRORS = True       # 是否忽略 HTTPS 错误（Playwright 特有）

# ----- DrissionPage 配置 -----
DRISSIONPAGE_BROWSER_PATH = None            # 浏览器路径（DrissionPage 特有）
DRISSIONPAGE_USER_DATA_PATH = None          # 用户数据目录（DrissionPage 特有）
DRISSIONPAGE_LOAD_IMAGES = True             # 是否加载图片（DrissionPage 特有）

# ----- Camoufox 配置 -----
CAMOUFOX_SOLVE_CLOUDFLARE = True            # 自动解决 Cloudflare Turnstile（Camoufox 核心能力）

# ----- CloakBrowser 配置 -----
CLOAKBROWSER_HUMAN_PRESET = "default"       # humanize 预设
CLOAKBROWSER_HUMAN_CONFIG = None            # humanize 自定义配置（dict）
CLOAKBROWSER_GEOIP = False                  # GeoIP 自动时区匹配
CLOAKBROWSER_TIMEZONE = None                # 手动设置时区
CLOAKBROWSER_LOCALE = None                  # 手动设置语言环境
CLOAKBROWSER_BACKEND = "playwright"         # 后端引擎
CLOAKBROWSER_STEALTH_ARGS = True            # 隐身启动参数
CLOAKBROWSER_FINGERPRINT = None             # 指纹种子
CLOAKBROWSER_FINGERPRINT_PLATFORM = None    # 指纹平台
CLOAKBROWSER_ARGS = []                      # 额外启动参数
CLOAKBROWSER_PERSISTENT_CONTEXT = False     # 持久化上下文模式
CLOAKBROWSER_USER_DATA_DIR = None           # 持久化用户数据目录
```

> **关键设计**：各下载器前缀的覆盖参数（如 `PLAYWRIGHT_HEADLESS`）**必须从 default_settings.py 中删除**（改为注释参考），否则 `SettingManager.get("PLAYWRIGHT_HEADLESS")` 永远返回 `True`（来自 defaults），永不回退到 `BROWSER_HEADLESS`。用户如需按下载器覆盖，可自行在 settings.py 中添加。例外：`CAMOUFOX_HUMANIZE = True` 保留为活跃定义，因其默认值与 `BROWSER_HUMANIZE = False` 不同。

### 3.4 DrissionPage 单位转换

DrissionPage 内部使用秒为单位，整合后需在读取时转换：

```python
# DrissionPage 下载器中
timeout_ms = get_browser_config(settings, "DRISSIONPAGE", "TIMEOUT", 30000, int)
timeout_seconds = timeout_ms / 1000  # 转换为秒供 DrissionPage 使用

scroll_delay_ms = get_browser_config(settings, "DRISSIONPAGE", "SCROLL_DELAY", 500, int)
scroll_delay_seconds = scroll_delay_ms / 1000
```

---

## 四、实现步骤

### Step 1：新增工具函数

**文件**：`crawlo/utils/misc.py`（紧接 `safe_get_config` 之后）

```python
def get_browser_config(settings, prefix: str, key: str, default: Any = None) -> Any:
    """获取原始值，三级优先级回退"""
    specific_key = f"{prefix}_{key}"
    common_key = f"BROWSER_{key}"
    value = settings.get(specific_key, None)
    if value is not None:
        return value
    value = settings.get(common_key, None)
    if value is not None:
        return value
    return default
```
同时提供 `get_browser_config_int` / `_bool` / `_list` 类型安全变体（兼容 `get_int`/`get_bool`/`get_list` 的行为）。

### Step 2：修改 `default_settings.py`

1. 在 3.4 和 3.5 之间新增 `BROWSER_*` 通用配置（15 个参数）
2. 各下载器配置区**删除**重复的默认定义（改为注释参考），仅保留特有参数
3. 原因：`SettingManager` 加载 defaults 后，`settings.get("PLAYWRIGHT_HEADLESS")` 会直接返回 `True`（来自 defaults），永不回退到 `BROWSER_HEADLESS`。必须删除才能在未显式覆盖时触发回退
4. 例外：`CAMOUFOX_HUMANIZE = True` 保留为活跃定义（与 `BROWSER_HUMANIZE = False` 不同）

### Step 3：修改各下载器实现

按以下顺序修改读取逻辑：

| 顺序 | 文件 | 修改内容 |
|------|------|---------|
| 1 | `crawlo/downloader/playwright_downloader.py` | 替换 `safe_get_config(settings, "PLAYWRIGHT_XXX", ...)` 为 `get_browser_config(settings, "PLAYWRIGHT", "XXX", ...)` |
| 2 | `crawlo/downloader/camoufox_downloader.py` | 同上 |
| 3 | `crawlo/downloader/cloakbrowser_downloader.py` | 同上 |
| 4 | `crawlo/downloader/drissionpage_downloader.py` | 同上 + 毫秒→秒转换 |

### Step 4：修复已知不一致问题

| 问题 | 修复方案 |
|------|---------|
| AioHttp `DOWNLOAD_TIMEOUT` 默认值 30 vs 配置 15 | 统一为 15 |
| CurlCffi `CONNECTION_POOL_LIMIT` 默认值 20 vs 配置 100 | 统一为 100 |
| AioHttp `CONNECTION_POOL_LIMIT_PER_HOST` 默认值 0 vs 配置 20 | 统一为 20 |
| 基类读 `DOWNLOADER_STATS` vs 配置 `DOWNLOAD_STATS` | 统一为 `DOWNLOAD_STATS` |

### Step 5：编写测试

```python
# tests/test_browser_config.py

def test_browser_config_fallback():
    """测试三级优先级回退"""
    # 1. 无任何配置 → 使用默认值
    # 2. 只设 BROWSER_HEADLESS=False → 所有下载器使用 False
    # 3. 设 BROWSER_HEADLESS=False + CLOAKBROWSER_HEADLESS=True → CloakBrowser 用 True，其他用 False
    pass

def test_drissionpage_unit_conversion():
    """测试 DrissionPage 毫秒→秒转换"""
    # BROWSER_TIMEOUT=30000 → DrissionPage 内部使用 30
    pass

def test_backward_compatibility():
    """测试旧配置继续生效"""
    # PLAYWRIGHT_HEADLESS=False 应该仍然生效
    pass
```

---

## 五、影响范围

### 5.1 需修改的文件

| 文件 | 修改类型 | 影响程度 |
|------|---------|---------|
| `crawlo/settings/default_settings.py` | 新增 BROWSER_* 配置区 | 中 |
| `crawlo/utils/config.py`（或 setting_manager.py） | 新增 `get_browser_config()` | 低 |
| `crawlo/downloader/playwright_downloader.py` | 替换配置读取逻辑 | 中 |
| `crawlo/downloader/camoufox_downloader.py` | 替换配置读取逻辑 | 中 |
| `crawlo/downloader/cloakbrowser_downloader.py` | 替换配置读取逻辑 | 中 |
| `crawlo/downloader/drissionpage_downloader.py` | 替换配置读取逻辑 + 单位转换 | 中 |
| `crawlo/downloader/aiohttp_downloader.py` | 修复默认值不一致 | 低 |
| `crawlo/downloader/httpx_downloader.py` | 修复默认值不一致（如有） | 低 |
| `crawlo/downloader/cffi_downloader.py` | 修复默认值不一致 | 低 |
| `crawlo/downloader/__init__.py` | 修复 DOWNLOADER_STATS 命名 | 低 |

### 5.2 无需修改的文件

- 用户项目的 `settings.py`（100% 向后兼容）
- 现有爬虫代码
- 中间件、管道等非下载器模块

---

## 六、配置使用示例

### 整合前

```python
# settings.py - 切换下载器需配置4套几乎相同的参数
PLAYWRIGHT_HEADLESS = False
PLAYWRIGHT_TIMEOUT = 60000
PLAYWRIGHT_VIEWPORT_WIDTH = 1920
PLAYWRIGHT_VIEWPORT_HEIGHT = 1080
PLAYWRIGHT_PROXY = "http://proxy:8080"
PLAYWRIGHT_BLOCK_RESOURCES = ["image", "font", "media"]
PLAYWRIGHT_AUTO_SCROLL = True

# 如果换成 CloakBrowser，又得配一遍
CLOAKBROWSER_HEADLESS = False
CLOAKBROWSER_TIMEOUT = 60000
CLOAKBROWSER_VIEWPORT_WIDTH = 1920
CLOAKBROWSER_VIEWPORT_HEIGHT = 1080
CLOAKBROWSER_PROXY = "http://proxy:8080"
CLOAKBROWSER_BLOCK_RESOURCES = ["image", "font", "media"]
CLOAKBROWSER_AUTO_SCROLL = True
```

### 整合后

```python
# settings.py - 一套通用配置搞定
BROWSER_HEADLESS = False
BROWSER_TIMEOUT = 60000
BROWSER_VIEWPORT_WIDTH = 1920
BROWSER_VIEWPORT_HEIGHT = 1080
BROWSER_PROXY = "http://proxy:8080"
BROWSER_BLOCK_RESOURCES = ["image", "font", "media"]
BROWSER_AUTO_SCROLL = True

# CloakBrowser 特有需求单独覆盖
CLOAKBROWSER_GEOIP = True
CLOAKBROWSER_FINGERPRINT = 42
```

---

## 七、风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 旧配置失效 | 低 | 三级回退机制确保旧配置优先级最高 |
| DrissionPage 单位转换错误 | 中 | 增加专门的单元测试 |
| `get_browser_config` 与 `safe_get_config` 行为不一致 | 中 | 统一使用相同的配置读取底层接口 |
| 配置覆盖逻辑不直观 | 低 | 文档说明优先级规则 |

---

## 八、验收标准

- [ ] `BROWSER_*` 通用配置可被所有 4 个浏览器下载器正确读取
- [ ] 下载器特有配置（如 `CLOAKBROWSER_HEADLESS`）可覆盖 `BROWSER_HEADLESS`
- [ ] DrissionPage 毫秒→秒转换正确
- [ ] 所有现有测试通过
- [ ] 新增配置优先级测试用例
- [ ] 已知默认值不一致问题已修复
- [ ] 向后兼容：仅使用旧配置的项目行为不变
