# 混合下载器使用指南

混合下载器（Hybrid Downloader）是 Crawlo 框架中一个强大的功能，它能够根据请求的特征智能选择合适的下载器来处理不同类型的网页内容。本文档将详细介绍如何配置和使用混合下载器。

## 1. 概述

混合下载器的主要优势在于它能够：

1. **智能选择**：根据 URL 模式、域名或请求标记自动选择最合适的下载器
2. **性能优化**：对静态内容使用高性能的协议下载器，对动态内容使用浏览器下载器
3. **资源管理**：统一管理不同类型的下载器资源
4. **灵活配置**：支持多种配置方式来适应不同的业务场景

## 2. 支持的下载器类型

混合下载器支持以下类型的下载器：

### 协议下载器（用于静态内容）
- `aiohttp`：基于 aiohttp 的高性能异步下载器
- `httpx`：支持 HTTP/2 的现代异步下载器
- `curl_cffi`：支持浏览器指纹模拟的下载器

### 动态下载器（用于 JavaScript 渲染内容）
- `selenium`：基于 Selenium WebDriver 的下载器
- `playwright`：基于 Playwright 的高性能下载器

## 3. 配置混合下载器

### 3.1 基本配置

要在项目中启用混合下载器，需要在配置文件或爬虫的 `custom_settings` 中进行配置：

```python
# 在 settings.py 或 Spider.custom_settings 中
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',  # 指定使用混合下载器
    'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',  # 默认协议下载器
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',  # 默认动态下载器
}
```

### 3.2 URL 模式配置

可以通过配置 URL 模式来指定哪些 URL 应该使用动态下载器：

```python
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',
    'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    # 动态加载URL模式
    'HYBRID_DYNAMIC_URL_PATTERNS': [
        r'/product/',      # 产品详情页
        r'/item/',         # 商品详情页
        r'/detail/',       # 详情页
        r'\.dynamic$',     # 以.dynamic结尾的URL
    ],
    # 协议加载URL模式
    'HYBRID_PROTOCOL_URL_PATTERNS': [
        r'/list/',         # 列表页
        r'/category/',     # 分类页
        r'/search/',       # 搜索页
        r'\.html$',        # 以.html结尾的URL
    ]
}
```

### 3.3 域名配置

可以通过配置域名来指定哪些网站应该使用动态下载器：

```python
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',
    'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    # 动态加载域名
    'HYBRID_DYNAMIC_DOMAINS': [
        'dynamic-shop.com',
        'social-media.com',
        'interactive-site.com',
    ],
    # 协议加载域名
    'HYBRID_PROTOCOL_DOMAINS': [
        'static-news.com',
        'blog-platform.com',
        'simple-site.com',
    ]
}
```

## 4. 使用场景适配器

为了简化配置，Crawlo 提供了场景适配器来自动配置混合下载器：

```python
from crawlo.tools.scenario_adapter import create_adapter_for_platform

class MySpider(Spider):
    name = 'my_spider'
    
    # 使用电商平台预设配置
    custom_settings = create_adapter_for_platform("电商网站").get_settings()
    custom_settings['DOWNLOADER_TYPE'] = 'hybrid'
    custom_settings['HYBRID_DEFAULT_PROTOCOL_DOWNLOADER'] = 'httpx'
    custom_settings['HYBRID_DEFAULT_DYNAMIC_DOWNLOADER'] = 'playwright'
    
    def start_requests(self):
        urls = [
            'https://shop.com/products/list',    # 列表页 - 使用协议下载器
            'https://shop.com/product/12345',    # 详情页 - 使用动态下载器
        ]
        
        # 使用场景适配器自动配置请求
        adapter = create_adapter_for_platform("电商网站")
        for url in urls:
            request = Request(url=url, callback=self.parse)
            adapter.adapt_request(request)
            yield request
```

## 5. 手动指定下载器

在某些情况下，您可能需要手动指定某个请求使用特定的下载器：

