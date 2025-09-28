#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模爬虫辅助工具使用示例
演示如何使用 LargeScaleHelper 等工具处理大规模爬取任务

使用场景：
适用于处理大规模数据的爬虫项目，特别是需要断点续传、进度管理和内存优化的场景。

典型应用场景：
- 处理数万+ URL的爬虫
- 需要断点续传的功能
- 内存敏感的大规模处理任务
- 需要进度跟踪和恢复的爬虫

与OfweekSpider的对比案例：
在OfweekSpider中，我们可以使用大规模爬虫辅助工具来增强功能：

```python
# OfweekSpider中原本的处理方式
# 直接处理所有页面，没有进度管理

# 使用大规模爬虫辅助工具重构后
class OfweekLargeScaleSpider(OfweekSpider):
    def __init__(self):
        super().__init__()
        # 初始化辅助工具
        self.large_scale_helper = LargeScaleHelper(batch_size=100, checkpoint_interval=500)
        self.progress_manager = ProgressManager(progress_file="ofweek_progress.json")
        self.memory_optimizer = MemoryOptimizer(max_memory_mb=500)
    
    def start_requests(self):
        """使用批处理生成大量请求并支持断点续传"""
        # 模拟大量数据源
        max_page = 1851
        data_source = [f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html' for page in range(1, max_page + 1)]
        
        # 加载进度
        progress = self.progress_manager.load_progress()
        start_offset = progress.get('processed_count', 0)
        
        self.logger.info(f"从偏移量 {start_offset} 开始处理")
        
        # 使用批处理迭代器处理数据
        processed_count = start_offset
        for batch in self.large_scale_helper.batch_iterator(data_source, start_offset):
            # 内存检查和优化
            if self.memory_optimizer.should_pause_for_memory():
                self.logger.warning("内存使用过高，执行垃圾回收")
                self.memory_optimizer.force_garbage_collection()
            
            for url in batch:
                processed_count += 1
                yield Request(
                    url=url,
                    callback=self.parse,
                    headers=self.headers,
                    cookies=self.cookies,
                    meta={'page': processed_count}
                )
                
                # 保存进度
                if processed_count % 100 == 0:
                    self.progress_manager.save_progress({
                        'processed_count': processed_count,
                        'timestamp': time.time()
                    })
```

