# CloakBrowser 下载器使用指南

CloakBrowser 是源码级修补的 Chromium 浏览器，通过 57 项 C++ 补丁修改指纹特征，可绕过 Cloudflare Turnstile、reCAPTCHA v3（0.9+ 评分）、FingerprintJS 等主流反爬系统。

> **何时选用 CloakBrowser？** 当 Playwright 或 Camoufox 被站点检测拦截时，升级到 CloakBrowser。详见 [下载器选择指南](downloader-guide.md)。

---

## 快速开始

### 1. 安装

```bash
# 推荐：通过 Crawlo 安装
pip install crawlo[stealth]

# 或独立安装
pip install cloakbrowser[geoip]
```

> 首次运行时 CloakBrowser 会自动下载 Chromium 二进制（约 200MB），缓存至 `~/.cloakbrowser/`。

### 2. 配置

```python
# settings.py

# 方式 A：独立使用
DOWNLOADER = 'crawlo.downloader.cloakbrowser_downloader.CloakBrowserDownloader'

# 方式 B：通过 HybridDownloader 使用（推荐）
DOWNLOADER = 'crawlo.downloader.hybrid_downloader.HybridDownloader'
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = 'cloakbrowser'
```

### 3. 编写爬虫

```python
from crawlo import Spider, Request

class MySpider(Spider):
    name = 'my_spider'

    def start_requests(self):
        yield Request(
            url='https://protected-site.com/page',
            meta={'use_dynamic_loader': True}
        )

    def parse(self, response):
        title = response.xpath('//title/text()').get()
        yield {'url': response.url, 'title': title}
```

---

## 核心配置

按场景分组，复制即可使用。

### 基础场景

```python
CLOAKBROWSER_HEADLESS = True          # 无头模式
CLOAKBROWSER_TIMEOUT = 30000          # 总超时（毫秒）
CLOAKBROWSER_MAX_PAGES = 10           # 最大标签页数
CLOAKBROWSER_BLOCK_RESOURCES = ['image', 'font', 'media']  # 加速加载
```

### 高对抗场景

Cloudflare / reCAPTCHA / DataDome 等强反爬站点：

```python
CLOAKBROWSER_HEADLESS = False         # 有头模式（高强度站点建议开启）
CLOAKBROWSER_HUMANIZE = True          # 类人鼠标/键盘/滚动行为
CLOAKBROWSER_HUMAN_PRESET = 'careful' # 审慎模式（更慢但更安全）
CLOAKBROWSER_GEOIP = True             # 根据代理 IP 自动匹配时区
CLOAKBROWSER_PROXY = 'socks5://user:pass@proxy:1080'  # 住宅代理
CLOAKBROWSER_FINGERPRINT = 42069      # 固定指纹种子（跨运行保持一致）
```

### 性能优化场景

不需要反检测，只需要 JS 渲染：

```python
CLOAKBROWSER_HEADLESS = True
CLOAKBROWSER_HUMANIZE = False
CLOAKBROWSER_BLOCK_RESOURCES = ['image', 'font', 'media', 'stylesheet']
CLOAKBROWSER_WAIT_STRATEGY = 'domcontentloaded'  # 更快返回
CLOAKBROWSER_TIMEOUT = 15000
```

### 持久化会话

保持登录状态、Cookie 跨运行保留：

```python
CLOAKBROWSER_PERSISTENT_CONTEXT = True
CLOAKBROWSER_USER_DATA_DIR = './browser_data/my_session'
CLOAKBROWSER_FINGERPRINT = 12345      # 固定指纹保持身份一致
```

---

## 全部配置项

### 基础设置

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `CLOAKBROWSER_HEADLESS` | `True` | 无头模式。高强度站点建议 `False` |
| `CLOAKBROWSER_TIMEOUT` | `30000` | 默认超时（毫秒） |
| `CLOAKBROWSER_LOAD_TIMEOUT` | `10000` | 页面导航超时（毫秒） |
| `CLOAKBROWSER_MAX_PAGES` | `10` | 最大标签页数（控制并发和内存） |
| `CLOAKBROWSER_VIEWPORT_WIDTH` | `1280` | 视口宽度 |
| `CLOAKBROWSER_VIEWPORT_HEIGHT` | `720` | 视口高度 |

