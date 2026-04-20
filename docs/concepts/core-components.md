# 核心组件详解

本章节详细介绍 Crawlo 框架中各个核心组件的功能、配置及最佳实践。

## 1. 下载器 (Downloader)

下载器负责实际的网络通信。Crawlo 推荐使用 **HybridDownloader**（混合下载器）。

### 混合模式 (Hybrid)
混合下载器可以在以下引擎间智能切换：
- **aiohttp / httpx**：用于高性能静态页面抓取。
- **Playwright / Camoufox**：用于处理 JS 渲染及高难度反爬。

### 关键配置
- `DOWNLOAD_TIMEOUT`: 请求超时时间。
- `CONCURRENCY`: 并发连接数限制。
- `DOWNLOAD_DELAY`: 请求间隔延迟（用于限速）。

---

## 2. 调度器 (Scheduler) 与 队列

调度器管理待抓取的 URL。

- **去重 (Filter)**：内置多种指纹算法，确保同一 URL 不会被重复抓取。
- **优先级 (Priority)**：支持设置请求优先级，紧急数据优先获取。
- **存储后端**：支持内存（Memory）和 Redis 后端。

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