```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    }
    
    def start_requests(self):
        # 强制使用动态下载器
        dynamic_request = Request(
            url='https://example.com/dynamic-page',
            callback=self.parse_dynamic
        ).set_dynamic_loader(True, {"wait_for_element": ".content"})
        
        # 强制使用协议下载器
        protocol_request = Request(
            url='https://example.com/static-page',
            callback=self.parse_static
        ).set_protocol_loader()
        
        yield dynamic_request
        yield protocol_request
    
    def parse_dynamic(self, response):
        # 处理动态内容
        pass
    
    def parse_static(self, response):
        # 处理静态内容
        pass
```

## 6. 翻页操作支持

混合下载器支持多种翻页操作，包括鼠标滑动和点击翻页，适用于动态加载内容的场景。

### 6.1 翻页操作配置

在动态下载器中，可以通过配置来指定翻页操作：

```python
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    
    # Playwright 翻页配置
    'PLAYWRIGHT_PAGINATION': {
        'scroll_to_bottom': True,  # 自动滚动到底部加载更多内容
        'scroll_wait_time': 2,     # 滚动后等待时间（秒）
        'max_scrolls': 5,          # 最大滚动次数
        'click_next_selector': '.next-page',  # 点击下一页按钮的选择器
        'click_wait_time': 3,      # 点击后等待时间（秒）
        'max_clicks': 10,          # 最大点击次数
    },
    
    # Selenium 翻页配置
    'SELENIUM_PAGINATION': {
        'scroll_to_bottom': True,
        'scroll_wait_time': 2,
        'max_scrolls': 5,
        'click_next_selector': '.next-page',
        'click_wait_time': 3,
        'max_clicks': 10,
    }
}
```

### 6.2 在请求中指定翻页操作

可以在单个请求中指定特定的翻页操作：

```python
class PaginationSpider(Spider):
    name = 'pagination_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    }
    
    def start_requests(self):
        # 滑动翻页请求
        scroll_request = Request(
            url='https://example.com/infinite-scroll-page',
            callback=self.parse_scroll
        ).set_dynamic_loader(True, {
            "pagination": {
                "type": "scroll",
                "scroll_to_bottom": True,
                "scroll_wait_time": 2,
                "max_scrolls": 3
            }
        })
        
        # 点击翻页请求
        click_request = Request(
            url='https://example.com/click-pagination-page',
            callback=self.parse_click
        ).set_dynamic_loader(True, {
            "pagination": {
                "type": "click",
                "click_next_selector": ".next-page",
                "click_wait_time": 3,
                "max_clicks": 5
            }
        })
        
        yield scroll_request
        yield click_request
    
    def parse_scroll(self, response):
        # 处理滑动翻页内容
        items = response.css('.item')
        for item in items:
            yield {
                'title': item.css('.title::text').get(),
                'content': item.css('.content::text').get(),
            }
    
    def parse_click(self, response):
        # 处理点击翻页内容
        items = response.css('.item')
        for item in items:
            yield {
                'title': item.css('.title::text').get(),
                'content': item.css('.content::text').get(),
            }
```

### 6.3 组合翻页操作

对于复杂的翻页场景，可以组合使用滑动和点击操作：

```python
class ComplexPaginationSpider(Spider):
    name = 'complex_pagination_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    }
    
    def start_requests(self):
        # 组合翻页请求
        complex_request = Request(
            url='https://example.com/complex-pagination-page',
            callback=self.parse_complex
        ).set_dynamic_loader(True, {
            "pagination": {
                "type": "mixed",
                "scroll_to_bottom": True,
                "scroll_wait_time": 2,
                "max_scrolls_before_click": 2,
                "click_next_selector": ".next-page",
                "click_wait_time": 3,
                "max_clicks": 5
            }
        })
        
        yield complex_request
    
    def parse_complex(self, response):
        # 处理组合翻页内容
        items = response.css('.item')
        for item in items:
            yield {
                'title': item.css('.title::text').get(),
                'content': item.css('.content::text').get(),
            }
```

## 7. 高级配置选项

### 7.1 动态下载器配置

