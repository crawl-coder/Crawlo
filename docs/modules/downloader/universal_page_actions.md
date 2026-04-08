# 通用页面操作指南

## 概述

现在 Crawlo 框架的 **Playwright** 和 **DrissionPage** 下载器支持使用统一的页面操作配置。无论使用哪种下载器，都可以使用相同的操作序列来控制浏览器行为。

## 快速开始

### 1. 使用 `dynamic_actions`（推荐）

在 Spider 中，通过 `meta` 参数传递 `dynamic_actions`：

```python
from crawlo import Spider, Request

class MySpider(Spider):
    def parse(self, response):
        yield Request(
            url='https://example.com',
            callback=self.parse_next,
            meta={
                'dynamic_actions': [
                    # 滚动到底部
                    {
                        'type': 'scroll_to_bottom',
                        'params': {
                            'scroll_delay': 500,
                            'max_no_content': 2
                        }
                    },
                    # 点击按钮
                    {
                        'type': 'click_and_wait',
                        'params': {
                            'selector': '//button[text()="加载更多"]',
                            'wait_timeout': 3000,
                            'wait_for': 'networkidle'
                        }
                    }
                ]
            }
        )
```

### 2. 选择器支持

通用操作处理器**自动识别** XPath 和 CSS 选择器：

```python
# XPath 选择器（自动识别）
'selector': '//div[@class="btn"]'
'selector': '//div[contains(@class, "more")]'
'selector': 'xpath=//div[@id="main"]'

# CSS 选择器（自动识别）
'selector': '.btn-primary'
'selector': '#main-content'
'selector': 'css=div.container'
```

## 支持的操作类型

### 1. `scroll_to_bottom` - 智能滚动到底部

适合懒加载页面，自动检测是否到达底部。

```python
{
    'type': 'scroll_to_bottom',
    'params': {
        'scroll_delay': 500,        # 每次滚动后等待时间（毫秒）
        'max_no_content': 2         # 连续无新内容的最大次数
    }
}
```

### 2. `click` - 点击元素

点击页面上的元素（按钮、链接等）。

```python
{
    'type': 'click',
    'params': {
        'selector': '.next-button',  # XPath 或 CSS 选择器
        'wait_timeout': 1000         # 点击后等待时间（毫秒）
    }
}
```

### 3. `click_and_wait` - 点击并等待

点击元素并等待新内容加载（适合翻页）。

```python
{
    'type': 'click_and_wait',
    'params': {
        'selector': '//a[text()="下一页"]',
        'wait_timeout': 3000,        # 等待超时（毫秒）
        'wait_for': 'networkidle',   # 等待策略: networkidle, domcontentloaded
        'before_count': '() => document.querySelectorAll(".item").length'  # 可选：验证新内容
    }
}
```

### 4. `wait` - 等待

简单的等待操作。

```python
{
    'type': 'wait',
    'params': {
        'timeout': 1000  # 等待时间（毫秒）
    }
}
```

### 5. `scroll` - 滚动

控制页面滚动。

```python
{
    'type': 'scroll',
    'params': {
        'position': 'bottom'  # 'top' 或 'bottom'
    }
}
```

### 6. `fill` - 填充表单

向输入框填充文本。

```python
{
    'type': 'fill',
    'params': {
        'selector': '#search-input',
        'value': '搜索关键词'
    }
}
```

### 7. `evaluate` - 执行 JavaScript

执行自定义 JavaScript 代码。

```python
{
    'type': 'evaluate',
    'params': {
        'script': 'window.scrollTo(0, document.body.scrollHeight)'
    }
}
```

## 完整示例

### 示例 1：滚动加载 + 点击翻页

```python
yield Request(
    url='https://example.com/articles',
    callback=self.parse_articles,
    meta={
        'page': current_page + 1,
        'max_pages': 5,
        'dynamic_actions': [
            # 1. 智能滚动到底部，触发懒加载
            {
                'type': 'scroll_to_bottom',
                'params': {
                    'scroll_delay': 500,
                    'max_no_content': 2
                }
            },
            # 2. 等待内容渲染
            {
                'type': 'wait',
                'params': {
                    'timeout': 1000
                }
            },
            # 3. 点击"加载更多"按钮
            {
                'type': 'click_and_wait',
                'params': {
                    'selector': '//button[contains(text(), "加载更多")]',
                    'wait_timeout': 3000,
                    'wait_for': 'networkidle'
                }
            }
        ]
    }
)
```

