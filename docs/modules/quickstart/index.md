# 快速开始

本指南将帮助您快速上手 Crawlo 框架，创建您的第一个爬虫项目并运行它。

## 安装 Crawlo

### 使用 pip 安装

```bash
pip install crawlo
```

### 从源码安装

```bash
git clone https://github.com/crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

## 创建第一个项目

使用 Crawlo 的命令行工具创建新项目：

```bash
crawlo startproject myproject
```

这将创建以下项目结构：

```
myproject/
├── crawlo.cfg           # 项目配置文件
├── run.py               # 启动脚本
├── logs/                # 日志目录
└── myproject/           # 项目模块目录
    ├── __init__.py
    ├── settings.py       # 项目配置
    ├── items.py         # 数据项定义
    ├── middlewares.py   # 中间件
    ├── pipelines.py     # 数据管道
    └── spiders/         # 爬虫目录
        ├── __init__.py
        └── example.py   # 示例爬虫
```

## 创建第一个爬虫

进入项目目录并生成新的爬虫：

```bash
cd myproject
crawlo genspider myspider example.com
```

这将在 `spiders/` 目录下创建一个新的爬虫文件 `myspider.py`：

```python
from crawlo import Spider

class MyspiderSpider(Spider):
    name = 'myspider'
    
    def parse(self, response):
        # 在这里实现解析逻辑
        pass
```

## 编写爬虫逻辑

编辑 `spiders/myspider.py` 文件，添加您的爬虫逻辑：

```python
from crawlo import Spider

class MyspiderSpider(Spider):
    name = 'myspider'
    start_urls = ['http://example.com']
    
    def parse(self, response):
        # 提取页面标题
        title = response.extract_text('title')
        
        # 提取所有链接
        links = response.extract_attrs('a', 'href')
        
        yield {
            'title': title,
            'links': links,
            'url': response.url
        }
        
        # 跟随链接继续爬取
        for link in links:
            if link.startswith('http'):
                yield response.follow(link, callback=self.parse)
```

## 运行爬虫

进入项目目录并运行爬虫：

```bash
cd myproject
crawlo run example
```

你也可以使用以下参数来控制爬虫运行：

```bash
# 设置日志级别为DEBUG以查看更多详细信息
crawlo run example --log-level DEBUG

# 设置并发数为32
crawlo run example --concurrency 32

# 组合使用多个参数
crawlo run example --log-level INFO --concurrency 16
```

## 查看结果

爬虫运行完成后，您可以在控制台看到输出的结果，或者在配置的管道中查看存储的数据。

## 下一步

- 学习更多关于[爬虫基类](../core/spider.md)的知识
- 了解[下载器](../downloader/index.md)的使用
- 探索[中间件](../middleware/index.md)的功能
- 掌握[管道](../pipeline/index.md)的使用