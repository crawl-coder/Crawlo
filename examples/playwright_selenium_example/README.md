# Playwright 和 Selenium 下载器使用说明

## 概述

Crawlo 框架提供了两种支持动态内容加载的下载器：

1. **PlaywrightDownloader** - 基于 Playwright 实现，性能更优
2. **SeleniumDownloader** - 基于 Selenium WebDriver 实现，兼容性更好

这两种下载器都支持处理 JavaScript 渲染的网页内容，适用于需要等待页面完全加载或执行交互操作的场景。

## 安装依赖

在使用这些下载器之前，需要安装相应的依赖：

```bash
# 安装 Playwright 依赖
pip install playwright
playwright install chromium firefox webkit

# 安装 Selenium 依赖
pip install selenium
# 根据使用的浏览器下载对应的 WebDriver
```

## 配置下载器

### 1. Playwright 下载器配置

在 settings.py 中配置：

```python
# 使用 Playwright 下载器
DOWNLOADER = 'crawlo.downloader.playwright_downloader.PlaywrightDownloader'

# Playwright 配置选项
PLAYWRIGHT_BROWSER_TYPE = "chromium"  # 浏览器类型: chromium, firefox, webkit
PLAYWRIGHT_HEADLESS = True           # 是否无头模式
PLAYWRIGHT_TIMEOUT = 30000          # 超时时间（毫秒）
PLAYWRIGHT_LOAD_TIMEOUT = 10000     # 页面加载超时时间（毫秒）
PLAYWRIGHT_VIEWPORT_WIDTH = 1920    # 视口宽度
PLAYWRIGHT_VIEWPORT_HEIGHT = 1080   # 视口高度
PLAYWRIGHT_WAIT_FOR_ELEMENT = None  # 等待特定元素选择器
PLAYWRIGHT_PROXY = None             # 代理设置
PLAYWRIGHT_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 10  # 单浏览器最大页面数量
```

### 2. Selenium 下载器配置

在 settings.py 中配置：

```python
# 使用 Selenium 下载器
DOWNLOADER = 'crawlo.downloader.selenium_downloader.SeleniumDownloader'

# Selenium 配置选项
SELENIUM_BROWSER_TYPE = "chrome"     # 浏览器类型: chrome, firefox, edge
SELENIUM_HEADLESS = True            # 是否无头模式
SELENIUM_TIMEOUT = 30               # 超时时间（秒）
SELENIUM_LOAD_TIMEOUT = 10          # 页面加载超时时间（秒）
SELENIUM_WINDOW_WIDTH = 1920       # 窗口宽度
SELENIUM_WINDOW_HEIGHT = 1080      # 窗口高度
SELENIUM_WAIT_FOR_ELEMENT = None   # 等待特定元素选择器
SELENIUM_ENABLE_JS = True          # 是否启用JavaScript
SELENIUM_PROXY = None              # 代理设置
SELENIUM_SINGLE_BROWSER_MODE = True  # 单浏览器多标签页模式
SELENIUM_MAX_TABS_PER_BROWSER = 10   # 单浏览器最大标签页数量
```

## 使用示例

### 1. 基本使用

在 Spider 中创建请求：

```python
from crawlo.spider import Spider
from crawlo.network.request import Request

class MySpider(Spider):
    name = 'my_spider'
    
    def start_requests(self):
        yield Request(
            url='https://example.com',
            callback=self.parse
        )
    
    def parse(self, response):
        # 处理解析逻辑
        pass
```

### 2. 使用自定义操作

#### Playwright 自定义操作

```python
def start_requests(self):
    yield Request(
        url='https://example.com',
        callback=self.parse,
        meta={
            # Playwright 自定义操作
            'playwright_actions': [
                # 点击元素
                {
                    'type': 'click',
                    'params': {
                        'selector': '#button-id'
                    }
                },
                # 填充表单
                {
                    'type': 'fill',
                    'params': {
                        'selector': '#input-id',
                        'value': 'test value'
                    }
                },
                # 等待
                {
                    'type': 'wait',
                    'params': {
                        'timeout': 2000  # 毫秒
                    }
                },
                # 执行 JavaScript
                {
                    'type': 'evaluate',
                    'params': {
                        'script': 'document.title'
                    }
                },
                # 滚动页面
                {
                    'type': 'scroll',
                    'params': {
                        'position': 'bottom'
                    }
                }
            ],
            # Playwright 翻页操作
            'pagination_actions': [
                {
                    'type': 'scroll',
                    'params': {
                        'count': 3,
                        'distance': 500,
                        'delay': 1000
                    }
                }
            ]
        }
    )
```

#### Selenium 自定义操作

```python
def start_requests(self):
    yield Request(
        url='https://example.com',
        callback=self.parse,
        meta={
            # Selenium 自定义脚本
            'selenium_scripts': [
                # 执行 JavaScript
                {
                    'type': 'js',
                    'content': 'document.querySelector("#button-id").click();'
                },
                # 等待
                {
                    'type': 'wait',
                    'content': 2  # 秒
                }
            ],
            # Selenium 翻页操作
            'pagination_actions': [
                {
                    'type': 'scroll',
                    'params': {
                        'count': 3,
                        'distance': 500,
                        'delay': 1  # 秒
                    }
                },
                {
                    'type': 'click',
                    'params': {
                        'selector': '.next-page',
                        'count': 1,
                        'delay': 1  # 秒
                    }
                }
            ]
        }
    )
```

## 性能优化建议

### 1. 单浏览器多标签页模式

两种下载器都支持单浏览器多标签页模式，可以显著减少浏览器启动开销：

```python
# Playwright 配置
PLAYWRIGHT_SINGLE_BROWSER_MODE = True
PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 10

# Selenium 配置
SELENIUM_SINGLE_BROWSER_MODE = True
SELENIUM_MAX_TABS_PER_BROWSER = 10
```

### 2. 无头模式

在生产环境中建议使用无头模式以提高性能：

```python
# Playwright
PLAYWRIGHT_HEADLESS = True

# Selenium
SELENIUM_HEADLESS = True
```

### 3. 合理设置超时时间

根据目标网站的响应速度合理设置超时时间：

```python
# Playwright
PLAYWRIGHT_TIMEOUT = 30000  # 30秒
PLAYWRIGHT_LOAD_TIMEOUT = 10000  # 10秒

# Selenium
SELENIUM_TIMEOUT = 30  # 30秒
SELENIUM_LOAD_TIMEOUT = 10  # 10秒
```

## 注意事项

1. **资源管理**：动态下载器会消耗更多系统资源，请合理控制并发数
2. **错误处理**：动态内容加载可能失败，建议添加重试机制
3. **代理支持**：两种下载器都支持代理配置，但配置方式略有不同
4. **浏览器兼容性**：Playwright 支持更多浏览器引擎，Selenium 兼容性更好
5. **性能差异**：Playwright 性能通常优于 Selenium，但 Selenium 生态更成熟

## 运行示例

```bash
cd examples/playwright_selenium_example
python playwright_selenium_example/run.py
```

选择相应的下载器进行测试。