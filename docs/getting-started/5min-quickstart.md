# 5分钟快速上手

欢迎使用 Crawlo！本教程将带你从零开始，在5分钟内完成第一个爬虫的开发和运行。

## ⏱️ 学习时长

**预计时间**：5分钟  
**前置要求**：Python 3.7+

---

## 第1步：安装 Crawlo（1分钟）

打开终端，运行以下命令：

```bash
# 基础安装
pip install crawlo
```

> 💡 **提示**：如果需要浏览器渲染支持（处理动态网页），可以安装完整版：
> ```bash
> pip install crawlo[render]
> playwright install  # 安装浏览器内核
> ```

**验证安装**：

```bash
crawlo --version
```

如果看到版本号，说明安装成功！✅

---

## 第2步：创建第一个项目（1分钟）

使用 Crawlo CLI 工具快速创建项目：

```bash
# 创建项目
crawlo startproject myproject

# 进入项目目录
cd myproject
```

**项目结构**：

```
myproject/
├── crawlo.cfg              # 框架配置文件
├── myproject/
│   ├── spiders/            # 爬虫代码目录
│   │   └── __init__.py
│   ├── items.py            # 数据模型
│   ├── middlewares.py      # 中间件
│   ├── pipelines.py        # 数据管道
│   └── settings.py         # 项目设置
└── run.py                  # 运行入口
```

---

## 第3步：生成爬虫模板（30秒）

使用 CLI 生成爬虫代码：

```bash
crawlo genspider quotes quotes.toscrape.com
```

这会在 `myproject/spiders/` 目录下生成 `quotes.py` 文件。

---

## 第4步：编写爬虫代码（2分钟）

打开 `myproject/spiders/quotes.py`，修改为以下代码：

```python
from crawlo import Spider
from crawlo import Request


class QuotesSpider(Spider):
    """名言爬虫"""
    
    name = 'quotes'  # 爬虫名称
    start_urls = ['https://quotes.toscrape.com/']  # 起始URL
    
    async def parse(self, response):
        """解析页面数据"""
        
        # 提取所有名言
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.css('small.author::text').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),
            }
        
        # 跟进下一页
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
```

**代码说明**：

- `name`: 爬虫唯一标识
- `start_urls`: 起始URL列表
- `parse()`: 解析响应的方法
- `response.css()`: CSS选择器提取数据
- `yield`: 返回数据或新请求

---

## 第5步：运行爬虫（30秒）

在项目根目录运行：

```bash
crawlo run quotes
```

**你会看到**：

```
2024-04-20 10:00:00 - INFO: Spider opened: quotes
2024-04-20 10:00:01 - INFO: Crawled (200) <GET https://quotes.toscrape.com/>
2024-04-20 10:00:01 - DEBUG: Scraped data: {'text': '...', 'author': '...', 'tags': [...]}
...
2024-04-20 10:00:10 - INFO: Closing spider: quotes
2024-04-20 10:00:10 - INFO: Spider closed: finished
```

---

## 第6步：保存数据（30秒）

Crawlo 使用 **Pipeline** 来处理和保存数据。在项目根目录创建或修改 `pipelines.py`：

```python
import json
from crawlo import Item


class JsonPipeline:
    """JSON文件导出管道"""
    
    def __init__(self):
        self.file = None
        self.items = []
    
    async def open_spider(self, spider):
        """爬虫启动时打开文件"""
        self.file = open('quotes.json', 'w', encoding='utf-8')
        self.items = []
    
    async def process_item(self, item, spider):
        """处理每个item"""
        self.items.append(dict(item))
        return item
    
    async def close_spider(self, spider):
        """爬虫关闭时保存文件"""
        json.dump(self.items, self.file, ensure_ascii=False, indent=2)
        self.file.close()
        spider.logger.info(f"已保存 {len(self.items)} 条数据到 quotes.json")
```

在 `settings.py` 中启用 Pipeline：

```python
PIPELINES = {
    'myproject.pipelines.JsonPipeline': 300,
}
```

然后运行爬虫：

```bash
crawlo run quotes
```

爬虫完成后，数据会自动保存到 `quotes.json` 文件中！

---

## 🎉 恭喜！

你已经完成了第一个 Crawlo 爬虫！

**你学会了**：
- ✅ 安装 Crawlo
- ✅ 创建项目
- ✅ 生成爬虫
- ✅ 编写代码
- ✅ 运行爬虫
- ✅ 保存数据

---

## 🚀 下一步

### 继续学习

1. **[安装指南](installation.md)** - 了解不同安装方式
2. **[创建第一个爬虫](first-spider.md)** - 深入学习爬虫开发
3. **[运行和调试](run-your-spider.md)** - 掌握调试技巧

### 进阶教程

- 📚 [教程系列](../tutorials/) - 从基础到生产
- 🎯 [使用指南](../guides/) - 解决具体问题
- 💡 [实战案例](../examples/) - 学习真实项目

### 常用配置

**调整并发数**（在 `settings.py` 中）：

```python
CONCURRENCY = 16  # 同时请求数
```

**添加下载延迟**：

```python
DOWNLOAD_DELAY = 1.0  # 每个请求间隔1秒
RANDOMNESS = True     # 随机抖动
```

**使用代理**：

```python
# 启用代理中间件
DOWNLOADER_MIDDLEWARES = {
    'crawlo.middleware.proxy.ProxyMiddleware': 350,
}

# 配置代理列表
PROXY_LIST = [
    'http://proxy1:8080',
    'http://proxy2:8080',
]

---

## 💡 常见问题

**Q: 爬虫没有数据输出？**  
A: 检查 CSS 选择器是否正确，可以使用 `response.css('selector').getall()` 调试。

**Q: 如何查看详细信息？**  
A: 添加 `--log-level DEBUG` 参数：
```bash
crawlo run quotes --log-level DEBUG
```

**Q: 网站有反爬怎么办？**  
A: 查看 [反检测中间件](../../crawlo/middleware/) 学习绕过技巧，或启用 `CloudflareBypassMiddleware`。

---

**遇到问题？** 查看 [常见问题 FAQ](../faq/) 获取帮助。