### 反检测设置

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `CLOAKBROWSER_HUMANIZE` | `False` | 类人行为模拟（鼠标/键盘/滚动） |
| `CLOAKBROWSER_HUMAN_PRESET` | `"default"` | 预设：`"default"` 或 `"careful"` |
| `CLOAKBROWSER_HUMAN_CONFIG` | `None` | 自定义人化配置（dict） |
| `CLOAKBROWSER_GEOIP` | `False` | 从代理 IP 自动检测时区和语言 |
| `CLOAKBROWSER_STEALTH_ARGS` | `True` | 启用默认隐身参数 |
| `CLOAKBROWSER_FINGERPRINT` | `None` | 固定指纹种子（int/str），用于会话持久化 |
| `CLOAKBROWSER_FINGERPRINT_PLATFORM` | `None` | 指纹平台：`"windows"` / `"macos"` / `"linux"` |
| `CLOAKBROWSER_BACKEND` | `"playwright"` | 后端：`"playwright"` 或 `"patchright"` |

### 代理设置

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `CLOAKBROWSER_PROXY` | `None` | 代理地址，支持 HTTP/SOCKS5 |
| `PROXY_API_URL` | `None` | 代理 API 地址，自动获取代理 |

### 性能设置

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `CLOAKBROWSER_BLOCK_RESOURCES` | `["image","font","media"]` | 屏蔽的资源类型 |
| `CLOAKBROWSER_AUTO_SCROLL` | `False` | 自动滚动到页面底部 |
| `CLOAKBROWSER_SCROLL_DELAY` | `500` | 滚动延迟（毫秒） |
| `CLOAKBROWSER_WAIT_STRATEGY` | `"auto"` | 等待策略：`"auto"` / `"networkidle"` / `"domcontentloaded"` |
| `CLOAKBROWSER_WAIT_TIMEOUT` | `10000` | 等待超时（毫秒） |

### 持久化设置

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `CLOAKBROWSER_PERSISTENT_CONTEXT` | `False` | 使用持久化浏览器上下文 |
| `CLOAKBROWSER_USER_DATA_DIR` | `None` | 持久化数据目录路径 |

### 高级设置

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `CLOAKBROWSER_ARGS` | `[]` | 额外 Chromium 命令行参数 |
| `CLOAKBROWSER_TIMEZONE` | `None` | 手动时区（如 `"America/New_York"`） |
| `CLOAKBROWSER_LOCALE` | `None` | 手动语言区域（如 `"en-US"`） |

---

## 请求级控制

所有全局配置均可在单个请求中通过 `meta` 覆盖，前缀为 `cloakbrowser_`：

```python
yield Request(
    url='https://high-protection-site.com/page',
    meta={
        'use_dynamic_loader': True,

        # 覆盖全局配置
        'cloakbrowser_headless': False,
        'cloakbrowser_humanize': True,
        'cloakbrowser_wait_strategy': 'networkidle',
        'cloakbrowser_auto_scroll': True,
        'cloakbrowser_block_resources': ['image', 'font'],

        # 页面操作
        'dynamic_actions': [
            {'type': 'wait', 'params': {'timeout': 3000}},
            {'type': 'click', 'selector': '#accept-cookies'},
            {'type': 'scroll_to_bottom', 'params': {'max_no_content': 3}},
        ]
    }
)
```

### 代理请求级配置

```python
yield Request(
    url='https://example.com',
    meta={
        'use_dynamic_loader': True,
        'cloakbrowser_proxy': 'http://user:pass@ip:port',
    }
)
```

---

## 使用示例

### 示例 1：采集 Cloudflare 保护站点

```python
class CloudflareSpider(Spider):
    name = 'cf_spider'

    def start_requests(self):
        yield Request(
            url='https://cloudflare-protected.com/data',
            meta={'use_dynamic_loader': True}
        )

    def parse(self, response):
        for item in response.css('.data-item'):
            yield {'text': item.css('::text').get()}
```

配合 settings.py：
```python
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = 'cloakbrowser'
CLOAKBROWSER_HUMANIZE = True
CLOAKBROWSER_GEOIP = True
CLOAKBROWSER_PROXY = 'socks5://user:pass@residential-proxy:1080'
```

### 示例 2：自动滚动 + 点击加载更多

```python
class InfiniteScrollSpider(Spider):
    name = 'scroll_spider'

    def start_requests(self):
        yield Request(
            url='https://example.com/infinite-scroll',
            meta={
                'use_dynamic_loader': True,
                'cloakbrowser_auto_scroll': True,
                'dynamic_actions': [
                    {'type': 'click', 'selector': '#load-more'},
                    {'type': 'scroll_to_bottom', 'params': {'max_no_content': 3}},
                ]
            }
        )
```

### 示例 3：保持登录状态

```python
# settings.py
CLOAKBROWSER_PERSISTENT_CONTEXT = True
CLOAKBROWSER_USER_DATA_DIR = './browser_data/logged_in'
CLOAKBROWSER_FINGERPRINT = 12345

# 首次运行：手动登录（设置 HEADLESS=False）
# 后续运行：自动保持登录状态
```

### 示例 4：批量采集 + 请求级代理

