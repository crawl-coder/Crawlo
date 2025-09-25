#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模配置工具使用示例
演示如何使用 LargeScaleConfig 优化大规模爬取配置

使用场景：
适用于不同规模和性能要求的爬虫项目，可以根据环境资源选择合适的配置。

典型应用场景：
- 资源受限环境（使用保守配置）
- 一般生产环境（使用平衡配置）
- 高性能服务器（使用激进配置）
- 内存受限但要处理大量请求（使用内存优化配置）

与OfweekSpider的对比案例：
在OfweekSpider中，我们可以根据不同的运行环境应用不同的配置：

```python
# OfweekSpider中原本的配置方式
custom_settings = {
    'DOWNLOAD_DELAY': 1.0,
    'CONCURRENCY': 16,
    'MAX_RETRY_TIMES': 5
}

# 使用大规模配置工具重构后
# 在settings.py中
from crawlo.utils.large_scale_config import apply_large_scale_config

# 根据环境变量选择配置类型
import os
config_type = os.getenv('CONFIG_TYPE', 'balanced')
concurrency = int(os.getenv('CONCURRENCY', '16'))

settings = {}
apply_large_scale_config(settings, config_type, concurrency)

# 应用到配置中
for key, value in settings.items():
    locals()[key] = value
```

优势：
- 针对不同场景优化的配置
- 简化配置过程
- 提高爬取效率和稳定性
- 减少配置错误
- 快速适配不同性能环境
"""

from crawlo.spider import Spider
from crawlo.network import Request
from crawlo.utils.large_scale_config import LargeScaleConfig, apply_large_scale_config
from crawlo.utils.log import get_logger


class LargeScaleConfigExampleSpider(Spider):
    """大规模配置示例爬虫"""
    name = 'large_scale_config_example'
    
    def __init__(self):
        super().__init__()
        # self.logger = get_logger(self.__class__.__name__)
        
        # 可以在爬虫初始化时应用大规模配置
        # 这里只是示例，实际应用中通常在 settings.py 中配置
        
    def start_requests(self):
        """生成起始请求"""
        urls = [
            'https://httpbin.org/get',
            'https://httpbin.org/json',
            'https://httpbin.org/headers'
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        # self.logger.info(f"处理响应: {response.url}")
        
        yield {
            'url': response.url,
            'status': response.status_code,
            'title': response.css('title::text').get() or 'N/A'
        }


# 不同配置类型的使用示例
def demonstrate_config_types():
    """演示不同配置类型的使用"""
    # logger = get_logger("ConfigDemo")
    
    # logger.info("=== 大规模配置工具演示 ===")
    
    # 1. 保守配置 - 适用于资源有限的环境
    conservative_config = LargeScaleConfig.conservative_config(concurrency=8)
    # logger.info("保守配置:")
    # logger.info(f"  并发数: {conservative_config['CONCURRENCY']}")
    # logger.info(f"  队列容量: {conservative_config['SCHEDULER_MAX_QUEUE_SIZE']}")
    # logger.info(f"  下载延迟: {conservative_config['DOWNLOAD_DELAY']}秒")
    
    # 2. 平衡配置 - 适用于一般生产环境
    balanced_config = LargeScaleConfig.balanced_config(concurrency=16)
    # logger.info("\n平衡配置:")
    # logger.info(f"  并发数: {balanced_config['CONCURRENCY']}")
    # logger.info(f"  队列容量: {balanced_config['SCHEDULER_MAX_QUEUE_SIZE']}")
    # logger.info(f"  下载延迟: {balanced_config['DOWNLOAD_DELAY']}秒")
    
    # 3. 激进配置 - 适用于高性能服务器
    aggressive_config = LargeScaleConfig.aggressive_config(concurrency=32)
    # logger.info("\n激进配置:")
    # logger.info(f"  并发数: {aggressive_config['CONCURRENCY']}")
    # logger.info(f"  队列容量: {aggressive_config['SCHEDULER_MAX_QUEUE_SIZE']}")
    # logger.info(f"  下载延迟: {aggressive_config['DOWNLOAD_DELAY']}秒")
    
    # 4. 内存优化配置 - 适用于内存受限但要处理大量请求
    memory_config = LargeScaleConfig.memory_optimized_config(concurrency=12)
    # logger.info("\n内存优化配置:")
    # logger.info(f"  并发数: {memory_config['CONCURRENCY']}")
    # logger.info(f"  队列容量: {memory_config['SCHEDULER_MAX_QUEUE_SIZE']}")
    # logger.info(f"  下载延迟: {memory_config['DOWNLOAD_DELAY']}秒")
    # logger.info(f"  最大下载大小: {memory_config['DOWNLOAD_MAXSIZE']}字节")


# 在 settings.py 中应用配置的示例
def apply_config_in_settings():
    """在 settings.py 中应用配置的示例"""
    # 模拟 settings.py 中的内容
    settings = {}
    
    # 应用平衡配置，16并发
    apply_large_scale_config(settings, "balanced", 16)
    
    print("应用平衡配置后的设置:")
    for key, value in settings.items():
        print(f"  {key}: {value}")


# 使用示例说明
USAGE_EXAMPLE = """
大规模配置工具使用说明
================

1. 配置类型:
   - Conservative (保守型): 资源受限环境，低并发，高延迟
   - Balanced (平衡型): 一般生产环境，中等并发和延迟
   - Aggressive (激进型): 高性能服务器，高并发，低延迟
   - Memory Optimized (内存优化型): 内存受限但要处理大量请求

2. 使用方法:
   - 在 settings.py 中使用 apply_large_scale_config()
   - 在代码中直接调用配置类方法
   - 自定义配置参数

3. 配置参数说明:
   - CONCURRENCY: 并发请求数
   - SCHEDULER_MAX_QUEUE_SIZE: 调度器最大队列大小
   - DOWNLOAD_DELAY: 下载延迟
   - CONNECTION_POOL_LIMIT: 连接池限制
   - DOWNLOAD_MAXSIZE: 最大下载大小

4. 优势:
   - 针对不同场景优化的配置
   - 简化配置过程
   - 提高爬取效率和稳定性
   - 减少配置错误

5. 适用场景:
   - 处理数万+请求的大规模爬取
   - 不同性能环境的适配
   - 快速配置优化
"""

if __name__ == '__main__':
    print(USAGE_EXAMPLE)
    
    # 演示不同配置类型
    demonstrate_config_types()
    
    print("\n" + "="*50)
    
    # 演示在 settings.py 中应用配置
    apply_config_in_settings()