# SeleniumDownloader

SeleniumDownloader 是 Crawlo 框架中基于 Selenium 的浏览器自动化下载器，适用于需要执行 JavaScript 或模拟用户交互的复杂网页爬取场景。

## 概述

SeleniumDownloader 提供了完整的浏览器环境，能够执行 JavaScript、处理 AJAX 请求、模拟用户交互操作，适用于现代 Web 应用的爬取需求。

### 核心特性

1. **完整浏览器环境** - 提供真实的浏览器环境
2. **JavaScript 执行** - 支持复杂的 JavaScript 执行
3. **用户交互模拟** - 支持点击、输入、滚动等用户操作
4. **等待机制** - 支持显式和隐式等待
5. **多浏览器支持** - 支持 Chrome、Firefox 等主流浏览器

## 配置选项

SeleniumDownloader 的行为可以通过以下配置项进行调整：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| SELENIUM_BROWSER | str | 'chrome' | 浏览器类型 (chrome/firefox) |
| SELENIUM_HEADLESS | bool | True | 是否启用无头模式 |
| SELENIUM_WINDOW_SIZE | tuple | (1920, 1080) | 浏览器窗口大小 |
| SELENIUM_TIMEOUT | int | 30 | 页面加载超时时间 |
| SELENIUM_IMPLICIT_WAIT | int | 10 | 隐式等待时间 |

## 使用示例

### 基本使用

```python
from crawlo.config import CrawloConfig

# 配置使用 Selenium 下载器
config = CrawloConfig.standalone(
    downloader_type='selenium',
    selenium_browser='chrome',
    selenium_headless=True
)
```

### 高级配置

```python
# 配置浏览器选项
config = CrawloConfig.standalone(
    downloader_type='selenium',
    selenium_browser='firefox',
    selenium_headless=False,
    selenium_window_size=(1366, 768),
    selenium_timeout=60
)
```

## 性能考虑

### 资源消耗

SeleniumDownloader 相比其他下载器资源消耗较高：

- **内存使用** - 每个浏览器实例消耗 100-200MB 内存
- **CPU 使用** - 启动和运行时 CPU 使用率较高
- **启动时间** - 浏览器启动需要 5-10 秒

### 并发限制

由于资源消耗较高，建议限制并发数：

```python
# 限制并发数
config = CrawloConfig.standalone(
    downloader_type='selenium',
    concurrency=2,  # 低并发
    download_delay=2.0  # 增加延迟
)
```

## 最佳实践

### 1. 选择性使用

```python
# 只对需要的请求使用 Selenium
class SelectiveSpider(Spider):
    def parse(self, response):
        # 检查是否需要浏览器环境
        if self.needs_browser(response):
            # 使用 Selenium 请求
            yield Request(
                url=response.url,
                callback=self.parse_with_browser,
                meta={'use_selenium': True}
            )
        else:
            # 使用普通请求
            yield Request(
                url=response.url,
                callback=self.parse_normal
            )
```

### 2. 资源管理

```python
# 合理管理浏览器实例
class EfficientSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.browser_pool = []
    
    def closed(self, reason):
        # 关闭所有浏览器实例
        for browser in self.browser_pool:
            browser.quit()
        super().closed(reason)
```

### 3. 错误处理

```python
# 处理浏览器相关异常
def parse_with_browser(self, response):
    try:
        # 浏览器操作
        yield self.extract_data(response)
    except WebDriverException as e:
        self.logger.error(f"浏览器操作失败: {e}")
        # 可以选择重启浏览器或跳过
    except TimeoutException as e:
        self.logger.warning(f"页面加载超时: {e}")
        # 可以选择重试
```