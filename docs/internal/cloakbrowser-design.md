# CloakBrowser 下载器设计方案

## 一、背景与动机

CloakBrowser 是一款源码级修补的隐身 Chromium，通过 57 项 C++ 补丁修改指纹特征，可完美绕过 Cloudflare Turnstile、reCAPTCHA v3（0.9 评分）、FingerprintJS、BrowserScan 等 30+ 种反机器人检测服务。

相比现有动态下载器的优势：

| 特性 | PlaywrightDownloader | DrissionPageDownloader | CamoufoxDownloader | **CloakBrowserDownloader** |
|------|---------------------|----------------------|--------------------|---------------------------|
| 反检测层级 | JS 注入（易被检测） | JS 注入 | Firefox C++ 补丁 | **Chromium C++ 补丁** |
| reCAPTCHA v3 分数 | 低（0.3-0.5） | 低 | 中高 | **0.9+** |
| Cloudflare 绕过 | 不稳定 | 不稳定 | 支持 | **原生支持** |
| 类人行为 | 无 | 无 | 内置 | **内置（更成熟）** |
| GeoIP 时区匹配 | 手动配置 | 手动配置 | 无 | **自动检测** |
| WebRTC 泄漏防护 | 需额外配置 | 需额外配置 | 无 | **自动注入** |
| 指纹持久化 | 不支持 | 不支持 | 不支持 | **种子固定** |

**定位**：作为 HybridDownloader 中最高等级的动态下载器，用于 Playwright/Camoufox 被检测的场景。

---

## 二、安装依赖

### 2.1 安装方式

```bash
# 方式 1: 作为 Crawlo 可选依赖安装（推荐）
pip install crawlo[stealth]

# 方式 2: 单独安装 cloakbrowser
pip install cloakbrowser

# 方式 3: 带 GeoIP 自动时区检测
pip install cloakbrowser[geoip]

# 方式 4: 带 Patchright 后端（更高级的 reCAPTCHA 绕过，但破坏代理认证）
pip install cloakbrowser[patchright]

# 方式 5: 安装 Crawlo 所有可选依赖
pip install crawlo[all]
```

> 注意：**不需要** `playwright install chromium`，CloakBrowser 下载自己的隐身二进制文件（约 200MB，缓存至 `~/.cloakbrowser/`）。

### 2.2 依赖管理策略

CloakBrowser 作为 Crawlo 的**可选依赖**（`extras_require`），不作为默认安装项。

**配置位置**：
- `setup.cfg` → `[options.extras_require]` → `stealth = cloakbrowser[geoip]>=0.3.14`
- `requirements.txt` → 注释说明（不启用）

**为什么不是默认依赖？**
- 首次启动需下载 ~200MB Chromium 二进制
- 仅强反爬场景需要，非通用需求
- 遵循 Crawlo 按需安装策略（与 playwright 一致）

**用户安装方式**：
```bash
# 只安装 stealth 依赖（推荐）
pip install crawlo[stealth]

# 组合安装
pip install crawlo[render,stealth]

# 单独安装（不通过 Crawlo）
pip install cloakbrowser[geoip]
```

---

## 三、架构设计

### 3.1 类层次

```
DownloaderBase (crawlo.downloader)
└── CloakBrowserDownloader
    ├── 复用 SmartWaitMixin（智能等待策略）
    ├── 复用 PageActionHandler（通用页面操作）
    ├── 复用 SelectorConverter（选择器转换）
    └── 不复用 StealthMixin（CloakBrowser 已内置 C++ 级反检测，JS 注入无意义且冲突）
```

### 3.2 核心设计原则

1. **异步优先**：使用 `launch_async()` 启动浏览器，完全融入 Crawlo 的 asyncio 事件循环
2. **不复用 StealthMixin**：CloakBrowser 已在 C++ 层面处理所有指纹伪造，额外注入 JS 脚本反而可能产生冲突
3. **页面池模式**：复用 PlaywrightDownloader 的单浏览器多标签页策略，通过信号量控制并发
4. **懒加载初始化**：浏览器在首次 `download()` 调用时才启动，避免空转开销
5. **配置前缀统一**：所有 settings 以 `CLOAKBROWSER_` 开头，与框架其他下载器风格一致

### 3.3 与 HybridDownloader 的集成

```
HybridDownloader
├── _downloaders["protocol"] → AioHttpDownloader / HttpXDownloader
└── _downloaders["dynamic"]
    ├── playwright  → PlaywrightDownloader    （常规动态渲染）
    ├── drissionpage → DrissionPageDownloader  （简单动态渲染）
    ├── camoufox    → CamoufoxDownloader      （中度反检测）
    └── cloakbrowser → CloakBrowserDownloader （高强度反检测）
```