### 示例 2：表单提交

```python
yield Request(
    url='https://example.com/search',
    callback=self.parse_results,
    meta={
        'dynamic_actions': [
            # 1. 填充搜索框
            {
                'type': 'fill',
                'params': {
                    'selector': '#search-input',
                    'value': 'Python 爬虫'
                }
            },
            # 2. 等待输入完成
            {
                'type': 'wait',
                'params': {
                    'timeout': 500
                }
            },
            # 3. 点击搜索按钮
            {
                'type': 'click_and_wait',
                'params': {
                    'selector': '#search-button',
                    'wait_timeout': 3000,
                    'wait_for': 'networkidle'
                }
            }
        ]
    }
)
```

### 示例 3：复杂翻页逻辑

```python
def parse_list(self, response):
    # 提取当前页数据
    items = response.xpath('//div[@class="item"]')
    for item in items:
        yield {'title': item.xpath('.//h3/text()').get()}
    
    # 翻页
    current_page = response.meta.get('page', 1)
    if current_page < 10:
        yield Request(
            url=response.url,
            callback=self.parse_list,
            dont_filter=True,
            meta={
                'page': current_page + 1,
                'dynamic_actions': [
                    # 滚动到底部
                    {
                        'type': 'scroll_to_bottom',
                        'params': {'scroll_delay': 300}
                    },
                    # 点击下一页
                    {
                        'type': 'click_and_wait',
                        'params': {
                            'selector': 'a.next-page',
                            'wait_for': 'networkidle'
                        }
                    }
                ]
            }
        )
```

## 向后兼容性

通用操作处理器**完全向后兼容**旧的配置方式：

```python
# 旧的方式（仍然有效）
meta={'playwright_actions': [...]}
meta={'drissionpage_actions': [...]}

# 新的推荐方式
meta={'dynamic_actions': [...]}
```

优先级：`dynamic_actions` > `playwright_actions` > `drissionpage_actions`

## 选择器最佳实践

### 1. 使用 XPath 的场景

- 需要通过文本内容定位元素
- 需要复杂的层级关系
- 需要多个条件组合

```python
'//div[contains(@class, "btn") and text()="提交"]'
'//ul[@class="list"]/li[3]/a'
'//input[@name="username"]'
```

### 2. 使用 CSS 的场景

- 简单的类名或 ID 选择
- 性能要求较高
- 选择器较简单

```python
'.btn-primary'
'#main-content'
'div.container > ul.list > li:nth-child(3)'
```

## 技术实现

通用页面操作由以下组件实现：

1. **PageActionHandler** - 统一的操作处理器
   - 兼容多种键名
   - 提取和管理选择器

2. **SelectorConverter** - 选择器转换器
   - 自动检测 XPath/CSS
   - 标准化选择器格式

3. **下载器集成**
   - PlaywrightDownloader: 使用 `page.locator('xpath=...')` 或 `page.click()`
   - DrissionPageDownloader: 使用 `page.ele('xpath:...')` 或 `page.ele()`

## 常见问题

### Q: 我的 XPath 不工作怎么办？

确保 XPath 语法正确，可以使用浏览器开发者工具测试：

```python
# 在浏览器控制台测试
$x('//div[@class="test"]')
```

### Q: 如何调试操作执行？

启用详细日志：

```python
# settings.py
HYBRID_VERBOSE_LOGGING = True
```

### Q: 操作执行失败会中断下载吗？

不会。单个操作失败会被记录为警告，不会中断整个下载流程。

## 更多资源

- 查看 [infoq_spider.py](file:///d:/dowell/others/Crawlo/examples/infoq_dynamic_test/infoq_dynamic_test/spiders/infoq_spider.py) 完整示例
- 运行测试：`python tests/test_page_action_handler.py`
- 查看实现：[page_action_handler.py](file:///d:/dowell/others/Crawlo/crawlo/downloader/page_action_handler.py)
