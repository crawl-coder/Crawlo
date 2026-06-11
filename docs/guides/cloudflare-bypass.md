# Cloudflare 绕过指南

> 自动检测 Cloudflare 挑战 → 切换到隐身浏览器 → 透明绕过，无需手动干预。

## 概述

Crawlo 通过 `CloudflareBypassMiddleware` 自动检测 Cloudflare 的 JS Challenge / Turnstile / CAPTCHA 页面，并切换到隐身浏览器（CloakBrowser / Camoufox / Playwright）完成绕过。整个过程对爬虫代码透明。

## 快速开启

```python
# settings.py
CLOUDFLARE_BYPASS_ENABLED = True
CLOUDFLARE_BYPASS_DOWNLOADER = 'cloakbrowser'   # 推荐
```

## 原理

```
普通请求 → AioHttp/HttpX 下载器
    ↓
Cloudflare 挑战页面被检测到
    ↓
CloudflareBypassMiddleware 拦截
    ↓
切换请求到隐身浏览器（CloakBrowser/Camoufox/Playwright）
    ↓
浏览器完成 JS Challenge / Turnstile 验证
    ↓
获取 cookies，后续请求携带 cookies，回到普通下载器
```

### 检测标识

中间件通过以下特征识别 Cloudflare 挑战页面：
- HTTP 状态码 403/503
- 页面标题含 "Just a moment" 或 "Checking your browser"
- HTML 包含 `cf-challenge` / `challenge-platform` / `turnstile` 特征串

## 配置

```python
# settings.py
CLOUDFLARE_BYPASS_ENABLED = True
CLOUDFLARE_BYPASS_MAX_RETRIES = 2       # 单 URL 最多绕过尝试次数
CLOUDFLARE_BYPASS_DOWNLOADER = 'cloakbrowser'  # 或: camoufox / playwright
CLOUDFLARE_BYPASS_TIMEOUT = 60000       # 绕过等待超时（毫秒）
```

## 支持的隐身浏览器

| 下载器 | 特点 | 推荐场景 |
|--------|------|---------|
| **CloakBrowser** | 57 项 C++ 补丁，深度反检测 | 强对抗 Cloudflare reCAPTCHA/Turnstile |
| **Camoufox** | Firefox 内核，指纹随机化 | JS Challenge、中等防护 |
| **Playwright** | Chromium 内核，stealth 模式 | 轻量防护、快速绕过 |

## 使用示例

### 全站自动绕过

```python
# settings.py
CLOUDFLARE_BYPASS_ENABLED = True
CLOUDFLARE_BYPASS_DOWNLOADER = 'cloakbrowser'
```

### 指定域名绕过

```python
CLOUDFLARE_BYPASS_DOMAIN_PATTERNS = [
    'cloudflare-protected-site.com',
    '*.cdn.example.com',
]
# 仅匹配这些域名的请求启用绕过
```

### 手动触发绕过

```python
# spider.py
yield Request(
    url='https://protected-site.com',
    meta={'cloudflare_bypass': True},   # 强制绕过
    callback=self.parse,
)
```

## 与 HybridDownloader 协同

当使用 HybridDownloader 时，绕过逻辑更加智能：

```python
DOWNLOADER = 'crawlo.downloader.HybridDownloader'
CLOUDFLARE_BYPASS_DOWNLOADER = 'cloakbrowser'

# 流程：
# 1. HybridDownloader 先用 AioHttp 发送请求
# 2. 检测到 Cloudflare → 中间件拦截
# 3. 自动切换到 CloakBrowser 完成验证
# 4. 验证通过后，后续请求继续用 AioHttp（携带 cookies）
```

## 性能建议

- CloakBrowser/Camoufox 启动有开销（1-3 秒），建议复用浏览器实例
- 验证通过获取的 cookies 有效期内可跳过后续绕过
- 对静态资源（image/font/css）请求设置 `dont_filter=True` 但跳过绕过

```python
BROWSER_MAX_PAGES = 10                  # 浏览器最大页面数，复用实例
CLOUDFLARE_BYPASS_MAX_RETRIES = 2      # 减少无效等待
```

## 故障排查

| 现象 | 可能原因 | 解决 |
|------|---------|------|
| 一直绕不过 | 下载器不可用或不兼容 | 安装 CloakBrowser 或 Camoufox |
| 绕过耗时过长 | 网络慢或验证复杂 | 调大 `CLOUDFLARE_BYPASS_TIMEOUT` |
| 绕过失败返回 403 | IP 被标记 | 配合代理使用，切换 IP |
| 浏览器内存溢出 | 实例过多 | 调小 `BROWSER_MAX_PAGES` |
