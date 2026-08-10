# 实战教程：整站抓取 Cookbook（real_world_catalog）

> 完整可运行示例：[examples/real_world_catalog/](../../examples/real_world_catalog/)
> 覆盖：列表页 → 分页 → 详情页 → 去重 → 存储（JSONL / MySQL）→ 监控告警 → 分布式。
> 本地演示站点由 `demo_server.py` 提供，无需外网即可跑通全流程。

## 1. 项目结构

```text
examples/real_world_catalog/
├── crawlo.cfg              # 项目配置入口（settings 模块路径）
├── settings.py             # 单机/分布式配置（环境变量切换）
├── items.py                # CatalogItem 数据模型
├── pipelines.py            # JSONL 存储管道（开箱即用）
├── spiders/catalog_spider.py  # 整站抓取 Spider
├── demo_server.py          # 本地 mock 目录站（分页列表 + 详情页）
├── docker-compose.yml      # MySQL + Redis（可选，用于存储/分布式验证）
└── run.py                  # 启动入口（--distributed 切分布式）
```

## 2. 快速开始（单机）

```bash
cd examples/real_world_catalog
python demo_server.py --port 9000      # 终端 1：起 mock 站
python run.py                          # 终端 2：跑爬虫
```

输出落在 `output/catalog.jsonl`，包含 url / title / price / category /
description / sku / in_stock 七个字段。

## 3. Spider 逐节讲解

### 3.1 起始请求（运行时构建）

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    base_url = os.environ.get("CATALOG_BASE_URL", "http://127.0.0.1:9000")
    self.start_urls = [f"{base_url}/catalog?page=1"]
```

**注意**：`start_urls` 必须在 `__init__` 里构建，不要在类体里用
`os.environ` 拼——类定义在 import 时执行，此时环境变量可能还没设置。

### 3.2 列表页解析 + 分页

```python
def parse(self, response):
    for href in response.css("a.product-link::attr(href)").getall():
        yield Request(url=response.urljoin(href), callback=self.parse_detail, meta={...})

    next_href = response.css(
        "a.pagination-link.next::attr(href)",
        adaptive=True,              # 自适应选择器：网站改版自动自愈
        identifier="catalog_next_page",
    ).get()
    if next_href and page < max_pages:
        yield Request(url=response.urljoin(next_href), callback=self.parse, meta={"page": page + 1})
```

要点：
- `response.css(..., adaptive=True)`：Crawlo 的自适应选择器会在选择器失效时
  用指纹+相似度自动重新定位，适合整站抓取这种"网站随时改版"的场景；
- 分页深度用 `MAX_PAGES` 限制（`custom_settings`），防止失控深爬；
- `dont_filter=False` 让下一页链接正常参与去重（避免重复页）。

### 3.3 详情页解析

详情页把列表页摘要（`meta` 透传）与详情字段合并成 `CatalogItem`：

```python
def parse_detail(self, response):
    summary = response.meta.get("listing_summary") or {}
    return CatalogItem(
        url=response.url,
        title=response.css("h1.product-title::text").get("").strip() or summary.get("title", ""),
        price=response.css(".product-price::text").get("").strip() or summary.get("price", ""),
        category=summary.get("category", ""),
        description=response.css(".product-description::text").get("").strip(),
        sku=response.css(".product-sku::text").get("").strip(),
        in_stock=response.css(".stock-status.in-stock").get() is not None,
    )
```

## 4. 去重

去重由框架自带，无需额外代码：

- 单机：`MemoryFilter`（进程内）；
- Redis 可用时自动切换 `AioRedisFilter`（跨运行去重，重启不重抓）；
- 列表页/详情页的重复请求由调度器过滤，统计里可见
  `filtered_count` / `Filtered N duplicate request(s)`。

## 5. 存储

### 5.1 JSONL（开箱即用）

`pipelines.py` 的 `JsonlCatalogPipeline` 把每个 item 写一行 JSON。
路径由 `CATALOG_OUTPUT_PATH` 控制（默认 `output/catalog.jsonl`）。

### 5.2 MySQL（可选）

```bash
docker compose up -d mysql            # 起 MySQL
CRAWLO_MYSQL_ENABLED=1 python run.py  # 启用 MySQL 管道
```

启用后 `settings.py` 会把 `crawlo.pipelines.MySQLPipeline`（批量插入，
`MYSQL_BATCH_SIZE=100`）追加到管道链，写入 `catalog_items` 表。
表结构由管道自动建表（首次运行自动创建）。

## 6. 监控与告警

`settings.py` 内置：

- `HealthCheckExtension`：健康检查（`HEALTH_CHECK_INTERVAL`）；
- `LogStats`：周期统计（items_per_minute / pages_per_minute / 事件循环延迟等）；
- 通知系统：配置 `NOTIFICATION_ENABLED = True` + 钉钉/飞书/企业微信
  webhook 后，爬虫状态/告警自动推送（见 `docs/guides/notification-guide.md`）。

运行结束的统计示例：

```text
'crawlo:items_per_minute': 552.32,
'crawlo:filter/duplicate_rps': ...,
'crawlo:download_error/ConnectError': 0,
```

## 7. 分布式模式

```bash
docker compose up -d redis            # 起 Redis
python run.py --distributed           # 终端 1：Worker 1（种子生成）
python run.py --distributed           # 终端 2+：更多 Worker
```

分布式由 `QUEUE_TYPE = redis_stream` 驱动：

- 种子 URL 由 Leader（首个 Worker）生成，其余 Worker 自动跳过（`_try_acquire_seed_lock_atomic`）；
- 任务通过 Redis Stream + Consumer Group 分发，`XACK` 确认；
- Worker 崩溃后任务被 `XCLAIM/XAUTOCLAIM` 回收，不丢失；
- 所有 Worker 空闲时 Leader 协调广播退出。

## 8. 真实站点适配清单

把示例改造成真实项目时，逐项替换：

| 位置 | 替换为 |
|---|---|
| `demo_server.py` | 真实目标站（或保留作测试） |
| `CATALOG_BASE_URL` | 真实站点入口 |
| 列表/详情 CSS 选择器 | 目标站真实选择器（用 `crawlo shell <url>` 交互调试） |
| `MAX_PAGES` | 真实页数上限或无限 |
| `JsonlCatalogPipeline` | MySQL / Mongo / ES 管道 |
| 通知配置 | 真实 webhook / 密钥 |

## 9. 验收

仓库自带集成测试 `tests/integration/test_real_world_catalog_example.py`：
自起 mock 站 → 全流程爬取 → 断言 6 条 item 字段完整、无重复写入。
