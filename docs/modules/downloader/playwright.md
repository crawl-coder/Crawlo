# PlaywrightDownloader

PlaywrightDownloader 是 Crawlo 框架中基于 Playwright 的现代浏览器自动化下载器，提供了比 Selenium 更好的性能和更简单的 API。

## 概述

PlaywrightDownloader 基于 Microsoft 的 Playwright 框架，支持多种浏览器（Chromium、Firefox、WebKit），具有更快的执行速度和更低的资源消耗。

### 核心特性

1. **多浏览器支持** - 支持 Chromium、Firefox、WebKit
2. **高性能** - 比 Selenium 更快的执行速度
3. **低资源消耗** - 相比 Selenium 消耗更少资源
4. **现代化 API** - 简洁易用的 API 设计
5. **移动端支持** - 支持设备模拟和移动端浏览器

## 配置选项

PlaywrightDownloader 的行为可以通过以下配置项进行调整：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| PLAYWRIGHT_BROWSER | str | 'chromium' | 浏览器类型 (chromium/firefox/webkit) |
| PLAYWRIGHT_HEADLESS | bool | True | 是否启用无头模式 |
| PLAYWRIGHT_VIEWPORT | dict | {'width': 1920, 'height': 1080} | 浏览器视口大小 |
| PLAYWRIGHT_TIMEOUT | int | 30000 | 操作超时时间（毫秒） |
| PLAYWRIGHT_SLOW_MO | int | 0 | 慢动作模式延迟（毫秒） |

## 使用示例

### 基本使用

```python
from crawlo.config import CrawloConfig

# 配置使用 Playwright 下载器
config = CrawloConfig.standalone(
    downloader_type='playwright',
    playwright_browser='chromium',
    playwright_headless=True
)
```

### 高级配置

```python
# 配置浏览器选项
config = CrawloConfig.standalone(
    downloader_type='playwright',
    playwright_browser='firefox',
    playwright_headless=False,
    playwright_viewport={'width': 1366, 'height': 768},
    playwright_timeout=60000
)
```

## 性能优势

### 与 Selenium 对比

| 特性 | Playwright | Selenium |
|------|------------|----------|
| 启动时间 | 1-2 秒 | 5-10 秒 |
| 内存消耗 | 低 | 高 |
| 执行速度 | 快 | 中等 |
| API 复杂度 | 简单 | 复杂 |
| 移动端支持 | 原生支持 | 需要额外配置 |

### 资源管理

```python
# Playwright 的资源管理更加高效
config = CrawloConfig.standalone(
    downloader_type='playwright',
    concurrency=5,  # 可以使用更高并发
    download_delay=1.0
)
```

## 最佳实践

### 1. 浏览器选择

```python
# 根据需求选择合适的浏览器
# Chromium - 性能最佳，兼容性好
config = CrawloConfig.standalone(playwright_browser='chromium')

# Firefox - 开源选择
config = CrawloConfig.standalone(playwright_browser='firefox')

# WebKit - 用于 Safari 兼容性测试
config = CrawloConfig.standalone(playwright_browser='webkit')
```

### 2. 设备模拟

```python
# 移动端设备模拟
config = CrawloConfig.standalone(
    playwright_browser='chromium',
    playwright_viewport={
        'width': 375,
        'height': 812,
        'isMobile': True,
        'hasTouch': True
    }
)
```

### 3. 错误处理

```python
# 处理 Playwright 相关异常
def parse_with_playwright(self, response):
    try:
        # 浏览器操作
        yield self.extract_data(response)
    except TimeoutError as e:
        self.logger.error(f"操作超时: {e}")
        # 可以选择重试
    except Error as e:
        self.logger.error(f"Playwright 错误: {e}")
        # 处理其他 Playwright 错误
```

### 4. 上下文管理

```python
# 合理使用浏览器上下文
class EfficientSpider(Spider):
    async def parse(self, response):
        # 创建新的浏览器上下文
        context = await self.playwright.new_context(
            user_agent='Custom User Agent',
            viewport={'width': 1920, 'height': 1080}
        )
        
        try:
            # 在上下文中执行操作
            page = await context.new_page()
            await page.goto(response.url)
            # 提取数据
            yield self.extract_data(page)
        finally:
            # 确保上下文被关闭
            await context.close()
```