配置方式：
```python
# settings.py — 将 CloakBrowser 设为默认动态下载器
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "cloakbrowser"

# 或独立使用
DOWNLOADER = "crawlo.downloader.cloakbrowser_downloader.CloakBrowserDownloader"
DOWNLOADER_TYPE = "cloakbrowser"
```

---

## 四、详细设计

### 4.1 配置项

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `CLOAKBROWSER_HEADLESS` | bool | `True` | 无头模式。高强度站点建议 `False` |
| `CLOAKBROWSER_PROXY` | str/dict | `None` | 代理配置，支持 HTTP/SOCKS5 |
| `CLOAKBROWSER_HUMANIZE` | bool | `False` | 类人鼠标/键盘/滚动行为 |
| `CLOAKBROWSER_HUMAN_PRESET` | str | `"default"` | 人化预设：`"default"` 或 `"careful"` |
| `CLOAKBROWSER_HUMAN_CONFIG` | dict | `None` | 自定义人化配置 |
| `CLOAKBROWSER_GEOIP` | bool | `False` | 从代理 IP 自动检测时区和语言 |
| `CLOAKBROWSER_TIMEZONE` | str | `None` | 手动时区（如 `"America/New_York"`） |
| `CLOAKBROWSER_LOCALE` | str | `None` | 手动语言区域（如 `"en-US"`） |
| `CLOAKBROWSER_BACKEND` | str | `"playwright"` | 后端：`"playwright"` 或 `"patchright"` |
| `CLOAKBROWSER_STEALTH_ARGS` | bool | `True` | 启用默认隐身参数 |
| `CLOAKBROWSER_FINGERPRINT` | str/int | `None` | 固定指纹种子（用于会话持久化） |
| `CLOAKBROWSER_FINGERPRINT_PLATFORM` | str | `None` | 指纹平台：`"windows"` / `"macos"` / `"linux"` |
| `CLOAKBROWSER_ARGS` | list | `[]` | 额外 Chromium 命令行参数 |
| `CLOAKBROWSER_TIMEOUT` | int | `30000` | 默认超时（毫秒） |
| `CLOAKBROWSER_LOAD_TIMEOUT` | int | `10000` | 导航超时（毫秒） |
| `CLOAKBROWSER_VIEWPORT_WIDTH` | int | `1280` | 视口宽度 |
| `CLOAKBROWSER_VIEWPORT_HEIGHT` | int | `720` | 视口高度 |
| `CLOAKBROWSER_MAX_PAGES` | int | `10` | 最大标签页数 |
| `CLOAKBROWSER_BLOCK_RESOURCES` | list | `["image","font","media"]` | 屏蔽的资源类型 |
| `CLOAKBROWSER_AUTO_SCROLL` | bool | `False` | 自动滚动 |
| `CLOAKBROWSER_SCROLL_DELAY` | int | `500` | 滚动延迟（毫秒） |
| `CLOAKBROWSER_WAIT_STRATEGY` | str | `"auto"` | 等待策略 |
| `CLOAKBROWSER_WAIT_TIMEOUT` | int | `10000` | 等待超时（毫秒） |
| `CLOAKBROWSER_PERSISTENT_CONTEXT` | bool | `False` | 是否使用持久化上下文 |
| `CLOAKBROWSER_USER_DATA_DIR` | str | `None` | 持久化配置目录路径 |

### 4.2 请求级 meta 覆盖

所有全局配置均可通过 `request.meta` 在单请求级别覆盖，前缀为 `cloakbrowser_`：

```python
request.meta = {
    "use_dynamic_loader": True,          # HybridDownloader 识别
    "cloakbrowser_headless": False,       # 该请求用有头模式
    "cloakbrowser_humanize": True,        # 该请求启用类人行为
    "cloakbrowser_wait_strategy": "networkidle",
    "cloakbrowser_auto_scroll": True,
    # ... 自定义操作
    "dynamic_actions": [
        {"type": "click", "selector": "#load-more"},
        {"type": "scroll_to_bottom", "params": {"max_no_content": 3}},
    ]
}
```

### 4.3 核心方法设计

```python
class CloakBrowserDownloader(DownloaderBase, SmartWaitMixin):
    """
    基于 CloakBrowser 的隐身动态下载器
    
    CloakBrowser 是源码级修补的 Chromium，内置 57 项 C++ 补丁，
    无需 JS 注入即可绕过主流反机器人检测。
    
    优势：
    - reCAPTCHA v3 0.9+ 评分
    - Cloudflare Turnstile 原生绕过
    - 内置类人行为模拟（humanize）
    - GeoIP 自动时区匹配
    - WebRTC IP 泄漏自动防护
    - 指纹种子持久化
    """
```

#### `__init__(self, crawler)`

- 调用 `super().__init__(crawler)`
- 读取所有 `CLOAKBROWSER_*` 配置项
- 初始化页面池 `_page_pool`、`_used_pages`、`_page_semaphore`

#### `open(self)`

