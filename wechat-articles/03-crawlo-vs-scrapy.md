# Crawlo vs Scrapy：同一个爬虫，两种写法

> 一样的需求，不一样的体验。

---

## 前言

很多人问：**我已经会 Scrapy 了，为什么要换 Crawlo？**

口说无凭，代码为证。今天我们用同一个需求——爬取一个分页列表 + 详情页的电商网站——分别用 Scrapy 和 Crawlo 实现，逐行对比。

---

## 场景描述

- 列表页：`/list?page=1,2,3...`，每页 20 个商品链接
- 详情页：`/item/{id}`，提取标题、价格、描述
- 要求：断点续爬、自动限速、存储到 MySQL

---

## 对比一：项目结构

### Scrapy

```bash
scrapy startproject shop
cd shop
scrapy genspider products example.com
# 手动创建 items.py、pipelines.py、middlewares.py、settings.py
```

### Crawlo

```bash
crawlo startproject shop
cd shop
crawlo genspider products example.com
```

**差异**：命令几乎完全兼容 Scrapy 习惯。`crawlo genspider` 自动从模板生成 Spider，包含 `start_requests` 和 `parse` 方法骨架。Scrapy 的 `startproject` 生成的项目文件较少（需手动创建 items/pipelines/settings），Crawlo 生成的项目模板更完整开箱即用。

---

## 对比二：定义数据模型

### Scrapy

```python
# items.py
import scrapy

class ProductItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()
```

### Crawlo

```python
# 不需要定义 Item 类！直接用字典
# 在 Spider 中 yield dict 即可
```

**差异**：Crawlo 不强制定义 Item 类，直接 `yield {'title': ..., 'price': ...}` 即可。更 Pythonic，也更灵活。

---

## 对比三：写爬虫

### Scrapy

```python
# spiders/products.py
import scrapy

class ProductsSpider(scrapy.Spider):
    name = 'products'
    start_urls = ['https://example.com/list?page=1']

    def parse(self, response):
        # 提取商品链接
        for href in response.css('a.product::attr(href)'):
            yield response.follow(href, callback=self.parse_detail)

        # 翻页
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page)

    def parse_detail(self, response):
        yield {
            'title': response.css('h1::text').get(),
            'price': response.css('.price::text').get(),
            'description': response.css('.desc::text').get(),
            'url': response.url,
        }
```

### Crawlo

```python
# spiders/products.py
import crawlo

class ProductsSpider(crawlo.Spider):
    name = 'products'
    start_urls = ['https://example.com/list?page=1']

    def parse(self, response):
        for href in response.css('a.product::attr(href)'):
            yield response.follow(href, callback=self.parse_detail)

        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page)

    def parse_detail(self, response):
        yield {
            'title': response.css('h1::text').get(),
            'price': response.css('.price::text').get(),
            'description': response.css('.desc::text').get(),
            'url': response.url,
        }
```

**差异**：核心逻辑代码几乎一样。Crawlo 的 Spider API 与 Scrapy 高度兼容，主要区别在于 `import crawlo` vs `import scrapy`。

---

## 对比四：断点续爬

### Scrapy

```bash
# 启动时指定 jobdir
scrapy crawl products -s JOBDIR=jobs/products_001

# 停止后重启，需要记住 jobdir 路径
scrapy crawl products -s JOBDIR=jobs/products_001
```

**问题**：
- 需要手动指定 JOBDIR，容易忘记
- 只保存待爬队列，不保存已爬数据
- 不支持自动恢复，需要手动传参

### Crawlo

```bash
# 第一次运行（自动保存检查点）
crawlo run products

# Ctrl+C 停止
^C[INFO] Checkpoint saved

# 第二次运行（自动续爬）
crawlo run products
[INFO] Resuming from checkpoint: 1200 items, 300 requests pending
```

**优势**：
- **检查点已开启**：配置 `CHECKPOINT_ENABLED = True` 后，保存待爬队列 + 已爬 URL 指纹
- **自动恢复**：检测到检查点自动续爬

