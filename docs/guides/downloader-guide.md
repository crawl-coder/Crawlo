# 下载器选择与使用指南

Crawlo 提供了多种下载器，覆盖从简单静态页面到高强度反爬站点的全场景需求。本文帮你快速选型并上手。

---

## 下载器总览

| 下载器 | 类型 | 反检测能力 | 速度 | 内存占用 | 适用场景 |
|--------|------|-----------|------|---------|---------|
| **AioHttpDownloader** | 协议 | 无 | 最快 | 极低 | 静态页面、API 接口 |
| **HttpXDownloader** | 协议 | 无 | 最快 | 极低 | 同上，HTTP/2 支持 |
| **CurlCffiDownloader** | 协议 | TLS 指纹模拟 | 快 | 低 | 有 TLS 指纹检测的 API |
| **PlaywrightDownloader** | 浏览器 | JS 注入（基础） | 中 | 中 | JS 渲染页面 |
| **DrissionPageDownloader** | 浏览器 | JS 注入（基础） | 中 | 中 | 简单动态页面 |
| **CamoufoxDownloader** | 浏览器 | C++ 补丁（Firefox） | 中慢 | 中高 | 中度反爬站点 |
| **CloakBrowserDownloader** | 浏览器 | C++ 补丁（Chromium） | 中慢 | 高 | 高强度反爬站点 |

---

## 如何选择下载器

```
目标页面需要 JS 渲染吗？
├── 否 → 使用协议下载器（AioHttp / HttpX）
│         └── 有 TLS 指纹检测？→ CurlCffi
│
└── 是 → 站点有反爬检测吗？
          ├── 无/弱 → PlaywrightDownloader（最轻量）
          ├── 中度 → CamoufoxDownloader（Firefox 反检测）
          └── 强（Cloudflare/reCAPTCHA）→ CloakBrowserDownloader（最强）
```

---

## 混合下载器 (HybridDownloader)

**推荐方式**：使用 HybridDownloader 自动在协议和浏览器下载器间智能切换，无需手动判断。

```python
# settings.py
DOWNLOADER = 'crawlo.downloader.hybrid_downloader.HybridDownloader'
```

### 工作原理

HybridDownloader 维护两类下载器：
- **协议下载器**：aiohttp / httpx / curl_cffi，处理静态页面
- **动态下载器**：Playwright / Camoufox / CloakBrowser，处理 JS 渲染页面

### 自动路由规则

1. **请求级标记**：`request.meta['use_dynamic_loader'] = True` → 使用动态下载器
2. **域名规则**：`HYBRID_DYNAMIC_DOMAINS` 列表中的域名 → 自动走动态下载器
3. **URL 模式**：`HYBRID_DYNAMIC_URL_PATTERNS` 匹配的 URL → 自动走动态下载器
4. **默认**：其余请求走协议下载器

### 配置示例

```python
# settings.py
DOWNLOADER = 'crawlo.downloader.hybrid_downloader.HybridDownloader'

# 默认协议下载器
HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = 'httpx'

# 默认动态下载器
HYBRID_DEFAULT_DYNAMIC_DOWNLOADER = 'playwright'  # 或 'camoufox' / 'cloakbrowser'

# 特定域名自动走浏览器
HYBRID_DYNAMIC_DOMAINS = ['www.cloudflare-site.com', 'spa.example.com']

# URL 正则匹配
HYBRID_DYNAMIC_URL_PATTERNS = [r'.*/captcha.*', r'.*/dashboard.*']
```

### 请求级控制

```python
from crawlo import Request

# 强制使用浏览器
yield Request(
    url='https://example.com/spa-page',
    meta={'use_dynamic_loader': True}
)

# 强制使用特定动态下载器
yield Request(
    url='https://high-protection-site.com',
    meta={
        'use_dynamic_loader': True,
        'dynamic_downloader': 'cloakbrowser',  # 指定下载器
    }
)
```

---

## 协议下载器

### AioHttpDownloader（默认）

最轻量的下载器，适合绝大多数静态页面。

```python
# settings.py — 默认已启用，无需额外配置
DOWNLOADER = 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader'
```

### HttpXDownloader

与 aiohttp 类似，额外支持 HTTP/2。

```python
DOWNLOADER = 'crawlo.downloader.httpx_downloader.HttpXDownloader'
```

### CurlCffiDownloader

模拟浏览器 TLS 指纹，绕过基于 TLS 的检测。

```bash
pip install crawlo[curl]
```

```python
DOWNLOADER = 'crawlo.downloader.curl_cffi_downloader.CurlCffiDownloader'
```