- 调用 `super().open()`
- 仅打印日志，**不启动浏览器**（懒加载）

#### `async _initialize_browser(self)`

- 懒加载：在首次 `download()` 时调用
- 构建 `launch_kwargs` 配置字典
- 调用 `await launch_async(**launch_kwargs)` 获取 Browser
- 调用 `browser.new_context(**context_options)` 创建上下文
- 初始化信号量

关键逻辑：
```python
from cloakbrowser import launch_async

launch_kwargs = {
    "headless": self.headless,
    "proxy": self.proxy,
    "humanize": self.humanize,
    "geoip": self.geoip,
    "stealth_args": self.stealth_args,
    "backend": self.backend,
}

# 可选参数
if self.timezone:
    launch_kwargs["timezone"] = self.timezone
if self.locale:
    launch_kwargs["locale"] = self.locale
if self.human_preset:
    launch_kwargs["human_preset"] = self.human_preset
if self.human_config:
    launch_kwargs["human_config"] = self.human_config
if self.args:
    launch_kwargs["args"] = self.args

# 指纹种子
if self.fingerprint is not None:
    fp_args = list(self.args) + [f"--fingerprint={self.fingerprint}"]
    if self.fingerprint_platform:
        fp_args.append(f"--fingerprint-platform={self.fingerprint_platform}")
    launch_kwargs["args"] = fp_args

self._browser = await launch_async(**launch_kwargs)
self._context = await self._browser.new_context(
    viewport={"width": self.viewport_width, "height": self.viewport_height},
    ignore_https_errors=True,
)
```

#### `async download(self, request) -> Optional[Response]`

完整流程：
1. **懒加载初始化**：如未启动浏览器，调用 `_initialize_browser()`
2. **获取页面**：从页面池获取或创建新标签页
3. **设置超时和视口**
4. **设置资源屏蔽**：复用 PlaywrightDownloader 的 route 拦截模式
5. **应用请求设置**：headers、cookies
6. **导航**：`page.goto(url, wait_until=wait_until)`
7. **智能等待**：复用 `SmartWaitMixin._smart_wait_for_page_load()`
8. **自动滚动**：如有配置
9. **自定义操作**：通过 `PageActionHandler` 执行
10. **翻页操作**：如有配置
11. **提取内容**：`page.content()`、`page.url`、`response.status`
12. **构造 Response**：统一格式返回
13. **归还页面**：finally 中归还到页面池

#### `async close(self)`

1. 关闭页面池中所有页面
2. 关闭 context
3. 关闭 browser
4. 清空所有引用

### 4.4 与 PlaywrightDownloader 的关键差异

| 方面 | PlaywrightDownloader | CloakBrowserDownloader |
|------|---------------------|----------------------|
| 浏览器启动 | `async_playwright().start()` → `playwright.chromium.launch()` | `launch_async()` |
| 反检测 | `StealthMixin`（JS 注入） | **无**（C++ 层已内置） |
| 代理配置 | settings → launch kwargs | settings → launch kwargs（相同） |
| 类人行为 | 无 | `humanize` / `human_preset` / `human_config` |
| GeoIP | 无 | `geoip=True` 自动检测 |
| 指纹管理 | 无 | `--fingerprint=seed` 种子持久化 |
| 资源屏蔽 | `SmartWaitMixin` 中的 route 拦截 | 相同方式（CloakBrowser 返回标准 Page） |
| 页面操作 | `PageActionHandler` + `SelectorConverter` | 完全复用 |
| Google Referer | 默认注入 | **不注入**（CloakBrowser 不需要额外伪装） |

### 4.5 需要修改的框架文件

#### 1. 新增文件：`crawlo/downloader/cloakbrowser_downloader.py`

CloakBrowser 下载器主文件。

#### 2. 修改文件：`crawlo/downloader/__init__.py`

在下载器导入区域添加：
```python
try:
    from .cloakbrowser_downloader import CloakBrowserDownloader
except ImportError:
    CloakBrowserDownloader = None
```

在 `DOWNLOADER_MAP` 中添加：
```python
'cloakbrowser': CloakBrowserDownloader,
```

#### 3. 修改文件：`crawlo/downloader/hybrid_downloader.py`

在 `_get_downloader_class()` 的 `downloader_map` 中添加：
```python
"cloakbrowser": (".cloakbrowser_downloader", "CloakBrowserDownloader"),
```

#### 4. 修改文件：`crawlo/settings/default_settings.py`

添加 CloakBrowser 相关默认配置（可选，因下载器内部已有默认值）。

---

## 五、使用示例

### 5.1 独立使用

