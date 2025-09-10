# Crawlo框架下载器全面技术使用教程

Crawlo框架提供了多种高性能的下载器实现，以满足不同场景下的网络请求需求。本文档将详细介绍每种下载器的功能特性、配置选项和使用方法。

## 1. 概述

Crawlo框架支持以下类型的下载器：

### 1.1 协议下载器（用于静态内容）
- **AioHttpDownloader**：基于aiohttp的高性能异步下载器
- **HttpXDownloader**：支持HTTP/2的现代异步下载器
- **CurlCffiDownloader**：支持浏览器指纹模拟的下载器

### 1.2 动态下载器（用于JavaScript渲染内容）
- **SeleniumDownloader**：基于Selenium WebDriver的下载器
- **PlaywrightDownloader**：基于Playwright的高性能下载器

### 1.3 混合下载器
- **HybridDownloader**：智能选择合适的下载器处理不同类型的请求

## 2. 协议下载器

### 2.1 AioHttpDownloader

#### 功能特性
- 基于持久化ClientSession
- 智能识别Request的高层语义（json_body/form_data）
- 支持GET/POST/PUT/DELETE等方法
- 支持中间件设置的IP代理（HTTP/HTTPS）
- 内存安全防护

#### 配置选项
```python
# 在settings.py或Spider.custom_settings中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'aiohttp',
    'DOWNLOAD_TIMEOUT': 30,  # 下载超时时间（秒）
    'VERIFY_SSL': True,      # 是否验证SSL证书
    'CONNECTION_POOL_LIMIT': 100,  # 连接池限制
    'CONNECTION_POOL_LIMIT_PER_HOST': 20,  # 每主机连接池限制
    'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 最大下载大小（10MB）
}
```

#### 使用示例
```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'aiohttp',
    }
    
    def start_requests(self):
        yield Request(url='https://example.com', callback=self.parse)
    
    def parse(self, response):
        # 处理响应
        pass
```

#### 代理配置
```python
# 在请求中设置代理
request = Request(
    url='https://example.com',
    callback=self.parse
).set_proxy('http://proxy.example.com:8080')

# 带认证的代理
request = Request(
    url='https://example.com',
    callback=self.parse
)
request.proxy = 'http://user:pass@proxy.example.com:8080'
```

### 2.2 HttpXDownloader

#### 功能特性
- 使用持久化AsyncClient
- 支持连接池、HTTP/2、透明代理
- 智能处理Request的json_body和form_data
- 支持代理失败后自动降级为直连

#### 配置选项
```python
# 在settings.py或Spider.custom_settings中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'httpx',
    'DOWNLOAD_TIMEOUT': 30,  # 下载超时时间（秒）
    'VERIFY_SSL': True,      # 是否验证SSL证书
    'CONNECTION_POOL_LIMIT': 100,  # 连接池限制
    'CONNECTION_POOL_LIMIT_PER_HOST': 20,  # 每主机连接池限制
    'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 最大下载大小（10MB）
    'HTTPX_HTTP2': True,  # 是否启用HTTP/2支持
}
```

#### 使用示例
```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'httpx',
    }
    
    def start_requests(self):
        yield Request(url='https://example.com', callback=self.parse)
    
    def parse(self, response):
        # 处理响应
        pass
```

#### 代理配置
```python
# 在请求中设置代理
request = Request(
    url='https://example.com',
    callback=self.parse
)
request.proxy = 'http://proxy.example.com:8080'

# 带认证的代理
request.proxy = 'http://user:pass@proxy.example.com:8080'

# 字典格式代理
request.proxy = {
    'http://': 'http://proxy1.example.com:8080',
    'https://': 'http://proxy2.example.com:8080'
}
```

### 2.3 CurlCffiDownloader

#### 功能特性
- 支持真实浏览器指纹模拟，绕过Cloudflare等反爬虫检测
- 高性能的异步HTTP客户端，基于libcurl
- 内存安全的响应处理
- 自动代理和Cookie管理
- 支持请求延迟、重试、警告大小检查等高级功能