---

## 浏览器下载器

### PlaywrightDownloader

基础浏览器渲染下载器，适合需要 JS 渲染但无强反爬的站点。

```bash
pip install crawlo[render]
playwright install chromium
```

```python
# settings.py
DOWNLOADER = 'crawlo.downloader.playwright_downloader.PlaywrightDownloader'

PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_BLOCK_RESOURCES = ['image', 'font', 'media']  # 加速加载
PLAYWRIGHT_STEALTH_LEVEL = 'basic'  # 基础反检测
```

**请求级控制**：

```python
yield Request(
    url='https://spa-site.com/page',
    meta={
        'use_dynamic_loader': True,
        'playwright_headless': False,
        'playwright_wait_strategy': 'networkidle',
        'dynamic_actions': [
            {'type': 'click', 'selector': '#load-more'},
            {'type': 'scroll_to_bottom', 'params': {'max_no_content': 3}},
        ]
    }
)
```

### CamoufoxDownloader

基于 Firefox C++ 补丁的反检测浏览器，适合中度反爬站点。

```bash
pip install crawlo[camoufox]
```

```python
DOWNLOADER = 'crawlo.downloader.camoufox_downloader.CamoufoxDownloader'
```

### CloakBrowserDownloader

基于 Chromium C++ 补丁的顶级反检测浏览器。适合 Cloudflare、reCAPTCHA v3 等高强度反爬站点。

详见 → [CloakBrowser 使用指南](cloakbrowser-guide.md)

---

## 通用请求级操作

所有浏览器下载器（Playwright / Camoufox / CloakBrowser）共享以下请求级 `meta` 配置：

### 等待策略

| 值 | 说明 |
|----|------|
| `auto` | 自动判断（默认） |
| `networkidle` | 等待网络空闲 |
| `domcontentloaded` | DOM 加载完成即返回 |

```python
meta={'cloakbrowser_wait_strategy': 'networkidle'}  # CloakBrowser
meta={'playwright_wait_strategy': 'networkidle'}     # Playwright
```

### 资源屏蔽

屏蔽不需要的资源可以显著加速页面加载：

```python
meta={'cloakbrowser_block_resources': ['image', 'font', 'media', 'stylesheet']}
```

### 页面操作 (dynamic_actions)

所有浏览器下载器共享统一的页面操作接口：

```python
meta={
    'dynamic_actions': [
        # 等待
        {'type': 'wait', 'params': {'timeout': 3000}},
        # 点击
        {'type': 'click', 'selector': '#accept-cookies'},
        # 点击后等待网络空闲
        {'type': 'click_and_wait', 'selector': '#load-more', 'params': {'wait_for': 'networkidle'}},
        # 填写表单
        {'type': 'fill', 'selector': '#search-input', 'params': {'value': '关键词'}},
        # 滚动到底部
        {'type': 'scroll_to_bottom', 'params': {'scroll_delay': 500, 'max_no_content': 3}},
        # 滚动到指定位置
        {'type': 'scroll', 'params': {'position': 'bottom'}},
        # 执行 JavaScript
        {'type': 'evaluate', 'params': {'script': 'window.scrollTo(0, document.body.scrollHeight)'}},
    ]
}
```

### 翻页操作 (pagination_actions)

```python
meta={
    'pagination_actions': [
        {'type': 'scroll', 'params': {'count': 3, 'distance': 500, 'delay': 1000}},
        {'type': 'click', 'params': {'selector': '.next-page', 'count': 2, 'delay': 2000}},
        {'type': 'evaluate', 'params': {'script': 'loadNextPage()'}},
    ]
}
```

---

## 常见问题

### Q: 协议下载器和浏览器下载器可以混用吗？

**可以**。使用 HybridDownloader 即可自动路由，也可以在请求中通过 `meta['use_dynamic_loader']` 手动控制。

### Q: 浏览器下载器占用内存太大怎么办？

1. 减小 `MAX_PAGES` 限制标签页数量
2. 启用 `BLOCK_RESOURCES` 屏蔽图片/字体等
3. 仅对需要 JS 渲染的 URL 使用浏览器下载器

### Q: Playwright 被检测了怎么办？

逐步升级：Playwright → Camoufox → CloakBrowser。详见 [CloakBrowser 使用指南](cloakbrowser-guide.md)。

---

## 相关文档

- [CloakBrowser 使用指南](cloakbrowser-guide.md) — 高强度反爬专用下载器
- [配置指南](configuration/index.md) — 全局配置详解
- [核心组件](../concepts/core-components.md) — 框架组件概述
