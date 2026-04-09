# 智能混合下载器 (HybridDownloader)

`HybridDownloader` 是 Crawlo 框架推荐的默认下载器。它充当一个智能调度层，能够根据请求的特性自动在高性能协议下载器与功能强大的浏览器渲染下载器之间进行切换。

## 核心设计理念

在复杂的爬虫项目中，通常会同时遇到两类页面：
1. **静态页面**：可以通过 `aiohttp` 或 `httpx` 快速下载，资源消耗极低。
2. **动态页面**：需要 JavaScript 渲染（如 SPA 应用）或有极强的反爬措施，必须使用 `Playwright` 或 `Camoufox`。

`HybridDownloader` 的目标是**性能与通过率的完美平衡**：默认使用最快的协议下载，仅在必要时才“降级”到浏览器渲染。

## 工作原理

`HybridDownloader` 遵循以下优先级逻辑来决定使用哪种底层引擎：

1. **Request Meta 标记**：如果 `request.meta` 中显式设置了 `use_dynamic_loader: True`，则强制使用动态下载器。
2. **URL 正则匹配**：检查 URL 是否匹配 `HYBRID_DYNAMIC_URL_PATTERNS` 配置。
3. **域名匹配**：检查 URL 的域名是否在 `HYBRID_DYNAMIC_DOMAINS` 列表中。
4. **文件后缀过滤**：自动识别并对图片、CSS、JS 等静态资源使用协议下载器。
5. **默认策略**：若以上均未命中，则使用 `HYBRID_DEFAULT_PROTOCOL_DOWNLOADER` 指定的协议下载器。

## 配置参考

在 `settings.py` 中进行配置：

```python
# 启用混合下载器（默认已启用）
DOWNLOADER = "crawlo.downloader.hybrid_downloader.HybridDownloader"

# 设置默认协议引擎 (httpx, aiohttp, curl_cffi)
HYBRID_DEFAULT_PROTOCOL_DOWNLOADER = "httpx"

# 配置需要动态渲染的域名
HYBRID_DYNAMIC_DOMAINS = [
    "example-spa.com",
    "protected-site.org"
]

# 配置需要动态渲染的 URL 正则模式
HYBRID_DYNAMIC_URL_PATTERNS = [
    r"/api/v\d+/data",
    r".*\?render=true"
]

# 配置强制使用协议下载的模式
HYBRID_PROTOCOL_URL_PATTERNS = [
    r"/static/.*",
    r"\.json$"
]
```

## 性能优化特性

- **延迟加载 (Lazy Loading)**：底层引擎（如 Playwright）仅在首次需要执行动态下载时才会初始化，避免了不必要的启动开销。
- **正则预编译**：所有 URL 模式在初始化时预编译，确保高并发下的匹配效率。
- **资源屏蔽**：配合 `PlaywrightDownloader` 自动屏蔽图片、字体等无关资源，加快渲染速度。

## 与中间件的协作

`HybridDownloader` 通常与 `DynamicRenderMiddleware` 配合使用。中间件负责根据规则在 `request.meta` 中打上标记，而 `HybridDownloader` 负责执行最终的选择逻辑。这种分层设计确保了逻辑判断与下载执行的深度解耦。