#### 配置选项
```python
# 在settings.py或Spider.custom_settings中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'curl_cffi',
    'DOWNLOAD_TIMEOUT': 30,  # 下载超时时间（秒）
    'VERIFY_SSL': True,      # 是否验证SSL证书
    'CONNECTION_POOL_LIMIT': 100,  # 连接池限制
    'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 最大下载大小（10MB）
    'DOWNLOAD_WARN_SIZE': 1024 * 1024,  # 警告大小（1MB）
    'DOWNLOAD_DELAY': 0,  # 下载延迟（秒）
    'RANDOMIZE_DOWNLOAD_DELAY': False,  # 是否随机化下载延迟
    'CURL_BROWSER_TYPE': 'chrome',  # 浏览器类型
    'CURL_BROWSER_VERSION_MAP': {  # 浏览器版本映射
        'chrome': 'chrome136',
        'edge': 'edge101',
        'safari': 'safari184',
        'firefox': 'firefox135',
    },
}
```

#### 使用示例
```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'curl_cffi',
        'CURL_BROWSER_TYPE': 'chrome136',  # 指定具体浏览器版本
    }
    
    def start_requests(self):
        yield Request(url='https://example.com', callback=self.parse)
    
    def parse(self, response):
        # 处理响应
        pass
```

#### 代理配置
```python
# 在请求中设置代理
request = Request(
    url='https://example.com',
    callback=self.parse
)
request.proxy = 'http://proxy.example.com:8080'

# 带认证的代理
request.proxy = 'http://user:pass@proxy.example.com:8080'

# 字典格式代理
request.proxy = {
    'http': 'http://proxy1.example.com:8080',
    'https': 'http://proxy2.example.com:8080'
}
```

## 3. 动态下载器

### 3.1 SeleniumDownloader

#### 功能特性
- 支持Chrome/Firefox/Edge等主流浏览器
- 智能等待页面加载完成
- 支持自定义浏览器选项和插件
- 内存安全的资源管理
- 自动处理Cookie和本地存储
- 支持翻页操作（鼠标滑动、点击翻页）
- 单浏览器多标签页模式

#### 配置选项
```python
# 在settings.py或Spider.custom_settings中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'selenium',
    'SELENIUM_BROWSER_TYPE': 'chrome',  # 浏览器类型
    'SELENIUM_HEADLESS': True,  # 是否无头模式
    'SELENIUM_TIMEOUT': 30,  # 超时时间（秒）
    'SELENIUM_LOAD_TIMEOUT': 10,  # 页面加载超时时间（秒）
    'SELENIUM_WINDOW_WIDTH': 1920,  # 窗口宽度
    'SELENIUM_WINDOW_HEIGHT': 1080,  # 窗口高度
    'SELENIUM_WAIT_FOR_ELEMENT': None,  # 等待特定元素选择器
    'SELENIUM_ENABLE_JS': True,  # 是否启用JavaScript
    'SELENIUM_PROXY': None,  # 代理设置
    'SELENIUM_SINGLE_BROWSER_MODE': True,  # 单浏览器多标签页模式
    'SELENIUM_MAX_TABS_PER_BROWSER': 10,  # 单浏览器最大标签页数量
}
```

#### 使用示例
```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'selenium',
        'SELENIUM_BROWSER_TYPE': 'chrome',
    }
    
    def start_requests(self):
        yield Request(url='https://example.com', callback=self.parse)
    
    def parse(self, response):
        # 处理响应
        pass
```

#### 代理配置
```python
# 在爬虫设置中配置代理
custom_settings = {
    'DOWNLOADER_TYPE': 'selenium',
    'SELENIUM_PROXY': 'http://proxy.example.com:8080',
}

# 带认证的代理
custom_settings = {
    'DOWNLOADER_TYPE': 'selenium',
    'SELENIUM_PROXY': 'http://user:pass@proxy.example.com:8080',
}
```

