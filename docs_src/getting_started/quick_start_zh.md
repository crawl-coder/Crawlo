# Crawlo 快速入门指南

本指南将帮助您开始使用 Crawlo，一个现代化的异步网络爬虫框架。

## 先决条件

- Python 3.10 或更高版本
- Python 和网络爬虫概念的基础知识

## 安装

1. 克隆仓库：
   ```bash
   git clone https://github.com/crawl-coder/Crawlo.git
   cd crawlo
   ```

2. 以开发模式安装：
   ```bash
   pip install -e .
   ```

## 创建您的第一个项目

1. 创建一个新项目：
   ```bash
   crawlo startproject my_first_project
   cd my_first_project
   ```

2. 生成一个爬虫：
   ```bash
   crawlo genspider my_spider example.com
   ```

3. 编辑 `my_first_project/spiders/my_spider.py` 中的爬虫：
   ```python
   from crawlo import Spider, Request
   from my_first_project.items import MyItem

   class MySpider(Spider):
       name = "my_spider"
       start_urls = ["https://example.com"]

       def parse(self, response):
           # 提取数据
           item = MyItem()
           item['title'] = response.css('title::text').get()
           yield item

           # 跟进链接
           for link in response.css('a::attr(href)').getall():
               yield Request(url=response.urljoin(link), callback=self.parse)
   ```

4. 运行爬虫：
   ```bash
   python run.py my_spider
   ```

## 分布式爬取

要在分布式模式下运行您的爬虫：

1. 启动 Redis：
   ```bash
   redis-server
   ```

2. 在分布式模式下运行爬虫：
   ```bash
   python run.py my_spider --distributed
   ```

3. 在其他机器上运行额外的节点：
   ```bash
   python run.py my_spider --distributed --redis-host YOUR_REDIS_HOST
   ```

## 配置

通过编辑 `settings.py` 自定义您的项目：

```python
# 增加并发数
CONCURRENCY = 16

# 添加请求之间的延迟
DOWNLOAD_DELAY = 1.0

# 启用管道
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
    'crawlo.pipelines.json_pipeline.JsonPipeline',
]
```

## 下一步

- 阅读完整的 [Crawlo 框架文档](crawlo_framework_documentation_zh.md)
- 探索 [examples](../examples/) 目录以获取更多复杂用例
- 查看 [API 参考](api_reference_zh.md) 了解所有类和方法的详细信息