```python
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',
    'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    
    # Playwright 配置
    'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
    'PLAYWRIGHT_HEADLESS': True,
    'PLAYWRIGHT_TIMEOUT': 30000,
    'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
    'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 5,
    
    # Selenium 配置（如果使用 Selenium）
    'SELENIUM_BROWSER_TYPE': 'chrome',
    'SELENIUM_HEADLESS': True,
    'SELENIUM_TIMEOUT': 30,
    'SELENIUM_SINGLE_BROWSER_MODE': True,
    'SELENIUM_MAX_TABS_PER_BROWSER': 5,
}
```

### 7.2 协议下载器配置

```python
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',
    'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    
    # HttpX 配置
    'HTTPX_HTTP2': True,
    'HTTPX_FOLLOW_REDIRECTS': True,
    
    # AioHttp 配置（如果使用 AioHttp）
    'AIOHTTP_AUTO_DECOMPRESS': True,
    
    # CurlCffi 配置（如果使用 CurlCffi）
    'CURL_BROWSER_TYPE': 'chrome',
}
```

## 8. 实际使用示例

### 8.1 电商网站爬虫

```python
from crawlo import Spider, Request
from crawlo.tools.scenario_adapter import create_adapter_for_platform

class EcommerceSpider(Spider):
    name = 'ecommerce_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
        **create_adapter_for_platform("电商网站").get_settings()
    }
    
    def start_requests(self):
        # 列表页使用协议下载器，详情页使用动态下载器
        urls = [
            'https://shop.com/products/category/electronics',
            'https://shop.com/product/12345',
            'https://shop.com/product/67890',
        ]
        
        adapter = create_adapter_for_platform("电商网站")
        for url in urls:
            request = Request(url=url, callback=self.parse)
            adapter.adapt_request(request)
            yield request
    
    def parse(self, response):
        if '/products/' in response.url:
            self.parse_list_page(response)
        elif '/product/' in response.url:
            self.parse_detail_page(response)
    
    def parse_list_page(self, response):
        # 提取产品链接
        product_links = response.css('a.product-link::attr(href)').getall()
        for link in product_links:
            full_url = response.urljoin(link)
            request = Request(url=full_url, callback=self.parse)
            # 详情页自动使用动态下载器
            create_adapter_for_platform("电商网站").adapt_request(request)
            yield request
    
    def parse_detail_page(self, response):
        # 提取产品详细信息
        product_data = {
            'name': response.css('h1.product-name::text').get(),
            'price': response.css('.price::text').get(),
            'description': response.css('.description::text').get(),
            'images': response.css('img.product-image::attr(src)').getall(),
        }
        yield product_data
```

### 8.2 社交媒体爬虫

```python
class SocialMediaSpider(Spider):
    name = 'social_media_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
        **create_adapter_for_platform("社交平台").get_settings()
    }
    
    def start_requests(self):
        # 所有页面都使用动态下载器
        urls = [
            'https://social-media.com/feed',
            'https://social-media.com/user/posts',
            'https://social-media.com/trending',
        ]
        
        adapter = create_adapter_for_platform("社交平台")
        for url in urls:
            request = Request(url=url, callback=self.parse)
            adapter.adapt_request(request)
            yield request
    
    def parse(self, response):
        # 提取社交媒体内容
        posts = response.css('.post-item')
        for post in posts:
            post_data = {
                'id': post.css('.post-id::text').get(),
                'content': post.css('.post-content::text').get(),
                'author': post.css('.post-author::text').get(),
                'timestamp': post.css('.post-timestamp::text').get(),
            }
            yield post_data
```

### 8.3 翻页操作详细示例

