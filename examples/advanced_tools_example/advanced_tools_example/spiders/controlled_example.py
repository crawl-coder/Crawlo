#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受控爬虫混入类使用示例
演示如何使用 ControlledRequestMixin 控制大规模请求生成

使用场景：
适用于需要生成大量请求的爬虫项目，特别是当起始URL数量庞大时，可以防止内存溢出并控制并发数量。

典型应用场景：
- 需要生成大量请求的爬虫
- 内存受限的环境
- 需要精确控制并发的场景
- 处理大规模网站的分页URL

与OfweekSpider的对比案例：
在OfweekSpider中，我们可以使用受控爬虫来优化起始请求的生成：

```python
# OfweekSpider中原本的起始请求生成方式
max_page = 1851
start_urls = []
for page in range(1, max_page + 1):
    url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
    start_urls.append(url)

# 使用受控爬虫重构后
class OfweekControlledSpider(OfweekSpider, ControlledRequestMixin):
    def __init__(self):
        OfweekSpider.__init__(self)
        ControlledRequestMixin.__init__(self)
        
        # 配置受控生成参数
        self.max_pending_requests = 100
        self.batch_size = 50
        self.generation_interval = 0.01
    
    def _original_start_requests(self):
        """提供原始的大量请求"""
        max_page = 1851  # 处理1851页
        for page in range(1, max_page + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            yield Request(
                url=url,
                callback=self.parse,
                headers=self.headers,
                cookies=self.cookies
            )
```

优势：
- 防止内存溢出
- 控制并发数量
- 动态负载调节
- 提高系统稳定性
- 背压控制，根据系统负载动态调节
"""

from crawlo.spider import Spider
from crawlo.network import Request
from crawlo.utils.controlled_spider_mixin import ControlledRequestMixin
from crawlo.utils.log import get_logger


class ControlledExampleSpider(Spider, ControlledRequestMixin):
    """受控爬虫示例"""
    name = 'controlled_example'
    
    def __init__(self):
        Spider.__init__(self)
        ControlledRequestMixin.__init__(self)
        
        # 配置受控生成参数
        self.max_pending_requests = 100     # 最大待处理请求数
        self.batch_size = 50               # 每批生成请求数
        self.generation_interval = 0.01     # 生成间隔（秒）
        self.backpressure_threshold = 200   # 背压阈值
        
        # self.logger = get_logger(self.__class__.__name__)
    
    def _original_start_requests(self):
        """提供原始的大量请求"""
        # self.logger.info("开始生成大量请求...")
        
        # 模拟生成10000个请求
        for i in range(10000):
            yield Request(
                url=f'https://httpbin.org/get?id={i}',
                callback=self.parse,
                meta={'id': i}
            )
    
    def parse(self, response):
        """解析响应"""
        item_id = response.meta.get('id', 'unknown')
        # self.logger.debug(f"处理响应: {item_id}")
        
        # 模拟一些处理工作
        import time
        time.sleep(0.001)
        
        yield {
            'id': item_id,
            'url': response.url,
            'status': response.status_code,
            'timestamp': time.time()
        }


# 异步版本示例
from crawlo.utils.controlled_spider_mixin import AsyncControlledRequestMixin


class AsyncControlledExampleSpider(Spider, AsyncControlledRequestMixin):
    """异步受控爬虫示例"""
    name = 'async_controlled_example'
    
    def __init__(self):
        Spider.__init__(self)
        AsyncControlledRequestMixin.__init__(self)
        
        # 配置异步控制参数
        self.max_concurrent_generations = 10
        self.queue_monitor_interval = 0.5
        
        # self.logger = get_logger(self.__class__.__name__)
    
    def _original_start_requests(self):
        """提供原始的大量请求"""
        # self.logger.info("开始生成大量异步请求...")
        
        # 模拟生成5000个请求
        for i in range(5000):
            yield Request(
                url=f'https://httpbin.org/json?id={i}',
                callback=self.parse,
                meta={'id': i}
            )
    
    async def parse(self, response):
        """异步解析响应"""
        item_id = response.meta.get('id', 'unknown')
        # self.logger.debug(f"异步处理响应: {item_id}")
        
        # 模拟异步处理工作
        import asyncio
        await asyncio.sleep(0.001)
        
        yield {
            'id': item_id,
            'url': response.url,
            'status': response.status_code,
            'timestamp': __import__('time').time()
        }


# 使用示例说明
USAGE_EXAMPLE = """
受控爬虫混入类使用说明
================

1. ControlledRequestMixin (同步版本):
   - 解决 start_requests() 同时生成大量请求导致的问题
   - 控制并发请求数量，避免内存爆炸
   - 支持背压控制，根据系统负载动态调节

2. AsyncControlledRequestMixin (异步版本):
   - 使用 asyncio 实现更精确的并发控制
   - 更好的性能和资源利用率
   - 适合高并发场景

3. 配置参数:
   - max_pending_requests: 最大待处理请求数
   - batch_size: 每批生成请求数
   - generation_interval: 请求生成间隔
   - backpressure_threshold: 背压阈值

4. 优势:
   - 防止内存溢出
   - 控制并发数量
   - 动态负载调节
   - 提高系统稳定性

5. 适用场景:
   - 需要生成大量请求的爬虫
   - 内存受限的环境
   - 需要精确控制并发的场景
"""

if __name__ == '__main__':
    print(USAGE_EXAMPLE)