---

## 对比五：限速/背压

### Scrapy

```python
# settings.py
DOWNLOAD_DELAY = 1.0                    # 固定延迟
CONCURRENT_REQUESTS_PER_DOMAIN = 8      # 固定并发
AUTOTHROTTLE_ENABLED = True             # 启用自动限速（需额外扩展）
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = True
```

**问题**：
- AutoThrottle 是独立扩展，配置复杂
- 只根据响应时间调整，不感知内存/队列压力
- 全局固定参数，无法按站点自适应

### Crawlo

```python
# settings.py
CONCURRENCY = 16                        # 基础并发
BACKPRESSURE_STRATEGY = 'queue_size'     # 背压策略
```

**优势**：
- **多维感知**：内存 + 队列 + 响应延迟，综合决策
- **3 种策略**：队列大小、自适应、智能计算
- **零调参**：框架自动找到最优并发度

---

## 对比六：Cloudflare 绕过

### Scrapy

```bash
pip install scrapy-cloudflare-middleware
pip install scrapy-playwright
# 或者
pip install scrapy-fake-useragent
pip install scrapy-rotating-proxies
# 配置中间件...
# 还不一定能过...
```

### Crawlo

```python
# settings.py
DOWNLOADER = 'cloakbrowser'   # 一行配置
```

**优势**：内置 5 种下载器，覆盖所有反爬场景，无需安装第三方中间件。

---

## 对比七：分布式

### Scrapy + Scrapy-Redis

```python
# settings.py
SCHEDULER = 'scrapy_redis.scheduler.Scheduler'
DUPEFILTER_CLASS = 'scrapy_redis.dupefilter.RFPDupeFilter'
REDIS_URL = 'redis://localhost:6379'
```

**差异**：
- Crawlo 有 ACK 语义，Scrapy-Redis 无
- Crawlo 有两阶段故障转移，Scrapy-Redis 节点下线后任务丢失
- Crawlo 有死信队列，Scrapy-Redis 失败任务无法重试

### Crawlo

```python
# settings.py
from crawlo.config import CrawloConfig
settings = CrawloConfig.distributed(
    redis_host='10.0.0.1',
    redis_port=6379,
)
```

**优势**：
- **ACK 语义**：任务分配 → Worker 确认 → 完成 XACK
- **两阶段故障转移**：suspect → confirm，防误回收
- **死信队列**：超过投递次数的任务进死信，可重试
- **心跳守护**：15 秒心跳 + ±20% jitter 防风暴
- **动态配置**：运行时调整并发/限速/种子 URL

---

## 功能对比总表

| 特性 | Crawlo | Scrapy |
|------|--------|--------|
| 异步引擎 | asyncio | Twisted |
| 代码风格 | async/await | 回调/deferred |
| 断点续爬 | ✅ 内置（需开启配置） | ⚠️ Jobdir 方案 |
| 背压控制 | ✅ 多策略控制 | ⚠️ AutoThrottle 扩展 |
| Cloudflare 绕过 | ✅ 内置 5 种下载器 | ⚠️ 需第三方扩展 |
| 分布式 | ✅ ACK + 故障转移 | ⚠️ Scrapy-Redis 扩展 |
| 深度传播 | ✅ 自动 | ⚠️ 手动传参 |
| 数据模型 | ✅ 字典（灵活） | Item 类 |
| Pipeline 内置 | 10+ 种 | ⚠️ 需自行实现 |
| Python 3.12+ | ✅ | ✅ 基本支持 |

---

## 迁移成本

从 Scrapy 迁移到 Crawlo，主要改动与注意事项：

1. `import scrapy` → `import crawlo`
2. `scrapy.Spider` → `crawlo.Spider`
3. `scrapy.Request` → `crawlo.Request`
4. 可直接使用字典代替 Item 类（也可保留 Item 类）
5. 需调整 `settings.py`（配置项名称略有差异）

**爬虫的核心解析逻辑基本可以保留复用。**

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
