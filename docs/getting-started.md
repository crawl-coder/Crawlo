# 快速入门指南

欢迎使用 Crawlo！本指南将带您完成从安装到运行第一个爬虫的全过程。

## 1. 安装

Crawlo 要求 **Python 3.7+** 环境。

### 基础安装
```bash
pip install crawlo
```

### 完整安装（推荐，包含 AI 适配与浏览器支持）
```bash
pip install "crawlo[mcp,playwright]"
playwright install  # 安装浏览器内核
```

---

## 2. 创建第一个项目

使用 CLI 工具可以快速初始化项目结构：

```bash
# 创建新项目
crawlo startproject myproject
cd myproject

# 生成爬虫模板
crawlo genspider example example.com
```

项目目录结构如下：
```text
myproject/
├── crawlo.cfg         # 框架配置文件
├── myproject/
│   ├── spiders/       # 爬虫脚本存放目录
│   ├── items.py       # 数据模型定义
│   ├── middlewares.py # 中间件定义
│   ├── pipelines.py   # 数据持久化定义
│   └── settings.py    # 项目全局设置
└── run.py             # 运行脚本
```

---

## 3. 编写您的第一个爬虫

打开 `myproject/spiders/example.py`，修改代码以提取数据：

```python
from crawlo import Spider
from crawlo.http import Request

class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['https://example.com']
    
    async def parse(self, response):
        # 使用 CSS 选择器提取标题
        title = response.css('h1::text').get()
        
        # 返回结果字典
        yield {
            'title': title,
            'url': response.url
        }
        
        # 自动发现并跟进链接
        for href in response.css('a::attr(href)').getall():
            yield Request(
                url=response.urljoin(href),
                callback=self.parse
            )
```

---

## 4. 运行爬虫

您可以直接通过命令行运行：

```bash
# 运行指定爬虫
crawlo run example

# 设置日志级别
crawlo run example --log-level DEBUG
```

或者使用项目根目录下的 `run.py` 脚本启动。

---

## 5. 下一步

- **[核心架构](architecture.md)**：了解 Crawlo 的内部数据流
- **[智能下载](advanced-features.md#hybrid-downloader)**：学习如何在协议与浏览器之间自动切换
- **[数据持久化](core-components.md#pipeline)**：配置 MySQL/MongoDB 存储