#### 翻页操作
```python
# 在请求中指定翻页操作
request = Request(
    url='https://example.com',
    callback=self.parse
)

# 鼠标滑动翻页
request.meta['pagination_actions'] = [
    {
        'type': 'scroll',
        'params': {
            'count': 3,  # 滚动次数
            'delay': 1,  # 每次滚动后等待时间（秒）
            'distance': 500,  # 每次滚动距离（像素）
        }
    }
]

# 鼠标点击翻页
request.meta['pagination_actions'] = [
    {
        'type': 'click',
        'params': {
            'selector': '.next-page',  # 下一页按钮选择器
            'count': 5,  # 点击次数
            'delay': 2,  # 每次点击后等待时间（秒）
        }
    }
]
```

### 3.2 PlaywrightDownloader

#### 功能特性
- 支持Chromium/Firefox/WebKit浏览器引擎
- 异步非阻塞操作
- 智能等待页面加载完成
- 支持自定义浏览器上下文和选项
- 内存安全的资源管理
- 自动处理Cookie和本地存储
- 支持翻页操作（鼠标滑动、点击翻页）
- 单浏览器多标签页模式

#### 配置选项
```python
# 在settings.py或Spider.custom_settings中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'playwright',
    'PLAYWRIGHT_BROWSER_TYPE': 'chromium',  # 浏览器类型
    'PLAYWRIGHT_HEADLESS': True,  # 是否无头模式
    'PLAYWRIGHT_TIMEOUT': 30000,  # 超时时间（毫秒）
    'PLAYWRIGHT_LOAD_TIMEOUT': 10000,  # 页面加载超时时间（毫秒）
    'PLAYWRIGHT_VIEWPORT_WIDTH': 1920,  # 视口宽度
    'PLAYWRIGHT_VIEWPORT_HEIGHT': 1080,  # 视口高度
    'PLAYWRIGHT_WAIT_FOR_ELEMENT': None,  # 等待特定元素选择器
    'PLAYWRIGHT_PROXY': None,  # 代理设置
    'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,  # 单浏览器多标签页模式
    'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 10,  # 单浏览器最大页面数量
}
```

#### 使用示例
```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
    }
    
    def start_requests(self):
        yield Request(url='https://example.com', callback=self.parse)
    
    def parse(self, response):
        # 处理响应
        pass
```

#### 代理配置
```python
# 在爬虫设置中配置代理
custom_settings = {
    'DOWNLOADER_TYPE': 'playwright',
    'PLAYWRIGHT_PROXY': 'http://proxy.example.com:8080',
}

# 带认证的代理
custom_settings = {
    'DOWNLOADER_TYPE': 'playwright',
    'PLAYWRIGHT_PROXY': {
        'server': 'http://proxy.example.com:8080',
        'username': 'user',
        'password': 'pass'
    },
}
```

#### 翻页操作
```python
# 在请求中指定翻页操作
request = Request(
    url='https://example.com',
    callback=self.parse
)

# 鼠标滑动翻页
request.meta['pagination_actions'] = [
    {
        'type': 'scroll',
        'params': {
            'count': 3,  # 滚动次数
            'delay': 1000,  # 每次滚动后等待时间（毫秒）
            'distance': 500,  # 每次滚动距离（像素）
        }
    }
]

# 鼠标点击翻页
request.meta['pagination_actions'] = [
    {
        'type': 'click',
        'params': {
            'selector': '.next-page',  # 下一页按钮选择器
            'count': 5,  # 点击次数
            'delay': 2000,  # 每次点击后等待时间（毫秒）
        }
    }
]
```

## 4. 混合下载器

### 4.1 功能特性
- 智能选择：根据URL模式、域名或请求标记自动选择最合适的下载器
- 性能优化：对静态内容使用高性能的协议下载器，对动态内容使用浏览器下载器
- 资源管理：统一管理不同类型的下载器资源
- 灵活配置：支持多种配置方式来适应不同的业务场景

### 4.2 配置选项
```python
# 在settings.py或Spider.custom_settings中配置
custom_settings = {
    'DOWNLOADER_TYPE': 'hybrid',
    'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',  # 默认协议下载器
    'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',  # 默认动态下载器
    # 动态加载URL模式
    'HYBRID_DYNAMIC_URL_PATTERNS': [
        r'/product/',
        r'/item/',
        r'/detail/',
        r'\.dynamic$',
    ],
    # 协议加载URL模式
    'HYBRID_PROTOCOL_URL_PATTERNS': [
        r'/list/',
        r'/category/',
        r'/search/',
        r'\.html$',
    ],
    # 动态加载域名
    'HYBRID_DYNAMIC_DOMAINS': [
        'dynamic-shop.com',
        'social-media.com',
    ],
    # 协议加载域名
    'HYBRID_PROTOCOL_DOMAINS': [
        'static-news.com',
        'blog-platform.com',
    ]
}
```

