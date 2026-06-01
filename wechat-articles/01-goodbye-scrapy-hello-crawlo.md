# 写爬虫这些年，我遇到的那些"没想到"

> 爬虫跑起来不难，跑稳才难。

你以为写完代码就完事了？实际上线之后，各种意外等着你：断电、重启、被限流、任务丢失、Cloudflare 升级……本文不讲特性，讲我经历过的五次生产事故，以及 Crawlo 怎么解决的。

---

## 事故一：跑了三天，被运维重启了服务器

这是最常见的事故。

爬虫跑了三天，采集了快 100 万条数据，运维不知道在跑爬虫，做了一次例行维护重启。那一刻心态是崩溃的——从头跑？100 万条重新来过？

**Crawlo 的解法：检查点自动保存。**

```python
# settings.py
CHECKPOINT_ENABLED = True
```

开启之后，Crawlo 在每次请求完成后自动保存状态到本地：
- **已爬 URL 指纹**：不重复爬取同一页面
- **待爬队列**：剩下的 URL 继续爬
- **运行统计**：当前进度记录

服务器重启？重新运行 `crawlo run myspider`，一行日志告诉你从哪继续：

```bash
$ crawlo run myspider
[INFO] Resuming from checkpoint: 14238 pending requests, 985421 fingerprints
```

不怕意外中断，只怕你没开检查点。

---

## 事故二：并发开太高，IP 被封了一个月

当时爬一个数据接口，自认为很克制地开了 32 并发。结果第二天醒来，IP 被封了，解封要等一个月。

限流这事，不是"开低就安全"这么简单——白天宽松晚上严、接口正常时快、响应一慢就要降速。每次换网站都要重新试，调试成本极高。

**Crawlo 的解法：背压控制器自动调节。**

```python
# settings.py
BACKPRESSURE_STRATEGY = 'adaptive'
```

Crawlo 实时监控三个维度：
- **内存占用**：过高自动降速，防止 OOM
- **响应延迟**：目标变慢，增大间隔
- **队列积压**：处理不过来，减少新请求

你不需要算参数，框架在运行过程中自动找到当前条件下的最优并发。

---

## 事故三：Cloudflare 突然升级，所有爬虫全挂

目标站点某天突然升级了 Cloudflare 防护，之前能爬的突然 403 了。更要命的是，不只是一两个页面，是整个站点全部返回挑战页面。

临时方案是手动换代理、加睡眠时间，但都是权宜之计。

**Crawlo 的解法：下载器按场景切换。**

```python
# settings.py
DOWNLOADER = 'cloakbrowser'   # Cloudflare 专用浏览器
# DOWNLOADER = 'camoufox'   # 指纹伪装
# DOWNLOADER = 'playwright'  # JS 渲染
```

遇到 Cloudflare 升级？换一行配置，重跑。不需要改爬虫代码，不需要装额外的包。

---

## 事故四：从单机扩展到五台机器，任务开始疯狂重复

单机跑得好好的，上了五台机器协同爬取，数据开始疯狂重复——同一个 URL 被不同的机器重复爬了好几次。还有更离谱的：一台机器在处理任务的时候突然宕机，那批任务就永远挂在那边，既不成功也不失败。

这是分布式爬虫的经典问题：**任务分发没有确认机制。**

**Crawlo 的解法：两阶段 ACK + 死信队列。**

```
阶段一：任务从主队列投递给 Worker，标记 pending
阶段二：Worker 完成任务后显式 ACK，任务才真正完成
```

Worker 崩溃？超过时间未 ACK 的任务自动重新入队，不会丢失。多次重试仍然失败的任务进入死信队列，可以手动查看和重试。

```python
# settings.py
CrawloConfig.distributed(
    redis_host='10.0.0.1',
    redis_port=6379,
    project_name='myproject',
)
```

从单机切到多机，不需要改一行爬虫代码。

---

## 事故五：每天凌晨跑数据，写了三屏的 crontab

业务需要每天凌晨抓一批数据，方案是：Python 脚本 + crontab 定时 + 日志管理 + 失败告警。写完发现，光是这些"基础设施"代码比爬虫本身还长。

而且 crontab 不好管理——多台机器要同步配置，机器重启后 crontab 可能失效，任务跑没跑成功也不容易追踪。

**Crawlo 的解法：内置定时调度器。**

```python
# settings.py
SCHEDULER_ENABLED = True
SCHEDULER_JOBS = [
    {
        'spider': 'news_spider',
        'cron': '0 0 8 * * *',       # 每天早上 8:00
        'enabled': True,
        'priority': 10,
        'max_retries': 3,
        'retry_delay': 60,
        'args': {},
    },
    {
        'spider': 'price_spider',
        'interval': {'hours': 1},     # 每 1 小时
        'enabled': True,
        'priority': 10,
        'max_retries': 3,
        'retry_delay': 60,
        'args': {},
    },
]
```

```bash
# 启动调度器
crawlo run schedule
```

Spider 本身不需要任何调度相关代码，调度逻辑全在配置层。跑没跑、跑了多少次，调度器统一管理。

---

## 完整代码：所有特性一起用

以上所有场景，对应同一个项目：

```bash
pip install crawlo[all]
crawlo startproject myproject
cd myproject
crawlo genspider quotes quotes.example.com
```

```python
# settings.py
CHECKPOINT_ENABLED = True
BACKPRESSURE_STRATEGY = 'adaptive'
DOWNLOADER = 'httpx'
SCHEDULER_ENABLED = True
ITEM_PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}
SCHEDULER_JOBS = [
    {
        'spider': 'quotes',
        'cron': '0 * * * *',           # 每小时执行一次
        'enabled': True,
        'priority': 10,
        'max_retries': 3,
        'retry_delay': 60,
        'args': {},
    },
]
```

```python
# spiders/quotes.py
import crawlo

class QuotesSpider(crawlo.Spider):
    name = 'quotes'

    def start_requests(self):
        yield crawlo.Request('https://quotes.toscrape.com/')

    def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small::text').get(),
            }
        for href in response.css('li.next a::attr(href)'):
            yield response.follow(href)
```

```bash
crawlo run quotes      # 立即运行
crawlo run schedule    # 定时调度
```

---

## 特性一览

| 特性 | 说明 |
|------|------|
| 检查点续爬 | `CHECKPOINT_ENABLED = True`，自动保存与恢复 |
| 智能背压 | 多策略自动调节并发 |
| 多种下载器 | HttpX / aiohttp / Playwright / Camoufox / CloakBrowser |
| 分布式 | 两阶段 ACK + 故障转移 + 死信队列 |
| 定时调度 | Cron / Interval，配置即用 |
| Pipeline | MySQL / MongoDB / PostgreSQL / ClickHouse 等内置 |
| asyncio 原生 | Python 3.8+，直接用 `async/await` |

---

## 开源地址

**GitHub**: https://github.com/crawl-coder/Crawlo

如果觉得有用，给我们一个 Star ⭐

---
