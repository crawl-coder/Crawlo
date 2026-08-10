# 什么时候用什么？——Crawlo 场景决策树

> Crawlo 的示例全部围绕**同一个网站**（[ee.ofweek.com](https://ee.ofweek.com/) 新闻目录站）
> 展开：`simple_quickstart` → `real_world_catalog` → `ofweek_standalone` →
> `ofweek_distributed`，从 23 行到分布式集群逐级加复杂度。
> 学一个网站 = 学会所有示例。

## 决策树

```text
我要抓取一个网站…
│
├─ 只是抓几十个页面、打印/存个文件？
│ └─ ▶ examples/simple_quickstart（23 行，无配置）
│
├─ 整站抓取：分页 + 详情 + 去重 + 结构化存储？
│ ├─ 先跑通：▶ examples/real_world_catalog（JSONL + 可选 MySQL）
│ └─ 要通知/健康检查：加 EXTENSIONS + NOTIFICATION_*（教程第 6 节）
│
├─ 网站反爬较强（动态渲染 / Cloudflare）？
│ └─ ▶ examples/infoq_dynamic_test（Playwright / CloakBrowser / Camoufox）
│
├─ 数据量大、需要多机横向扩展？
│ └─ ▶ examples/ofweek_distributed（Redis Stream + Worker 集群）
│
├─ 想复用功能给多个爬虫？
│ └─ ▶ examples/plugin_hello_world（注册中间件/管道/扩展）
│
└─ 让 AI 工具直接调爬虫？
 └─ ▶ examples/mcp_quickstart（MCP Server）
```

## 每个高级概念：什么时候需要 / 不需要

| 概念 | 什么时候需要 | 什么时候不需要 |
|---|---|---|
| **背压**（BACKPRESSURE_*） | 队列积压导致内存/Redis 压力大 | 小站点、短任务，默认配置即可 |
| **分布式**（redis_stream） | 单机并发不够 / 需要多机容错 | 单机几万页以内，分布式反而增加运维成本 |
| **浏览器渲染**（Playwright/Camoufox） | 目标站是 SPA / 有 JS 反爬 | 纯 HTML 站（如 ee.ofweek.com 列表页），httpx 就够 |
| **自适应选择器**（adaptive=True） | 长期运行的抓取，网站会改版 | 一次性任务、改版不频繁 |
| **MySQL/Mongo 管道**| 需要跨进程查询 / 长期存储 | 只要落盘分析，JSONL/CSV 足够 |
| **通知告警**| 生产环境长驻任务 | 本地开发调试 |
| **插件系统**| 多个项目共享组件 | 单个爬虫内直接用类 |
| **MCP**| 想让 Claude/Cursor 直接操作爬虫 | 纯代码工作流 |

## 复杂度阶梯（同一网站）

| 阶梯 | 示例 | 新增概念 |
|---|---|---|
| L0 | simple_quickstart（23 行） | Spider + 列表/详情解析 |
| L1 | real_world_catalog | 分页、去重、管道存储、监控 |
| L2 | ofweek_standalone | 工程化配置、通知、DB 管道 |
| L3 | ofweek_distributed | Redis Stream、多 Worker、故障恢复 |

> 判断口诀：**先 L0 跑通数据，再按需升级**。不要一开始就上分布式 +
> 浏览器 + 数据库，90% 的场景 L0/L1 就够。

## 配置速查（对应场景）

| 场景 | 关键配置 |
|---|---|
| 简单单机 | 什么都不配（默认 memory 队列 + MemoryFilter） |
| 需要去重跨运行 | Redis 可用即可（自动 AioRedisFilter） |
| 整站抓取 | `MAX_PAGES` / `DOWNLOAD_DELAY` / `RETRY_*` |
| 分布式 | `QUEUE_TYPE = redis_stream` + `CLUSTER_*` |
| 反爬 | `DOWNLOADER = CamoufoxDownloader` + `DYNAMIC_RENDER_*` |
| 通知 | `NOTIFICATION_ENABLED = True` + 渠道 webhook |