```python
class PaginationDetailSpider(Spider):
    name = 'pagination_detail_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 3,
    }
    
    def start_requests(self):
        # 滑动翻页示例
        scroll_pagination_request = Request(
            url='https://example.com/infinite-scroll-products',
            callback=self.parse_scroll_pagination
        ).set_dynamic_loader(True, {
            "pagination": {
                "type": "scroll",
                "scroll_to_bottom": True,
                "scroll_wait_time": 2,
                "max_scrolls": 5
            }
        })
        
        # 点击翻页示例
        click_pagination_request = Request(
            url='https://example.com/click-pagination-products',
            callback=self.parse_click_pagination
        ).set_dynamic_loader(True, {
            "pagination": {
                "type": "click",
                "click_next_selector": "a.next-page-button",
                "click_wait_time": 3,
                "max_clicks": 10
            }
        })
        
        # 组合翻页示例
        mixed_pagination_request = Request(
            url='https://example.com/mixed-pagination-products',
            callback=self.parse_mixed_pagination
        ).set_dynamic_loader(True, {
            "pagination": {
                "type": "mixed",
                "scroll_to_bottom": True,
                "scroll_wait_time": 2,
                "max_scrolls_before_click": 3,
                "click_next_selector": "a.next-page-button",
                "click_wait_time": 3,
                "max_clicks": 5
            }
        })
        
        yield scroll_pagination_request
        yield click_pagination_request
        yield mixed_pagination_request
    
    def parse_scroll_pagination(self, response):
        """处理滑动翻页内容"""
        # 提取产品信息
        products = response.css('.product-item')
        for product in products:
            yield {
                'name': product.css('.product-name::text').get(),
                'price': product.css('.product-price::text').get(),
                'url': product.css('a::attr(href)').get(),
            }
        
        self.logger.info(f"滑动翻页完成，共提取 {len(products)} 个产品")
    
    def parse_click_pagination(self, response):
        """处理点击翻页内容"""
        # 提取产品信息
        products = response.css('.product-item')
        for product in products:
            yield {
                'name': product.css('.product-name::text').get(),
                'price': product.css('.product-price::text').get(),
                'url': product.css('a::attr(href)').get(),
            }
        
        self.logger.info(f"点击翻页完成，共提取 {len(products)} 个产品")
    
    def parse_mixed_pagination(self, response):
        """处理组合翻页内容"""
        # 提取产品信息
        products = response.css('.product-item')
        for product in products:
            yield {
                'name': product.css('.product-name::text').get(),
                'price': product.css('.product-price::text').get(),
                'url': product.css('a::attr(href)').get(),
            }
        
        self.logger.info(f"组合翻页完成，共提取 {len(products)} 个产品")
```

## 9. 性能优化建议

1. **合理配置并发数**：动态下载器通常比协议下载器消耗更多资源，建议适当降低并发数
2. **使用单浏览器模式**：启用 `PLAYWRIGHT_SINGLE_BROWSER_MODE` 或 `SELENIUM_SINGLE_BROWSER_MODE` 来减少浏览器实例数量
3. **控制标签页数量**：通过 `PLAYWRIGHT_MAX_PAGES_PER_BROWSER` 或 `SELENIUM_MAX_TABS_PER_BROWSER` 控制标签页数量
4. **启用无头模式**：在生产环境中启用无头模式以提高性能
5. **合理设置超时时间**：为不同类型的页面设置合适的超时时间
6. **优化翻页操作**：根据实际页面特点调整翻页参数，避免不必要的等待和操作

## 10. 故障排除

### 10.1 下载器选择不正确

如果发现下载器选择不正确，可以检查以下配置：
- URL 模式配置是否正确
- 域名配置是否正确
- 是否手动指定了下载器类型

### 10.2 动态内容加载不完整

如果动态内容加载不完整，可以尝试：
- 增加等待时间
- 配置等待特定元素出现
- 使用自定义的翻页操作

### 10.3 翻页操作不生效

如果翻页操作不生效，可以检查：
- 选择器是否正确
- 等待时间是否足够
- 页面是否真的有更多内容可以加载

### 10.4 资源消耗过高

如果资源消耗过高，可以尝试：
- 降低并发数
- 启用单浏览器模式
- 控制标签页数量
- 启用无头模式
- 优化翻页参数

通过合理配置和使用混合下载器，您可以显著提高爬虫的性能和效率，同时减少资源消耗。