# crawlo.spider.__init__

Crawlo Spider Module
==================
提供爬虫基类和相关功能。

核心功能:
- Spider基类：所有爬虫的基础类
- 自动注册机制：通过元类自动注册爬虫
- 配置管理：支持自定义设置和链式调用
- 生命周期管理：开启/关闭钩子函数
- 分布式支持：智能检测运行模式

使用示例:
    class MySpider(Spider):
        name = 'my_spider'
        start_urls = ['http://example.com']
        
        # 自定义配置
        custom_settings = {
            'DOWNLOADER_TYPE': 'httpx',
            'CONCURRENCY': 10
        }
        
        def parse(self, response):
            # 解析逻辑
            yield Item(data=response.json())

## 导入的类

- annotations
- Type
- Any
- Optional
- List
- Dict
- Union
- Iterator
- AsyncIterator
- Request
- get_logger

## 类

### SpiderMeta
爬虫元类，提供自动注册功能

功能:
- 自动注册爬虫到全局注册表
- 验证爬虫名称的唯一性
- 提供完整的错误提示

#### 方法

##### __new__

### Spider
爬虫基类 - 所有爬虫实现的基础

必须定义的属性:
- name: 爬虫名称，必须全局唯一

可选配置:
- start_urls: 起始 URL 列表
- custom_settings: 自定义设置字典
- allowed_domains: 允许的域名列表

必须实现的方法:
- parse(response): 解析响应的主方法

可选实现的方法:
- spider_opened(): 爬虫开启时调用
- spider_closed(): 爬虫关闭时调用
- start_requests(): 生成初始请求（默认使用start_urls）

示例:
    class MySpider(Spider):
        name = 'example_spider'
        start_urls = ['https://example.com']
        
        custom_settings = {
            'DOWNLOADER_TYPE': 'httpx',
            'CONCURRENCY': 5,
            'DOWNLOAD_DELAY': 1.0
        }
        
        def parse(self, response):
            # 提取数据
            data = response.css('title::text').get()
            yield {'title': data}
            
            # 生成新请求
            for link in response.css('a::attr(href)').getall():
                yield Request(url=link, callback=self.parse_detail)

#### 方法

##### __init__
初始化爬虫实例

:param name: 爬虫名称（可选，默认使用类属性）
:param kwargs: 其他初始化参数

##### create_instance
创建爬虫实例并绑定 crawler

:param crawler: Crawler 实例
:return: 爬虫实例

##### start_requests
生成初始请求

默认行为:
- 使用 start_urls 生成请求
- 智能检测分布式模式决定是否去重
- 支持单个 start_url 属性（兼容性）
- 支持批量生成优化（大规模URL场景）

:return: Request 迭代器

##### _get_batch_size
获取批量处理大小配置

用于大规模URL场景的性能优化

:return: 批量大小（0表示无限制）

##### _is_distributed_mode
智能检测是否为分布式模式

检测条件:
- QUEUE_TYPE = 'redis'
- FILTER_CLASS 包含 'aioredis_filter' 
- RUN_MODE = 'distributed'

:return: 是否为分布式模式

##### _is_allowed_domain
检查URL是否在允许的域名列表中

:param url: 要检查的URL
:return: 是否允许

##### parse
解析响应的主方法（必须实现）

:param response: 响应对象
:return: 生成的 Item 或 Request

##### __str__

##### __repr__

##### set_custom_setting
设置自定义配置（链式调用）

:param key: 配置键名
:param value: 配置值
:return: self（支持链式调用）

示例:
    spider.set_custom_setting('CONCURRENCY', 10)                  .set_custom_setting('DOWNLOAD_DELAY', 1.0)

##### get_custom_setting
获取自定义配置值

:param key: 配置键名 
:param default: 默认值
:return: 配置值

##### get_spider_info
获取爬虫详细信息

:return: 爬虫信息字典

##### make_request
便捷方法：创建 Request 对象

:param url: 请求URL
:param callback: 回调函数（默认为parse）
:param kwargs: 其他Request参数
:return: Request对象

### SpiderStatsTracker
爬虫统计跟踪器
提供详细的性能监控功能

#### 方法

##### __init__

##### start_tracking
开始统计

##### stop_tracking
停止统计

##### record_request
记录请求

##### record_response
记录响应

##### record_item
记录Item

##### record_error
记录错误

##### get_summary
获取统计摘要

## 函数

### create_spider_from_template
从模板快速创建爬虫类

:param name: 爬虫名称
:param start_urls: 起始URL列表
:param options: 其他选项
:return: 新创建的爬虫类

示例:
    MySpider = create_spider_from_template(
        name='quick_spider',
        start_urls=['http://example.com'],
        allowed_domains=['example.com'],
        custom_settings={'CONCURRENCY': 5}
    )

### get_global_spider_registry
获取全局爬虫注册表的副本

:return: 爬虫注册表的副本

### get_spider_by_name
根据名称获取爬虫类

:param name: 爬虫名称
:return: 爬虫类或None

### get_all_spider_classes
获取所有注册的爬虫类

:return: 爬虫类列表

### get_spider_names
获取所有爬虫名称

:return: 爬虫名称列表

### is_spider_registered
检查爬虫是否已注册

:param name: 爬虫名称
:return: 是否已注册

### unregister_spider
取消注册爬虫（仅用于测试）

:param name: 爬虫名称
:return: 是否成功取消注册
