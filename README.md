# Crawlo 爬虫框架

Crawlo 是一个高性能、可扩展的 Python 爬虫框架，支持单机和分布式部署。

## 特性

- 高性能异步爬取
- 支持多种下载器 (aiohttp, httpx, curl-cffi)
- 内置数据清洗和验证
- 分布式爬取支持
- 灵活的中间件系统
- 强大的配置管理系统
- 详细的日志记录和监控
- Windows 和 Linux 兼容

## 安装

```bash
pip install crawlo
```

或者从源码安装：

```bash
git clone git@github.com:crawl-coder/Crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

## 快速开始

```python
from crawlo import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # 解析逻辑
        pass

# 运行爬虫
# crawlo run example
```

更多示例请查看 [examples](examples/) 目录。

## Response 对象功能

Crawlo 框架对 Response 对象进行了增强，提供了更多便捷方法：

### URL 处理

使用 Response 对象封装的 URL 处理方法可以方便地处理各种 URL 操作，无需手动导入 `urllib.parse` 中的函数：

```python
class MySpider(Spider):
    def parse(self, response):
        # 1. 处理相对URL和绝对URL
        absolute_url = response.urljoin('/relative/path')
        
        # 2. 解析URL组件
        parsed = response.urlparse()  # 解析当前响应URL
        scheme = parsed.scheme
        domain = parsed.netloc
        path = parsed.path
        
        # 3. 解析查询参数
        query_params = response.parse_qs()  # 解析当前URL的查询参数
        
        # 4. 编码查询参数
        new_query = response.urlencode({'key': 'value', 'name': '测试'})
        
        # 5. URL编码/解码
        encoded = response.quote('hello world 你好')
        decoded = response.unquote(encoded)
        
        # 6. 移除URL片段
        url_without_fragment, fragment = response.urldefrag('http://example.com/path#section')
        
        yield Request(url=absolute_url, callback=self.parse_detail)
```

### 编码检测优化

Crawlo 框架对 Response 对象的编码检测功能进行了优化，提供了更准确和可靠的编码检测：

```python
class MySpider(Spider):
    def parse(self, response):
        # 自动检测响应编码
        encoding = response.encoding
        
        # 获取声明的编码（Request编码 > BOM > HTTP头部 > HTML meta标签）
        declared_encoding = response._declared_encoding()
        
        # 响应文本已自动使用正确的编码解码
        text = response.text
        
        # 处理解码后的内容
        # ...
```

编码检测优先级：
1. Request 中指定的编码
2. BOM 字节顺序标记
3. HTTP Content-Type 头部
4. HTML meta 标签声明
5. 内容自动检测
6. 默认编码 (utf-8)

### 选择器方法优化

Crawlo 框架对 Response 对象的选择器方法进行了优化，提供了更便捷的数据提取功能，方法命名更加直观和统一：

```python
class MySpider(Spider):
    def parse(self, response):
        # 1. 提取单个元素文本（支持CSS和XPath）
        title = response.extract_text('title')  # CSS选择器
        title = response.extract_text('//title')  # XPath选择器
        
        # 2. 提取多个元素文本
        paragraphs = response.extract_texts('.content p')  # CSS选择器
        paragraphs = response.extract_texts('//div[@class="content"]//p')  # XPath选择器
        
        # 3. 提取单个元素属性
        link_href = response.extract_attr('a', 'href')  # CSS选择器
        link_href = response.extract_attr('//a[@class="link"]', 'href')  # XPath选择器
        
        # 4. 提取多个元素属性
        all_links = response.extract_attrs('a', 'href')  # CSS选择器
        all_links = response.extract_attrs('//a[@class="link"]', 'href')  # XPath选择器
        
        yield {
            'title': title,
            'paragraphs': paragraphs,
            'links': all_links
        }
```

所有选择器方法都采用了简洁直观的命名风格，便于记忆和使用。

### 工具模块

Crawlo 框架提供了丰富的工具模块，用于处理各种常见任务。选择器相关的辅助函数现在位于 `crawlo.utils.selector_helper` 模块中：

```python
from crawlo.utils import (
    extract_text,
    extract_texts,
    extract_attr,
    extract_attrs,
    is_xpath
)

# 在自定义代码中使用这些工具函数
title_elements = response.css('title')
title_text = extract_text(title_elements)

li_elements = response.css('.list li')
li_texts = extract_texts(li_elements)

link_elements = response.css('.link')
link_href = extract_attr(link_elements, 'href')

all_links = response.css('a')
all_hrefs = extract_attrs(all_links, 'href')
```

## 日志系统

Crawlo 拥有一个功能强大的日志系统，支持多种配置选项：

### 基本配置

```python
from crawlo.logging import configure_logging, get_logger

# 配置日志系统
configure_logging(
    LOG_LEVEL='INFO',
    LOG_FILE='logs/app.log',
    LOG_MAX_BYTES=10*1024*1024,  # 10MB
    LOG_BACKUP_COUNT=5
)

# 获取logger
logger = get_logger('my_module')
logger.info('这是一条日志消息')
```

### 高级配置

```python
# 分别配置控制台和文件日志级别
configure_logging(
    LOG_LEVEL='INFO',
    LOG_CONSOLE_LEVEL='WARNING',  # 控制台只显示WARNING及以上级别
    LOG_FILE_LEVEL='DEBUG',       # 文件记录DEBUG及以上级别
    LOG_FILE='logs/app.log',
    LOG_INCLUDE_THREAD_ID=True,   # 包含线程ID
    LOG_INCLUDE_PROCESS_ID=True   # 包含进程ID
)

