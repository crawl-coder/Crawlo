# 🔰 新手手把手教程

欢迎来到 Crawlo！本教程将带您从零开始，一步步构建并运行您的第一个爬虫项目。

---

## 1. 环境准备

在开始之前，请确保您的电脑已安装 **Python 3.7** 或更高版本。

### 安装框架
打开终端（或命令提示符），运行以下命令：

```bash
# 基础安装
pip install crawlo

# 推荐安装（包含 AI 适配与浏览器支持）
pip install "crawlo[mcp,playwright]"

# 如果安装了 playwright，需要初始化浏览器内核
playwright install
```

---

## 2. 创建您的第一个项目

使用 `crawlo` 命令行工具可以快速搭建项目骨架。

```bash
# 创建项目文件夹
crawlo startproject my_first_spider
cd my_first_spider
```

项目结构如下：
- `crawlo.cfg`: 框架主配置文件。
- `my_first_spider/`: 项目代码包。
    - `spiders/`: 存放爬虫代码的地方。
    - `settings.py`: 项目的全局设置。
    - `items.py`: 定义您要抓取的数据结构。
    - `middlewares.py`: 自定义请求/响应处理逻辑。
    - `pipelines.py`: 数据保存逻辑（如保存到数据库）。
- `run.py`: 启动爬虫的入口脚本。

---

## 3. 编写第一个爬虫

我们将抓取 `quotes.toscrape.com` 这个专门用于练习爬虫的网站。

生成一个爬虫模板：
```bash
crawlo genspider quotes quotes.toscrape.com
```

打开 `my_first_spider/spiders/quotes.py`，将其修改为：

```python
from crawlo import Spider

class QuotesSpider(Spider):
    name = 'quotes'
    start_urls = ['https://quotes.toscrape.com/']

    async def parse(self, response):
        # 循环处理页面上的每一条名言
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small.author::text').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),
            }

        # 寻找“下一页”按钮并自动跟进
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)
```

---

## 4. 运行并查看结果

在项目根目录下运行：

```bash
crawlo run quotes
```

您将在控制台中看到抓取到的名言数据。

---

## 5. 核心参数配置（快速上手）

所有的配置都在 `settings.py` 中。以下是新手最常用的几个参数：

### 设置并发数
控制同时抓取多少个网页：
```python
CONCURRENCY = 16  # 默认通常为 8 或 16
```

### 设置下载延迟
防止抓取过快被封：
```python
DOWNLOAD_DELAY = 1.0  # 每个请求间隔 1 秒
RANDOMNESS = True     # 开启随机抖动，更像真人
```

### 开启浏览器渲染
如果网页内容是动态加载的（如 Vue/React 编写的网站）：
```python
# 在爬虫代码中指定
yield Request(url, callback=self.parse, meta={'use_dynamic_loader': True})
```

### 数据保存到文件
在运行命令时指定输出文件：
```bash
crawlo run quotes -o result.json
# 或者
crawlo run quotes -o result.csv
```

### 应对网站改版（进阶必备）
如果您抓取的网站经常改版，建议在编写选择器时加上 `adaptive=True`。
```python
# 即使 class="text" 变成了 class="content"，框架也能自动找回它！
title = response.css('span.text::text', adaptive=True).get()
```

---

## 6. 进阶建议

- **[参数配置详解](configuration.md)**：深入了解所有可调参数。
- **[实战案例库](examples.md)**：查看各种复杂场景的现成代码。
- **[高级特性](advanced-features.md)**：学习如何绕过 Cloudflare、使用自适应选择器等。
