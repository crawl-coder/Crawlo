# 核心组件详解

本章节详细介绍 Crawlo 框架中各个核心组件的功能、配置及最佳实践。

## 1. 下载器 (Downloader)

下载器负责实际的网络通信。Crawlo 推荐使用 **HybridDownloader**（混合下载器），自动在协议和浏览器下载器间智能切换。

### 下载器类型

| 类型 | 下载器 | 适用场景 |
|------|--------|---------|
| **协议** | AioHttp / HttpX / CurlCffi | 静态页面、API 接口 |
| **浏览器** | Playwright | JS 渲染页面 |
| **浏览器** | Camoufox | 中度反爬站点（Firefox 补丁） |
| **浏览器** | **CloakBrowser** | 高强度反爬站点（Chromium 补丁） |

### 混合模式 (Hybrid)

混合下载器根据请求特征自动选择下载器：
- **协议下载器**（aiohttp / httpx / curl_cffi）：处理静态页面，速度最快
- **动态下载器**（Playwright / Camoufox / CloakBrowser）：处理 JS 渲染页面

路由规则：
1. `request.meta['use_dynamic_loader'] = True` → 使用动态下载器
2. `HYBRID_DYNAMIC_DOMAINS` 中的域名 → 自动走动态下载器
3. `HYBRID_DYNAMIC_URL_PATTERNS` 匹配的 URL → 自动走动态下载器
4. 其余 → 走协议下载器

详见 [下载器选择与使用指南](../guides/downloader-guide.md)。

### 关键配置
- `DOWNLOAD_TIMEOUT`: 请求超时时间。
- `CONCURRENCY`: 并发连接数限制。
- `DOWNLOAD_DELAY`: 请求间隔延迟（用于限速）。
- `HYBRID_DEFAULT_DYNAMIC_DOWNLOADER`: 默认动态下载器（`playwright` / `camoufox` / `cloakbrowser`）。

---

## 2. 调度器 (Scheduler) 与 队列

调度器管理待抓取的 URL，负责优先级排序和去重。

- **去重 (Filter)**：内置多种指纹算法，确保同一 URL 不会被重复抓取。
- **优先级 (Priority)**：支持设置请求优先级，紧急数据优先获取。用户设置 `priority` 时数值越大越优先，框架内部自动取反存储（min-heap 机制）。
- **Depth 自动传播**：框架自动为子请求传播 `depth`（`子请求.depth = 父请求.depth + 1`），无需用户手动管理。
- **调度策略**：通过 `DEPTH_PRIORITY` 配置项控制深度优先/广度优先策略。
- **存储后端**：支持内存（Memory）和 Redis 后端。

### Depth 自动传播机制

框架在 Engine 层面自动传播请求深度，无需用户在 Spider 中手动设置 `meta['depth']`：

1. `start_requests` 产生的请求：`depth` 默认为 1
2. Spider 回调产生的子请求：`depth` 自动设为 `parent_request.depth + 1`
3. Errback 产生的请求：同样自动传播 `depth`

### 优先级与调度策略

| 配置值 | 策略 | 效果 | 适用场景 |
|--------|------|------|---------|
| `DEPTH_PRIORITY = 1`（默认） | 深度优先 | 详情页优先出队，列表页解析后立即处理详情 | 列表→详情型爬虫，避免"先列后详" |
| `DEPTH_PRIORITY = -1` | 广度优先 | 列表页优先出队，同层级请求先处理完 | 逐层抓取，确保层级完整 |
| `DEPTH_PRIORITY = 0` | 不调整 | 不按深度调整优先级，纯按用户设置的 priority 排序 | 自定义优先级策略 |

> **优先级计算公式**：`内部 priority = -用户priority - depth × DEPTH_PRIORITY`
>
> 用户传入 `priority=100` → 内部存储 `-100`；再经 depth 调整后，深度越深优先级变化越大。

---

## 3. 中间件 (Middleware)

中间件采用**洋葱模型**设计，具有明确的优先级执行顺序。

### 执行顺序
- **请求阶段**：按优先级数值从小到大执行。
- **响应阶段**：按优先级数值从大到小执行（LIFO）。

### 内置中间件
- `RetryMiddleware`: 自动错误重试。
- `ProxyMiddleware`: 动态代理切换。
- `UserAgentMiddleware`: 随机 UA 注入。
- `CloudflareBypass`: 自动检测并绕过 Cloudflare 挑战。

---

## 4. 管道 (Pipeline)

管道用于处理爬虫提取出的 Item。

### 数据存储
Crawlo 内置了多种持久化支持：
- **MySQL**: 异步连接池支持（`asyncmy`）。
- **MongoDB**: 异步驱动支持（`motor`）。
- **JSON / CSV**: 本地文件序列化。

### 去重管道
支持在存储层执行 Item 去重，防止数据库出现重复记录。

---

## 5. 爬虫 (Spider)

爬虫是编写业务逻辑的核心。

### 生命周期
- `start_requests()`: 生成初始请求。
- `parse(response)`: 默认回调函数，解析网页并提取数据。
- `closed(reason)`: 爬虫关闭时的清理回调。