```python
# settings.py
DOWNLOADER_TYPE = "cloakbrowser"

CLOAKBROWSER_HEADLESS = False        # 高对抗站点建议有头模式
CLOAKBROWSER_HUMANIZE = True         # 启用类人行为
CLOAKBROWSER_GEOIP = True            # 自动时区匹配
CLOAKBROWSER_PROXY = "http://user:pass@residential-proxy:8080"  # 住宅代理
CLOAKBROWSER_FINGERPRINT = 42069     # 固定指纹种子
CLOAKBROWSER_BLOCK_RESOURCES = ["image", "font", "media"]
CLOAKBROWSER_AUTO_SCROLL = True
```

### 5.2 在 HybridDownloader 中使用

```python
# settings.py
DOWNLOADER_TYPE = "hybrid"
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = "cloakbrowser"

# 指定特定域名使用 CloakBrowser
HYBRID_DYNAMIC_DOMAINS = ["www.cloudflare-protected-site.com"]

# 指定 URL 模式
HYBRID_DYNAMIC_URL_PATTERNS = [r".*/captcha-protected/.*"]
```

### 5.3 请求级别控制

```python
import scrapy

class MySpider:
    def start_requests(self):
        yield Request(
            url="https://high-protection-site.com/page",
            meta={
                "use_dynamic_loader": True,
                # CloakBrowser 特定配置
                "cloakbrowser_humanize": True,
                "cloakbrowser_geoip": True,
                "cloakbrowser_headless": False,
                # 页面操作
                "dynamic_actions": [
                    {"type": "wait", "params": {"timeout": 3000}},  # 等待 3 秒（推荐用 time.sleep 代替 page.wait_for_timeout）
                    {"type": "click", "selector": "#accept-cookies"},
                    {"type": "scroll_to_bottom", "params": {"max_no_content": 3}},
                ]
            }
        )
```

### 5.4 持久化会话

```python
# settings.py
CLOAKBROWSER_PERSISTENT_CONTEXT = True
CLOAKBROWSER_USER_DATA_DIR = "./browser_profiles/my_session"
CLOAKBROWSER_FINGERPRINT = 12345  # 固定指纹，跨运行保持一致
```

### 5.5 reCAPTCHA v3 优化配置

```python
# settings.py
CLOAKBROWSER_HEADLESS = False
CLOAKBROWSER_HUMANIZE = True
CLOAKBROWSER_HUMAN_PRESET = "careful"    # 更慢更审慎
CLOAKBROWSER_GEOIP = True
CLOAKBROWSER_PROXY = "socks5://user:pass@residential-proxy:1080"  # SOCKS5 推荐
CLOAKBROWSER_FINGERPRINT = 42069         # 固定指纹种子
CLOAKBROWSER_ARGS = ["--fingerprint-storage-quota=5000"]  # 避免 BrowserScan notPrivate 标记
```

---

## 六、注意事项

### 6.1 humanize 模式下的 API 使用

| 推荐用法 | 避免用法 | 原因 |
|---------|---------|------|
| `page.click(selector)` | `page.query_selector()` → `.click()` | ElementHandle 绕过人化管道 |
| `page.type(selector, text)` | `page.fill(selector, text)` | fill 是瞬时的，type 有键盘事件 |
| `page.locator(selector).*` | — | Locator API 经过完整人化 |
| `time.sleep(3)` | `page.wait_for_timeout(3000)` | wait_for_timeout 发 CDP 命令，可被 reCAPTCHA 检测 |

### 6.2 macOS 首次启动

macOS 需要手动允许二进制执行：
```bash
xattr -cr ~/.cloakbrowser/chromium-*/Chromium.app
```

### 6.3 macOS 指纹不一致

在激进检测下 macOS 指纹可能不一致，建议切换到 Windows 指纹：
```python
CLOAKBROWSER_FINGERPRINT_PLATFORM = "windows"
```

### 6.4 Patchright 后端限制

使用 `backend="patchright"` 时：
- 代理认证（username/password）会失效
- `add_init_script` 不可用
- 仅在默认后端 reCAPTCHA 分数仍低时使用

### 6.5 内存占用

| 状态 | 内存 |
|------|------|
| 空闲 | ~190 MB |
| 3 标签页 | ~280 MB |
| 每额外标签页 | ~30 MB |

### 6.6 与现有下载器的选择策略

```
请求需要动态渲染？
├── 否 → 协议下载器（aiohttp/httpx/curl_cffi）
└── 是 → 是否有高强度反检测？
    ├── 否 → PlaywrightDownloader（最轻量）
    ├── 中度 → CamoufoxDownloader（Firefox 变体）
    └── 是 → CloakBrowserDownloader（最强反检测）
```

---

## 七、文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `crawlo/downloader/cloakbrowser_downloader.py` | **新增** | CloakBrowser 下载器主文件 |
| `crawlo/downloader/__init__.py` | **修改** | 添加 CloakBrowserDownloader 导入和 DOWNLOADER_MAP 注册 |
| `crawlo/downloader/hybrid_downloader.py` | **修改** | 在 `_get_downloader_class()` 的映射中添加 cloakbrowser |
| `docs/cloakbrowser_downloader_design.md` | **新增** | 本设计文档 |

