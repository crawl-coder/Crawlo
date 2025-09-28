#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理工具使用示例
演示如何使用 Crawlo 的批处理工具处理大量数据

使用场景：
适用于需要处理大量数据的爬虫项目，特别是当数据量超过内存限制或需要控制并发处理数量时。

典型应用场景：
- 处理大量数据项
- 需要控制并发数量
- 内存敏感的数据处理任务
- 需要批量存储数据到数据库

与OfweekSpider的对比案例：
在OfweekSpider中，我们可以使用批处理来优化数据存储：

```python
# OfweekSpider中原本的数据处理方式
yield item  # 逐个处理数据项

# 使用批处理重构后
# 在爬虫初始化时创建批处理器
self.batch_processor = BatchProcessor(batch_size=100, max_concurrent_batches=5)

# 在parse_detail方法中收集数据
self.data_items.append({
    'title': title,
    'publish_time': publish_time,
    'url': response.url,
    'source': source,
    'content': content
})

# 定期批量处理数据
if len(self.data_items) >= 100:
    await self.batch_processor.process_in_batches(
        items=self.data_items,
        processor_func=self.batch_save_items
    )
    self.data_items.clear()
```

优势：
- 控制内存使用，避免一次性处理大量数据
- 支持并发处理提高效率
- 自动错误处理和恢复
- 可配置的批处理大小和并发数
"""

import asyncio
import time
from typing import List, Any

from crawlo.spider import Spider
from crawlo.network import Request
from crawlo.utils.batch_processor import BatchProcessor, batch_process
from crawlo.utils.log import get_logger


class BatchExampleSpider(Spider):
    """批处理工具示例爬虫"""
    name = 'batch_example'
    
    def __init__(self):
        super().__init__()
        # self.logger = get_logger(self.__class__.__name__)
        self.batch_processor = BatchProcessor(batch_size=50, max_concurrent_batches=3)
    
    def start_requests(self):
        """生成大量起始请求"""
        # 模拟生成1000个请求
        for i in range(1000):
            url = f'https://httpbin.org/get?page={i}'
            yield Request(url=url, callback=self.parse, meta={'page': i})
    
    async def parse(self, response):
        """解析响应并演示批处理"""
        page = response.meta.get('page', 0)
        # self.logger.info(f"处理页面: {page}")
        
        # 模拟需要批处理的数据
        data_items = [f"item_{page}_{i}" for i in range(100)]
        
        # 使用批处理工具处理数据
        start_time = time.time()
        results = await self.batch_processor.process_in_batches(
            items=data_items,
            processor_func=self._process_item,
            prefix=f"page_{page}"
        )
        end_time = time.time()
        
        # self.logger.info(f"页面 {page} 批处理完成，耗时: {end_time - start_time:.2f}秒")
        
        yield {
            'page': page,
            'items_processed': len(results),
            'processing_time': end_time - start_time
        }
    
    async def _process_item(self, item: str, prefix: str) -> dict:
        """处理单个数据项"""
        # 模拟处理时间
        await asyncio.sleep(0.01)
        return {
            'processed_item': f"{prefix}_{item}",
            'timestamp': time.time(),
            'length': len(item)
        }


# 独立批处理工具使用示例
async def batch_processing_example():
    """批处理工具独立使用示例"""
    # logger = get_logger("BatchProcessingExample")
    
    # 创建大量数据
    data = [f"data_item_{i}" for i in range(1000)]
    
    # 定义处理函数
    def process_data_item(item: str) -> dict:
        """处理数据项"""
        time.sleep(0.001)  # 模拟处理时间
        return {
            'processed': item.upper(),
            'length': len(item),
            'timestamp': time.time()
        }
    
    # logger.info("开始批处理示例...")
    start_time = time.time()
    
    # 使用便捷函数进行批处理
    results = batch_process(
        items=data,
        processor_func=process_data_item,
        batch_size=100,
        max_concurrent_batches=5
    )
    
    end_time = time.time()
    # logger.info(f"批处理完成，处理了 {len(results)} 个项目，耗时: {end_time - start_time:.2f}秒")
    
    return results


# 使用示例说明
USAGE_EXAMPLE = """
批处理工具使用说明
==============

1. BatchProcessor 类:
   - 初始化: BatchProcessor(batch_size=100, max_concurrent_batches=5)
   - 批处理: process_in_batches(items, processor_func, *args, **kwargs)
   - 支持异步处理和并发控制

2. 便捷函数 batch_process:
   - 简化批处理调用
   - 自动创建处理器实例
   - 适合一次性批处理任务

3. 优势:
   - 控制内存使用，避免一次性处理大量数据
   - 支持并发处理提高效率
   - 自动错误处理和恢复

4. 适用场景:
   - 大量数据的处理
   - 需要控制并发数的任务
   - 内存敏感的数据处理
"""

if __name__ == '__main__':
    print(USAGE_EXAMPLE)
    
    # 运行独立批处理示例
    print("\n运行独立批处理示例...")
    asyncio.run(batch_processing_example())