```python
class BatchSpider(Spider):
    name = 'batch_spider'

    def start_requests(self):
        targets = ['小米科技', '华为技术', '阿里巴巴']
        for name in targets:
            yield Request(
                url=f'https://baike.baidu.com/item/{name}',
                meta={
                    'use_dynamic_loader': True,
                    'cloakbrowser_block_resources': ['image', 'font'],
                }
            )
```

---

## 与其他下载器对比

| 特性 | Playwright | Camoufox | **CloakBrowser** |
|------|-----------|----------|-----------------|
| 反检测层级 | JS 注入 | Firefox C++ 补丁 | **Chromium C++ 补丁** |
| reCAPTCHA v3 分数 | 0.3-0.5 | 中高 | **0.9+** |
| Cloudflare 绕过 | 不稳定 | 支持 | **原生支持** |
| 类人行为 | 无 | 内置 | **内置（更成熟）** |
| GeoIP 时区匹配 | 手动 | 无 | **自动检测** |
| 指纹持久化 | 不支持 | 不支持 | **种子固定** |
| 安装体积 | ~200MB | ~150MB | ~200MB |
| 内存占用 | ~200MB | ~250MB | ~280MB |

---

## 注意事项

### humanize 模式下的 API 使用

| 推荐 | 避免 | 原因 |
|------|------|------|
| `page.click(selector)` | `page.query_selector().click()` | ElementHandle 绕过人化管道 |
| `page.type(selector, text)` | `page.fill(selector, text)` | fill 是瞬时的，type 有键盘事件 |
| `time.sleep(3)` | `page.wait_for_timeout(3000)` | wait_for_timeout 发 CDP 命令，可被检测 |

### Patchright 后端限制

使用 `CLOAKBROWSER_BACKEND = 'patchright'` 时：
- 代理认证（username/password）会失效
- `add_init_script` 不可用
- 仅在默认后端 reCAPTCHA 分数仍低时使用

### macOS 首次启动

需要手动允许二进制执行：
```bash
xattr -cr ~/.cloakbrowser/chromium-*/Chromium.app
```

### macOS 指纹不一致

激进检测下 macOS 指纹可能不一致，建议切换到 Windows 指纹：
```python
CLOAKBROWSER_FINGERPRINT_PLATFORM = 'windows'
```

### 内存占用参考

| 状态 | 内存 |
|------|------|
| 空闲 | ~190 MB |
| 3 标签页 | ~280 MB |
| 每额外标签页 | ~30 MB |

---

## 首次下载 Chromium

CloakBrowser 首次运行时自动下载 Chromium（约 200MB）。如果下载超时或失败：

### 方案 1：使用代理

```powershell
$env:HTTP_PROXY = "http://your-proxy:port"
$env:HTTPS_PROXY = "http://your-proxy:port"
```

### 方案 2：手动下载

1. 访问 [GitHub Releases](https://github.com/CloakHQ/CloakBrowser/releases)
2. 下载对应平台压缩包（如 `cloakbrowser-windows-x64.zip`）
3. 解压到 `~/.cloakbrowser/`
4. 验证：`python -c "from cloakbrowser import launch; print('OK')"`

### 方案 3：指定浏览器路径

```python
# settings.py
CLOAKBROWSER_ARGS = ['--browser-path=D:/cloakbrowser/chrome.exe']
```

或设置环境变量：
```powershell
$env:CLOAKBROWSER_BROWSER_PATH = "D:\cloakbrowser\chrome.exe"
```

---

## 常见问题

### 提示 "cloakbrowser not installed"

```bash
pip install crawlo[stealth]
```

### 浏览器无法启动

1. 检查 Chromium 是否正确下载（`~/.cloakbrowser/` 目录）
2. 设置 `LOG_LEVEL = 'DEBUG'` 查看详细日志
3. 临时设为有头模式 `CLOAKBROWSER_HEADLESS = False` 观察浏览器行为

### 页面加载慢

```python
CLOAKBROWSER_BLOCK_RESOURCES = ['image', 'font', 'media', 'stylesheet']
CLOAKBROWSER_TIMEOUT = 20000
```

### 被反爬检测

逐步增强反检测配置：
```python
CLOAKBROWSER_HUMANIZE = True        # 启用类人行为
CLOAKBROWSER_GEOIP = True           # 时区自动匹配
CLOAKBROWSER_HEADLESS = False       # 有头模式
CLOAKBROWSER_PROXY = 'socks5://...' # 使用住宅代理
```

---

## 相关文档

- [下载器选择指南](downloader-guide.md) — 各下载器对比与选型
- [配置指南](configuration/index.md) — 全局配置详解
- [CloakBrowser 设计文档](../internal/cloakbrowser-design.md) — 内部架构（面向开发者）
- [CloakBrowser 官方网站](https://cloakbrowser.dev/)