# 模块特定日志级别
configure_logging(
    LOG_LEVEL='WARNING',
    LOG_LEVELS={
        'my_module.debug': 'DEBUG',
        'my_module.info': 'INFO'
    }
)
```

### 性能监控

```python
from crawlo.logging import get_monitor

# 启用日志性能监控
monitor = get_monitor()
monitor.enable_monitoring()

# 获取性能报告
report = monitor.get_performance_report()
print(report)
```

### 日志采样

```python
from crawlo.logging import get_sampler

# 设置采样率（只记录30%的日志）
sampler = get_sampler()
sampler.set_sample_rate('my_module', 0.3)

# 设置速率限制（每秒最多100条日志）
sampler.set_rate_limit('my_module', 100)
```

## Windows 兼容性说明

在 Windows 系统上使用日志轮转功能时，可能会遇到文件锁定问题。为了解决这个问题，建议安装 `concurrent-log-handler` 库：

```bash
pip install concurrent-log-handler
```

Crawlo 框架会自动检测并使用这个库来提供更好的 Windows 兼容性。

如果未安装 `concurrent-log-handler`，在 Windows 上运行时可能会出现以下错误：
```bash
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。
```

## 爬虫自动发现

Crawlo 框架支持通过 `SPIDER_MODULES` 配置自动发现和加载爬虫，类似于其他主流爬虫框架的机制：

```python
# settings.py
SPIDER_MODULES = [
    'myproject.spiders',
    'myproject.more_spiders',
]

SPIDER_LOADER_WARN_ONLY = True  # 加载错误时只警告不报错
```

框架会自动扫描配置的模块目录，发现并注册其中的爬虫类。

## 文档

请查看 [文档](http://localhost:8000) 获取更多信息。

构建文档:
```bash
mkdocs serve
```

然后在浏览器中打开 http://localhost:8000 查看文档。

您也可以查看在线文档：
- [中文文档](https://crawlo.readthedocs.io/en/latest/README_zh/)
- [English Documentation](https://crawlo.readthedocs.io/en/latest/)

## 文档目录

### 核心概念
- [架构概述](docs/modules/architecture/index.md) - Crawlo 的整体架构设计
- [运行模式](docs/modules/architecture/modes.md) - 单机与分布式模式详解
- [配置系统](docs/modules/configuration/index.md) - 配置管理与验证

### 核心模块
- [引擎 (Engine)](docs/modules/core/engine.md) - 爬取过程的核心协调器
- [调度器 (Scheduler)](docs/modules/core/scheduler.md) - 请求队列与去重管理
- [处理器 (Processor)](docs/modules/core/processor.md) - 响应处理与数据提取
- [爬虫基类 (Spider)](docs/modules/core/spider.md) - 爬虫基础类与生命周期

### 功能模块
- [下载器 (Downloader)](docs/modules/downloader/index.md) - HTTP 客户端实现
- [队列 (Queue)](docs/modules/queue/index.md) - 请求队列管理
- [过滤器 (Filter)](docs/modules/filter/index.md) - 请求去重功能
- [中间件 (Middleware)](docs/modules/middleware/index.md) - 请求/响应处理组件
- [管道 (Pipeline)](docs/modules/pipeline/index.md) - 数据处理和存储组件
- [扩展 (Extension)](docs/modules/extension/index.md) - 附加功能和监控组件

### 命令行工具
- [CLI 概述](docs/modules/cli/index.md) - 命令行工具使用指南
- [startproject](docs/modules/cli/startproject.md) - 项目初始化命令
- [genspider](docs/modules/cli/genspider.md) - 爬虫生成命令
- [run](docs/modules/cli/run.md) - 爬虫运行命令
- [list](docs/modules/cli/list.md) - 查看爬虫列表
- [check](docs/modules/cli/check.md) - 配置检查命令
- [stats](docs/modules/cli/stats.md) - 统计信息查看

### 高级主题
- [分布式部署](docs/modules/advanced/distributed.md) - 分布式爬取配置与部署
- [性能优化](docs/modules/advanced/performance.md) - 性能调优指南
- [故障排除](docs/modules/advanced/troubleshooting.md) - 常见问题与解决方案
- [最佳实践](docs/modules/advanced/best_practices.md) - 开发最佳实践

### API 参考
- [完整 API 文档](docs/api/) - 详细的类和方法参考

## 学习路径

如果您是 Crawlo 的新用户，建议按以下顺序学习：

1. **入门** - 阅读快速开始指南，运行第一个示例
2. **核心概念** - 了解框架架构和基本概念
3. **核心模块** - 深入学习引擎、调度器、处理器等核心组件
4. **功能模块** - 根据需求学习下载器、队列、过滤器等模块
5. **高级主题** - 掌握分布式部署、性能优化等高级功能

## 贡献

我们欢迎社区贡献！如果您想为 Crawlo 做出贡献：

1. Fork 项目仓库
2. 创建功能分支
3. 提交您的更改
4. 发起 Pull Request

## 许可证

MIT