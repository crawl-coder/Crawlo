# 创建第一个爬虫

本教程将引导您创建第一个 Crawlo 爬虫，从安装到运行的完整过程。

## 环境准备

### 安装 Python
确保您的系统已安装 Python 3.7 或更高版本：

```bash
python --version
```

### 安装 Crawlo
使用 pip 安装 Crawlo：

```bash
pip install crawlo
```

## 创建项目

使用 Crawlo 命令行工具创建新项目：

```bash
crawlo startproject my_first_spider
cd my_first_spider
```

这将创建以下项目结构：

```
my_first_spider/
├── settings.py          # 项目配置文件
├── spiders/             # 爬虫目录
│   ├── __init__.py
│   └── example.py       # 示例爬虫
├── pipelines/           # 数据管道目录
│   └── __init__.py
├── middlewares/         # 中间件目录
│   └── __init__.py
└── items/               # 数据项定义目录
    └── __init__.py
```

## 编写爬虫

编辑 `spiders/example.py` 文件，创建您的第一个爬虫：

```python
from crawlo import Spider

class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['http://httpbin.org/get']
    
    def parse(self, response):
        # 提取页面信息
        yield {
            'url': response.url,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'text': response.text[:100] + '...' if len(response.text) > 100 else response.text
        }
```

## 运行爬虫

在项目目录中运行爬虫：

```bash
crawlo run example
```

您将看到类似以下的输出：

```
2023-01-01 12:00:00 [crawlo] INFO: Spider opened: example
2023-01-01 12:00:01 [crawlo] INFO: Received response: 200 http://httpbin.org/get
2023-01-01 12:00:01 [crawlo] INFO: Spider closed: example
```

## 进阶示例

让我们创建一个更复杂的爬虫，爬取新闻网站的标题和链接：

```python
from crawlo import Spider

class NewsSpider(Spider):
    name = 'news'
    start_urls = ['https://news.ycombinator.com/']
    
    def parse(self, response):
        # 提取新闻标题和链接
        for item in response.css('.storylink'):
            yield {
                'title': item.css('::text').get(),
                'url': item.css('::attr(href)').get()
            }
        
        # 跟随下一页链接
        next_page = response.css('.morelink::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

## 配置爬虫

您可以通过 `settings.py` 文件配置爬虫行为：

```python
# settings.py
CONCURRENCY = 10           # 并发请求数
DOWNLOAD_DELAY = 1.0       # 下载延迟（秒）
DOWNLOAD_TIMEOUT = 30      # 下载超时（秒）
DOWNLOADER_TYPE = 'httpx'  # 下载器类型

# 自定义请求头
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Crawlo/1.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
```

## 使用管道处理数据

创建一个简单的管道来处理爬取的数据：

```python
# pipelines.py
class JsonWriterPipeline:
    def open_spider(self, spider):
        self.file = open('items.json', 'w')
    
    def close_spider(self, spider):
        self.file.close()
    
    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
        return item
```

在 `settings.py` 中启用管道：

```python
# settings.py
PIPELINES = {
    'my_first_spider.pipelines.JsonWriterPipeline': 300,
}
```

## 使用中间件

创建一个简单的中间件来处理请求和响应：

```python
# middlewares.py
class UserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers['User-Agent'] = 'MyBot/1.0'
        return request
```

在 `settings.py` 中启用中间件：

```python
# settings.py
MIDDLEWARES = {
    'my_first_spider.middlewares.UserAgentMiddleware': 400,
}
```

## 运行带参数的爬虫

```bash
# 设置日志级别
crawlo run example --log-level DEBUG

# 指定配置文件
crawlo run example --config settings.py

# 设置并发数
crawlo run example --concurrency 20
```

## 查看统计信息

运行完成后，查看爬虫统计信息：

```bash
crawlo stats example
```

## 下一步

- 学习更多关于[下载器](../modules/downloader/index.md)的知识
- 探索[中间件](../modules/middleware/index.md)的功能
- 掌握[管道](../modules/pipeline/index.md)的使用
- 了解[分布式部署](../modules/advanced/distributed.md)