### 4.3 使用示例
```python
class MySpider(Spider):
    name = 'my_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
    }
    
    def start_requests(self):
        urls = [
            'https://shop.com/products/list',    # 列表页 - 使用协议下载器
            'https://shop.com/product/12345',    # 详情页 - 使用动态下载器
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        # 处理响应
        pass
```

### 4.4 手动指定下载器
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

## 5. 场景适配器

为了简化配置，Crawlo提供了场景适配器来自动配置下载器：

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

## 6. 性能优化建议

### 6.1 选择合适的下载器
- **静态内容**：使用AioHttpDownloader或HttpXDownloader
- **需要绕过反爬虫检测**：使用CurlCffiDownloader
- **JavaScript渲染内容**：使用SeleniumDownloader或PlaywrightDownloader
- **混合场景**：使用HybridDownloader

### 6.2 配置优化
```python
# 连接池优化
custom_settings = {
    'CONNECTION_POOL_LIMIT': 200,
    'CONNECTION_POOL_LIMIT_PER_HOST': 50,
    'CONNECTION_TTL_DNS_CACHE': 300,
    'CONNECTION_KEEPALIVE_TIMEOUT': 15,
}

# 下载优化
custom_settings = {
    'DOWNLOAD_TIMEOUT': 60,
    'DOWNLOAD_MAXSIZE': 20 * 1024 * 1024,  # 20MB
    'DOWNLOAD_DELAY': 1,
    'RANDOMIZE_DOWNLOAD_DELAY': True,
}
```

### 6.3 资源管理
```python
# 单浏览器多标签页模式（适用于Selenium和Playwright）
custom_settings = {
    'SELENIUM_SINGLE_BROWSER_MODE': True,
    'SELENIUM_MAX_TABS_PER_BROWSER': 20,
    'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
    'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 20,
}
```

## 7. 故障排除

### 7.1 常见问题

#### 代理配置问题
```python
# 检查代理URL格式
proxy = 'http://user:pass@proxy.example.com:8080'

# 对于带认证的代理，确保用户名和密码正确
# 如果使用Selenium，可能需要通过扩展处理认证
```

#### SSL证书问题
```python
# 禁用SSL验证（仅用于测试）
custom_settings = {
    'VERIFY_SSL': False,
}
```

#### 超时问题
```python
# 增加超时时间
custom_settings = {
    'DOWNLOAD_TIMEOUT': 120,
    'SELENIUM_TIMEOUT': 60,
    'PLAYWRIGHT_TIMEOUT': 60000,
}
```

### 7.2 日志调试
```python
# 启用详细日志
custom_settings = {
    'LOG_LEVEL': 'DEBUG',
}
```

## 8. 最佳实践

### 8.1 根据内容类型选择下载器
```python
# 静态内容使用协议下载器
class StaticContentSpider(Spider):
    name = 'static_content'
    custom_settings = {
        'DOWNLOADER_TYPE': 'httpx',
    }

# 动态内容使用动态下载器
class DynamicContentSpider(Spider):
    name = 'dynamic_content'
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
    }
```

### 8.2 合理配置并发数
```python
# 根据下载器类型调整并发数
custom_settings = {
    'CONCURRENCY': 10,  # 协议下载器可以设置较高并发
    # 'CONCURRENCY': 3,   # 动态下载器建议设置较低并发
}
```

### 8.3 使用场景适配器
```python
# 使用预定义的场景配置
from crawlo.tools.scenario_adapter import create_adapter_for_platform

adapter = create_adapter_for_platform("新闻网站")
custom_settings = adapter.get_settings()
```

通过合理选择和配置下载器，您可以充分发挥Crawlo框架的性能优势，高效地处理各种类型的网络爬虫任务。