优势：
- 处理大量数据时的内存管理
- 断点续传支持
- 进度跟踪和恢复
- 内存使用优化
- 批量数据处理
"""

import json
import tempfile
from typing import List, Any

from crawlo.spider import Spider
from crawlo.network import Request
from crawlo.utils.large_scale_helper import (
    LargeScaleHelper, 
    ProgressManager, 
    MemoryOptimizer,
    DataSourceAdapter
)
from crawlo.utils.log import get_logger


class LargeScaleHelperExampleSpider(Spider):
    """大规模爬虫辅助工具示例"""
    name = 'large_scale_helper_example'
    
    def __init__(self):
        super().__init__()
        # self.logger = get_logger(self.__class__.__name__)
        
        # 初始化辅助工具
        self.large_scale_helper = LargeScaleHelper(batch_size=100, checkpoint_interval=500)
        self.progress_manager = ProgressManager(progress_file=f"{self.name}_progress.json")
        self.memory_optimizer = MemoryOptimizer(max_memory_mb=500)
    
    def start_requests(self):
        """使用批处理生成大量请求"""
        # 模拟大量数据源
        data_source = [f"https://example.com/page/{i}" for i in range(1000)]
        
        # 加载进度
        progress = self.progress_manager.load_progress()
        start_offset = progress.get('processed_count', 0)
        
        # self.logger.info(f"从偏移量 {start_offset} 开始处理")
        
        # 使用批处理迭代器处理数据
        processed_count = start_offset
        for batch in self.large_scale_helper.batch_iterator(data_source, start_offset):
            # 内存检查和优化
            if self.memory_optimizer.should_pause_for_memory():
                # self.logger.warning("内存使用过高，执行垃圾回收")
                self.memory_optimizer.force_garbage_collection()
            
            for url in batch:
                processed_count += 1
                yield Request(url=url, callback=self.parse, meta={'id': processed_count})
                
                # 保存进度
                if processed_count % 100 == 0:
                    self.progress_manager.save_progress({
                        'processed_count': processed_count,
                        'timestamp': __import__('time').time()
                    })
    
    def parse(self, response):
        """解析响应"""
        item_id = response.meta.get('id', 'unknown')
        # self.logger.debug(f"处理响应: {item_id}")
        
        yield {
            'id': item_id,
            'url': response.url,
            'status': response.status_code
        }
    
    def closed(self, reason):
        """爬虫关闭时清理进度"""
        self.progress_manager.clear_progress()
        # self.logger.info(f"爬虫关闭，原因: {reason}")


# 独立使用辅助工具的示例
def demonstrate_standalone_tools():
    """演示独立使用辅助工具"""
    # logger = get_logger("StandaloneToolsDemo")
    
    # logger.info("=== 大规模爬虫辅助工具演示 ===")
    
    # 1. LargeScaleHelper 使用示例
    # logger.info("\n1. LargeScaleHelper 使用示例:")
    helper = LargeScaleHelper(batch_size=50, checkpoint_interval=200)
    
    # 处理大量数据
    large_data = list(range(1000))
    batch_count = 0
    total_items = 0
    
    for batch in helper.batch_iterator(large_data):
        batch_count += 1
        total_items += len(batch)
        # logger.info(f"  批次 {batch_count}: 处理 {len(batch)} 个项目")
    
    # logger.info(f"  总共处理 {batch_count} 个批次，{total_items} 个项目")
    
    # 2. ProgressManager 使用示例
    # logger.info("\n2. ProgressManager 使用示例:")
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        progress_file = tmp.name
    
    progress_manager = ProgressManager(progress_file=progress_file)
    
    # 保存进度
    progress_data = {
        'processed_count': 500,
        'timestamp': __import__('time').time(),
        'checkpoint': 'middle'
    }
    progress_manager.save_progress(progress_data)
    # logger.info(f"  进度已保存: {progress_data}")
    
    # 加载进度
    loaded_progress = progress_manager.load_progress()
    # logger.info(f"  进度已加载: {loaded_progress}")
    
    # 清理进度
    progress_manager.clear_progress()
    # logger.info("  进度已清理")
    
    # 3. MemoryOptimizer 使用示例
    # logger.info("\n3. MemoryOptimizer 使用示例:")
    memory_optimizer = MemoryOptimizer(max_memory_mb=100)
    
    current_memory = memory_optimizer.get_current_memory_usage()
    # logger.info(f"  当前内存使用: {current_memory:.2f} MB")
    
    should_pause = memory_optimizer.should_pause_for_memory()
    # logger.info(f"  是否应该暂停: {should_pause}")
    
    # 4. DataSourceAdapter 使用示例
    # logger.info("\n4. DataSourceAdapter 使用示例:")
    
    # 从列表创建数据源
    list_data = ['item1', 'item2', 'item3', 'item4', 'item5']
    list_adapter = DataSourceAdapter.from_list(list_data)
    # logger.info(f"  列表数据源: {list_adapter.get_batch(0, 3)}")
    
    # 从文件创建数据源（创建临时文件）
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        for i in range(10):
            tmp.write(f"line_{i}\n")
        file_path = tmp.name
    
    file_adapter = DataSourceAdapter.from_file(file_path, batch_size=3)
    # logger.info(f"  文件数据源批次1: {file_adapter.get_batch(0, 3)}")
    # logger.info(f"  文件数据源批次2: {file_adapter.get_batch(3, 3)}")


# 使用示例说明
USAGE_EXAMPLE = """
大规模爬虫辅助工具使用说明
===================

1. LargeScaleHelper:
   - batch_iterator(): 批量迭代大量数据
   - 支持不同数据源类型（列表、函数、自定义数据源）
   - 可配置批次大小和检查点间隔

2. ProgressManager:
   - save_progress(): 保存处理进度
   - load_progress(): 加载处理进度
   - clear_progress(): 清理进度文件
   - 支持断点续传功能

3. MemoryOptimizer:
   - get_current_memory_usage(): 获取当前内存使用
   - should_pause_for_memory(): 检查是否应该暂停以释放内存
   - force_garbage_collection(): 强制垃圾回收

4. DataSourceAdapter:
   - from_list(): 从列表创建数据源
   - from_file(): 从文件创建数据源
   - from_database(): 从数据库创建数据源
   - get_batch(): 获取指定批次的数据

5. 优势:
   - 处理大量数据时的内存管理
   - 断点续传支持
   - 进度跟踪和恢复
   - 内存使用优化

6. 适用场景:
   - 处理数万+ URL的爬虫
   - 需要断点续传的功能
   - 内存敏感的大规模处理任务
"""

if __name__ == '__main__':
    print(USAGE_EXAMPLE)
    
    # 演示独立使用辅助工具
    demonstrate_standalone_tools()