---

## 八、CloakBrowserDownloader 伪代码

```python
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 下载器
====================
基于 CloakBrowser 的隐身动态内容下载器。

CloakBrowser 特性:
- 源码级修补的 Chromium（57 项 C++ 补丁）
- 内置全链路指纹伪造，无需 JS 注入
- reCAPTCHA v3 0.9+ 评分
- Cloudflare Turnstile 原生绕过
- 类人行为模拟（humanize）
- GeoIP 自动时区匹配
- 指纹种子持久化

依赖安装:
pip install cloakbrowser
pip install cloakbrowser[geoip]  # GeoIP 支持
"""

import time
import asyncio
from typing import Optional, Dict, List, Set

from crawlo.downloader import DownloaderBase
from crawlo.downloader.wait_strategies import SmartWaitMixin, WaitStrategy
from crawlo.utils.page_utils import PageActionHandler, SelectorConverter
from crawlo.network.response import Response
from crawlo.logging import get_logger
from crawlo.constants import (
    BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS,
    BROWSER_ELEMENT_WAIT_TIMEOUT_MS,
    BROWSER_NETWORK_IDLE_TIMEOUT_MS,
)


class CloakBrowserDownloader(DownloaderBase, SmartWaitMixin):
    """
    基于 CloakBrowser 的隐身动态内容下载器

    相比 PlaywrightDownloader:
    - 无需 JS 注入即可绕过反检测（C++ 层内置）
    - 内置类人行为模拟（humanize）
    - GeoIP 自动时区匹配
    - 指纹种子持久化
    - reCAPTCHA v3 0.9+ 评分

    使用场景:
    - 高强度反爬网站（Cloudflare、DataDome、PerimeterX 等）
    - reCAPTCHA v3 Enterprise 评分系统
    - 需要持久化浏览器身份的场景
    - Playwright/Camoufox 被检测后的降级方案
    """

    def __init__(self, crawler):
        super().__init__(crawler)
        self.logger = get_logger(self.__class__.__name__)

        # 浏览器实例
        self._browser = None
        self._context = None

        # 页面池
        self._page_pool: List = []
        self._used_pages: set = set()
        self._page_semaphore: Optional[asyncio.Semaphore] = None
        self._page_semaphore_lock = asyncio.Lock()

        # ===== 基础配置 =====
        self.headless = crawler.settings.get_bool("CLOAKBROWSER_HEADLESS", True)
        self.proxy = crawler.settings.get("CLOAKBROWSER_PROXY", None)
        self.timeout = crawler.settings.get_int("CLOAKBROWSER_TIMEOUT", 30000)
        self.load_timeout = crawler.settings.get_int("CLOAKBROWSER_LOAD_TIMEOUT", 10000)
        self.viewport_width = crawler.settings.get_int("CLOAKBROWSER_VIEWPORT_WIDTH", 1280)
        self.viewport_height = crawler.settings.get_int("CLOAKBROWSER_VIEWPORT_HEIGHT", 720)
        self.max_pages = crawler.settings.get_int("CLOAKBROWSER_MAX_PAGES", 10)

        # ===== CloakBrowser 特有配置 =====
        self.humanize = crawler.settings.get_bool("CLOAKBROWSER_HUMANIZE", False)
        self.human_preset = crawler.settings.get("CLOAKBROWSER_HUMAN_PRESET", "default")
        self.human_config = crawler.settings.get("CLOAKBROWSER_HUMAN_CONFIG", None)
        self.geoip = crawler.settings.get_bool("CLOAKBROWSER_GEOIP", False)
        self.timezone = crawler.settings.get("CLOAKBROWSER_TIMEZONE", None)
        self.locale = crawler.settings.get("CLOAKBROWSER_LOCALE", None)
        self.backend = crawler.settings.get("CLOAKBROWSER_BACKEND", "playwright")
        self.stealth_args = crawler.settings.get_bool("CLOAKBROWSER_STEALTH_ARGS", True)
        self.fingerprint = crawler.settings.get("CLOAKBROWSER_FINGERPRINT", None)
        self.fingerprint_platform = crawler.settings.get("CLOAKBROWSER_FINGERPRINT_PLATFORM", None)
        self.extra_args = crawler.settings.get_list("CLOAKBROWSER_ARGS", [])

        # ===== 持久化配置 =====
        self.persistent_context = crawler.settings.get_bool("CLOAKBROWSER_PERSISTENT_CONTEXT", False)
        self.user_data_dir = crawler.settings.get("CLOAKBROWSER_USER_DATA_DIR", None)

        # ===== 等待策略 =====
        self.wait_strategy = crawler.settings.get("CLOAKBROWSER_WAIT_STRATEGY", "auto")
        self.wait_timeout = crawler.settings.get_int("CLOAKBROWSER_WAIT_TIMEOUT", 10000)

        # ===== 资源屏蔽 =====
        self.block_resources: Set[str] = set(
            crawler.settings.get_list("CLOAKBROWSER_BLOCK_RESOURCES", ["image", "font", "media"])
        )

        # ===== 自动滚动 =====
        self.auto_scroll = crawler.settings.get_bool("CLOAKBROWSER_AUTO_SCROLL", False)
        self.scroll_delay = crawler.settings.get_int("CLOAKBROWSER_SCROLL_DELAY", 500)

    def open(self):
        super().open()
        self.logger.info("Opening CloakBrowserDownloader (lazy initialization)")

    async def _initialize_browser(self):
        """懒加载：首次 download 时初始化浏览器"""
        try:
            from cloakbrowser import launch_async, launch_persistent_context_async
        except ImportError:
            raise ImportError(
                "CloakBrowser is not installed. "
                "Please install with: pip install cloakbrowser[geoip]"
            )

        try:
            # 构建启动参数
            launch_kwargs = {
                "headless": self.headless,
                "humanize": self.humanize,
                "geoip": self.geoip,
                "stealth_args": self.stealth_args,
                "backend": self.backend,
            }

            # 可选参数
            if self.proxy:
                launch_kwargs["proxy"] = self.proxy
            if self.timezone:
                launch_kwargs["timezone"] = self.timezone
            if self.locale:
                launch_kwargs["locale"] = self.locale
            if self.humanize and self.human_preset:
                launch_kwargs["human_preset"] = self.human_preset
            if self.humanize and self.human_config:
                launch_kwargs["human_config"] = self.human_config

            # 构建额外参数（含指纹种子）
            args = list(self.extra_args)
            if self.fingerprint is not None:
                args.append(f"--fingerprint={self.fingerprint}")
            if self.fingerprint_platform:
                args.append(f"--fingerprint-platform={self.fingerprint_platform}")
            if args:
                launch_kwargs["args"] = args

            # 持久化上下文模式
            if self.persistent_context and self.user_data_dir:
                self._context = await launch_persistent_context_async(
                    self.user_data_dir, **launch_kwargs
                )
                self._browser = None  # 持久化模式无独立 Browser 对象
            else:
                self._browser = await launch_async(**launch_kwargs)
                self._context = await self._browser.new_context(
                    viewport={"width": self.viewport_width, "height": self.viewport_height},
                    ignore_https_errors=True,
                )

            # 初始化信号量
            self._page_semaphore = asyncio.Semaphore(self.max_pages)

            self.logger.info(
                f"CloakBrowserDownloader initialized "
                f"(headless={self.headless}, humanize={self.humanize}, "
                f"geoip={self.geoip}, backend={self.backend})"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize CloakBrowser: {e}")
            raise

    async def download(self, request) -> Optional[Response]:
        """下载动态内容"""
        # 懒加载初始化
        if not self._context:
            try:
                await self._initialize_browser()
            except Exception as e:
                self.logger.error(f"Failed to initialize CloakBrowser for {request.url}: {e}")
                return None

        start_time = time.time() if self.crawler.settings.get_bool("DOWNLOAD_STATS", True) else None

        page = None
        try:
            page = await self._get_page()

            # 设置超时
            page.set_default_timeout(self.timeout)
            page.set_default_navigation_timeout(self.load_timeout)

            # 设置视口
            await page.set_viewport_size({
                "width": self.viewport_width,
                "height": self.viewport_height,
            })

            # 资源屏蔽
            await self._setup_resource_blocking(page, request)

            # 请求级设置
            await self._apply_request_settings(page, request)

            # 导航
            wait_until = self._get_wait_until(request)
            response = await page.goto(request.url, wait_until=wait_until)

            # 智能等待
            await self._smart_wait_for_page_load(page, request)

            # 自动滚动
            if self._should_auto_scroll(request):
                await self._auto_scroll_page(page, request)

            # 自定义操作
            await self._execute_custom_actions(page, request)

            # 翻页操作
            await self._execute_pagination_actions(page, request)

            # 提取内容
            page_content = await page.content()
            page_url = page.url
            status_code = response.status if response else 200
            headers = dict(response.headers) if response else {}
            cookies = await self._get_cookies()

            # 构造响应
            crawlo_response = Response(
                url=page_url,
                headers=headers,
                status=status_code,
                body=page_content.encode('utf-8'),
                request=request,
            )
            crawlo_response.cookies = cookies

            if start_time:
                download_time = time.time() - start_time
                self.logger.debug(f"Downloaded {request.url} in {download_time:.3f}s")

            return crawlo_response

        except Exception as e:
            self.logger.debug(f"Download error for {request.url}: {type(e).__name__}: {e}")
            raise
        finally:
            if page:
                await self._release_page(page)

    # ---- 页面池管理 ----

    async def _get_page(self):
        """获取页面（单浏览器多标签页模式 + 信号量控制并发）"""
        if not self._context:
            raise RuntimeError("Browser context not initialized")

        await self._page_semaphore.acquire()
        semaphore_acquired = True

        try:
            for page in self._page_pool:
                if id(page) not in self._used_pages:
                    self._used_pages.add(id(page))
                    return page

            new_page = await self._context.new_page()
            self._page_pool.append(new_page)
            self._used_pages.add(id(new_page))
            return new_page

        except Exception:
            if semaphore_acquired:
                self._page_semaphore.release()
            raise

    async def _release_page(self, page):
        """归还页面到池中"""
        page_id = id(page)

        async with self._page_semaphore_lock:
            if page_id in self._used_pages:
                self._used_pages.discard(page_id)
                if self._page_semaphore:
                    self._page_semaphore.release()
                try:
                    await page.goto("about:blank", timeout=BROWSER_PAGE_GOTO_BLANK_TIMEOUT_MS)
                except Exception:
                    pass
            else:
                try:
                    await page.close()
                except Exception:
                    pass

    # ---- 等待策略 ----

    def _get_wait_until(self, request) -> str:
        strategy = request.meta.get("cloakbrowser_wait_strategy", self.wait_strategy)
        if strategy == "auto":
            return "domcontentloaded"
        elif strategy == "networkidle":
            return "networkidle"
        return "domcontentloaded"

    # ---- 资源屏蔽 ----

    async def _setup_resource_blocking(self, page, request):
        block_resources = request.meta.get("cloakbrowser_block_resources", self.block_resources)
        if not block_resources:
            return

        async def route_handler(route):
            if route.request.resource_type in block_resources:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

    # ---- 请求设置 ----

    async def _apply_request_settings(self, page, request):
        if request.headers:
            await page.set_extra_http_headers(request.headers)
        if request.cookies:
            from urllib.parse import urlparse
            parsed = urlparse(request.url)
            cookies = [
                {"name": k, "value": v, "domain": parsed.netloc, "path": "/"}
                for k, v in request.cookies.items()
            ]
            await page.context.add_cookies(cookies)

    # ---- 自动滚动 ----

    def _should_auto_scroll(self, request) -> bool:
        return request.meta.get("cloakbrowser_auto_scroll", self.auto_scroll)

    async def _auto_scroll_page(self, page, request):
        scroll_delay = request.meta.get("cloakbrowser_scroll_delay", self.scroll_delay)
        max_no_content = request.meta.get("cloakbrowser_max_no_content", 2)

        try:
            consecutive_no_content = 0
            while True:
                current_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # humanize 模式下避免使用 wait_for_timeout（会发 CDP 命令，可被 reCAPTCHA 检测）
                time.sleep(scroll_delay / 1000)  # 使用 time.sleep 代替
                new_height = await page.evaluate("document.body.scrollHeight")

                if new_height > current_height:
                    consecutive_no_content = 0
                else:
                    consecutive_no_content += 1
                    if consecutive_no_content >= max_no_content:
                        break
                if consecutive_no_content > 10:
                    break
        except Exception as e:
            self.logger.warning(f"Auto scroll failed: {e}")

    # ---- 自定义操作 ----

    async def _execute_custom_actions(self, page, request):
        """复用 PageActionHandler 通用操作接口"""
        custom_actions = PageActionHandler.get_actions_from_request(request)

        if custom_actions:
            self.logger.info(f"Executing {len(custom_actions)} custom action(s)...")

        for i, action in enumerate(custom_actions, 1):
            try:
                if not isinstance(action, dict):
                    continue

                action_type = action.get("type")
                action_params = action.get("params", {})

                self.logger.info(f"  [{i}/{len(custom_actions)}] Executing: {action_type}")

                if action_type == "scroll_to_bottom":
                    await self._scroll_to_bottom(page, action_params)
                elif action_type == "click":
                    selector = PageActionHandler.extract_selector(action)
                    if selector:
                        await self._click_with_selector(page, selector)
                        await page.wait_for_timeout(action_params.get("wait_timeout", 1000))
                elif action_type == "click_and_wait":
                    selector = PageActionHandler.extract_selector(action)
                    if selector:
                        await self._click_with_selector(page, selector)
                        wait_for = action_params.get("wait_for", "networkidle")
                        if wait_for == "networkidle":
                            await page.wait_for_load_state("networkidle")
                        else:
                            await page.wait_for_timeout(action_params.get("wait_timeout", 2000))
                elif action_type == "fill":
                    selector = PageActionHandler.extract_selector(action)
                    value = action_params.get("value")
                    if selector and value is not None:
                        await self._fill_with_selector(page, selector, value)
                elif action_type == "wait":
                    # humanize 模式下避免使用 wait_for_timeout
                    timeout = action_params.get("timeout", 1000)
                    time.sleep(timeout / 1000)  # 使用 time.sleep 代替
                elif action_type == "evaluate":
                    script = action_params.get("script")
                    if script:
                        await page.evaluate(script)
                elif action_type == "scroll":
                    position = action_params.get("position", "bottom")
                    if position == "bottom":
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    elif position == "top":
                        await page.evaluate("window.scrollTo(0, 0)")

            except Exception as e:
                self.logger.warning(f"  Failed to execute action {i} ({action.get('type', '?')}): {e}")

    async def _click_with_selector(self, page, selector: str):
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        if selector_type == "xpath":
            await page.locator(f"xpath={clean_selector}").click()
        else:
            await page.click(clean_selector)

    async def _fill_with_selector(self, page, selector: str, value: str):
        selector_type, clean_selector = SelectorConverter.normalize_selector(selector)
        if selector_type == "xpath":
            await page.locator(f"xpath={clean_selector}").fill(value)
        else:
            await page.fill(clean_selector, value)

    async def _scroll_to_bottom(self, page, params: dict):
        scroll_delay = params.get("scroll_delay", self.scroll_delay)
        max_no_content = params.get("max_no_content", 2)
        max_scrolls = params.get("max_scrolls", 50)

        try:
            consecutive_no_content = 0
            scroll_count = 0
            while scroll_count < max_scrolls:
                scroll_count += 1
                current_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                # humanize 模式下避免使用 wait_for_timeout
                time.sleep(scroll_delay / 1000)  # 使用 time.sleep 代替
                new_height = await page.evaluate("document.body.scrollHeight")

                if new_height > current_height:
                    consecutive_no_content = 0
                else:
                    consecutive_no_content += 1
                    if consecutive_no_content >= max_no_content:
                        break
                if consecutive_no_content > 10:
                    break
        except Exception as e:
            self.logger.warning(f"Scroll to bottom failed: {e}")

    # ---- 翻页操作 ----

    async def _execute_pagination_actions(self, page, request):
        pagination_actions = request.meta.get("pagination_actions", [])

        for action in pagination_actions:
            try:
                if not isinstance(action, dict):
                    continue
                action_type = action.get("type")
                params = action.get("params", {})

                if action_type == "scroll":
                    for _ in range(params.get("count", 1)):
                        await page.mouse.wheel(0, params.get("distance", 500))
                        # humanize 模式下避免使用 wait_for_timeout
                        time.sleep(params.get("delay", 1000) / 1000)  # 使用 time.sleep 代替
                elif action_type == "click":
                    selector = params.get("selector")
                    if selector:
                        for _ in range(params.get("count", 1)):
                            await page.click(selector)
                            # humanize 模式下避免使用 wait_for_timeout
                            time.sleep(params.get("delay", 1000) / 1000)  # 使用 time.sleep 代替
                elif action_type == "evaluate":
                    script = params.get("script")
                    if script:
                        await page.evaluate(script)
            except Exception as e:
                self.logger.warning(f"Failed to execute pagination action: {e}")

    # ---- Cookies ----

    async def _get_cookies(self) -> Dict[str, str]:
        try:
            if self._context:
                cookies = await self._context.cookies()
                return {c['name']: c['value'] for c in cookies}
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
            return {}

    # ---- 资源关闭 ----

    async def close(self) -> None:
        self.logger.info("Closing CloakBrowserDownloader...")

        # 关闭页面池
        for page in self._page_pool:
            try:
                await page.close()
            except Exception:
                pass
        self._page_pool.clear()
        self._used_pages.clear()

        # 关闭上下文
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            finally:
                self._context = None

        # 关闭浏览器（持久化模式无独立 browser）
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            finally:
                self._browser = None

        self.logger.info("CloakBrowserDownloader closed successfully")
```

---

## 九、测试计划

| 测试项 | 方法 |
|--------|------|
| 导入检测 | `pip install cloakbrowser` 后验证 `from cloakbrowser import launch_async` |
| 基础启动 | 无配置启动，验证页面导航和内容获取 |
| headless 模式 | 验证有头/无头模式切换 |
| 代理配置 | 验证 HTTP/SOCKS5 代理字符串和字典格式 |
| humanize | 验证类人行为开启/关闭 |
| geoip | 验证带代理时自动检测时区 |
| 指纹种子 | 验证固定种子跨启动一致 |
| 页面池 | 验证多标签页复用和信号量控制 |
| 资源屏蔽 | 验证 route 拦截图片/字体/媒体 |
| 自定义操作 | 验证 click/fill/wait/evaluate/scroll 操作 |
| 混合下载器集成 | 验证 HybridDownloader 识别 `"cloakbrowser"` 类型 |
| 持久化上下文 | 验证跨运行 cookie 保持 |
| 异常恢复 | 验证浏览器崩溃后重新初始化 |
| 资源释放 | 验证 close() 完全释放所有资源 |
