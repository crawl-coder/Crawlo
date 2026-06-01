# 3 分钟写一个爬虫：Crawlo 极速上手指南

> 从 pip install 到数据入库，比泡一杯咖啡还快。

---

## 第 1 分钟：安装

```bash
pip install crawlo
```

就这一行。核心功能全包含：异步引擎、调度器、下载器、Pipeline。

如果你需要更多能力：

```bash
pip install crawlo[render]      # Playwright/Camoufox 浏览器渲染
pip install crawlo[stealth]     # CloakBrowser 反检测
pip install crawlo[database]    # MySQL/MongoDB/PostgreSQL/ClickHouse
pip install crawlo[all]         # 全部依赖
```

---

## 第 2 分钟：写爬虫

创建项目：

```bash
crawlo startproject demo
cd demo
```

项目结构：

```
demo/
├── run.py                # 入口脚本（直接运行 or --schedule 定时）
├── crawlo.cfg            # 入口配置文件
├── demo/
│   ├── __init__.py
│   ├── settings.py       # 配置文件
│   ├── middlewares.py    # 中间件
│   ├── pipelines.py      # 数据管道
│   └── spiders/
│       └── __init__.py
└── logs/                 # 日志目录
```

写一个最简单的爬虫，爬取名言网站：

```python
# demo/spiders/quotes.py
import crawlo

class QuotesSpider(crawlo.Spider):
    name = 'quotes'
    start_urls = ['https://quotes.toscrape.com/']

    def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small.author::text').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),
            }

        # 自动翻页
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page)
```

**就这么简单。** 如果你用过 Scrapy，这段代码你应该一眼就懂。

---

## 第 3 分钟：运行 + 存数据

### 运行爬虫

```bash
crawlo run quotes
```

你会看到类似输出：

```
[INFO] Spider 'quotes' started
[INFO] Crawled (200) <GET https://quotes.toscrape.com/>
[INFO] Crawled (200) <GET https://quotes.toscrape.com/page/2/>
[INFO] Spider 'quotes' closed (finished)
[INFO] Stats: {'download_count': 10, 'item_count': 100}
```

### 存储到 CSV

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.CsvPipeline': 300,
}
CSV_FILE = 'quotes.csv'
```

### 存储到 MySQL

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.MySQLPipeline': 300,
}
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_DATABASE = 'demo'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password'
```

### 存储到 MongoDB

```python
# settings.py
ITEM_PIPELINES = {
    'crawlo.pipelines.MongoPipeline': 300,
}
MONGO_URI = 'mongodb://localhost:27017'
MONGO_DATABASE = 'demo'
```

### 存储到更多

Crawlo 内置 10+ 数据管道，开箱即用：

| Pipeline | 用途 |
|----------|------|
| `CsvPipeline` | CSV 文件 |
| `JsonLinesPipeline` | JSON Lines 文件 |
| `MySQLPipeline` | MySQL |
| `MongoPipeline` | MongoDB |
| `PostgreSQLPipeline` | PostgreSQL |
| `ClickHousePipeline` | ClickHouse |
| `ElasticsearchPipeline` | Elasticsearch |
| `SQLitePipeline` | SQLite |
| `HBasePipeline` | HBase |
| `MemoryDedupPipeline` | 内存去重 |
| `RedisDedupPipeline` | Redis 去重 |

---

## 进阶：5 个常用配置

### 1. 设置并发数

```python
CONCURRENCY = 32  # 默认 8
```

### 2. 设置下载延迟

```python
DOWNLOAD_DELAY = 1.0  # 秒
```

### 3. 切换下载器（JS 渲染）

```python
DOWNLOADER = 'playwright'  # aiohttp / playwright / camoufox / cloakbrowser
```

### 4. 启用断点续爬

```python
CHECKPOINT_ENABLED = True       # 启用检查点（默认关闭）
CHECKPOINT_DIR = '.checkpoints' # 保存目录
```

### 5. 分布式模式

```python
# 单机 → 分布式，只需改配置
from crawlo.config import CrawloConfig

settings = CrawloConfig.distributed(
    redis_host='10.0.0.1',
    redis_port=6379,
)
```

---

## 不写项目？直接单文件跑

 Crawlo 也支持不创建项目，直接写一个 Python 文件运行：

```python
# standalone_spider.py
import crawlo

class MySpider(crawlo.Spider):
    name = 'my'
    start_urls = ['https://httpbin.org/get']

    def parse(self, response):
        yield {'url': response.url, 'status': response.status}

if __name__ == '__main__':
    from crawlo.framework import run_spider
    import asyncio
    asyncio.run(run_spider(MySpider))
```

```bash
python standalone_spider.py
```

---

## 项目自带 run.py：一文件双模式

`crawlo startproject` 生成的 `run.py` 支持两种运行模式：

```python
# run.py（startproject 自动生成）
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        # 定时任务调度器模式
        from crawlo.scheduling import start_scheduler
        start_scheduler(os.path.dirname(os.path.abspath(__file__)))
    else:
        # 正常爬虫模式
        asyncio.run(CrawlerProcess().crawl('my_spider'))
```

```bash
python run.py             # 立即执行爬虫
python run.py --schedule  # 启动定时任务调度器

# 等价 CLI 命令
crawlo run myspider       # 立即执行爬虫
crawlo run schedule       # 启动定时任务调度器
```

---

---

*关注公众号，获取更多 Crawlo 技术干货和爬虫实战经验。*
