#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 QUEUE_TYPE = 'redis' 时的配置一致性
验证当 QUEUE_TYPE 明确设置为 'redis' 时，过滤器和管道配置是否正确更新
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess
from crawlo.core.scheduler import Scheduler
from crawlo.queue.queue_manager import QueueType


def test_redis_config_consistency():
    """测试 QUEUE_TYPE = 'redis' 时的配置一致性"""
    print("=== 测试 QUEUE_TYPE = 'redis' 时的配置一致性 ===")
    
    # 创建配置，QUEUE_TYPE 设置为 'redis'，但过滤器和管道使用内存版本
    config = {
        'PROJECT_NAME': 'test_redis_consistency',
        'QUEUE_TYPE': 'redis',
        'FILTER_CLASS': 'crawlo.filters.memory_filter.MemoryFilter',
        'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.dedup.memory.MemoryDedupPipeline',
        'REDIS_URL': 'redis://127.0.0.1:6379/2',
        'CONCURRENCY': 1,
        'DOWNLOAD_DELAY': 0.1,
        'LOG_LEVEL': 'INFO'
    }
    
    # 验证初始配置
    initial_filter = config['FILTER_CLASS']
    initial_pipeline = config['DEFAULT_DEDUP_PIPELINE']
    print(f"初始过滤器配置: {initial_filter}")
    print(f"初始管道配置: {initial_pipeline}")
    
    # 验证初始配置是内存版本
    assert 'memory_filter' in initial_filter, f"期望初始过滤器为内存版本，实际得到 {initial_filter}"
    assert 'memory_dedup_pipeline' in initial_pipeline, f"期望初始管道为内存版本，实际得到 {initial_pipeline}"
    print("✅ 初始配置正确（内存版本）")
    
    print("✅ 配置一致性测试完成")


async def test_scheduler_redis_config_update():
    """测试调度器在 QUEUE_TYPE = 'redis' 时的配置更新"""
    print("\n=== 测试调度器在 QUEUE_TYPE = 'redis' 时的配置更新 ===")
    
    # 创建配置，QUEUE_TYPE 设置为 'redis'，但过滤器和管道使用内存版本
    from crawlo.settings.setting_manager import SettingManager
    settings = SettingManager()
    settings.set('PROJECT_NAME', 'test_scheduler_redis_update')
    settings.set('QUEUE_TYPE', 'redis')
    settings.set('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
    settings.set('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.dedup.memory.MemoryDedupPipeline')
    settings.set('REDIS_URL', 'redis://127.0.0.1:6379/2')
    settings.set('CONCURRENCY', 1)
    settings.set('DOWNLOAD_DELAY', 0.1)
    settings.set('LOG_LEVEL', 'INFO')
    
    # 创建一个模拟的爬虫对象
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
            self.stats = None
            self.spider = None
    
    crawler = MockCrawler(settings)
    
    # 创建调度器实例
    scheduler = Scheduler.create_instance(crawler)
    
    # 验证初始配置
    initial_filter = crawler.settings.get('FILTER_CLASS')
    initial_pipeline = crawler.settings.get('DEFAULT_DEDUP_PIPELINE')
    print(f"调度器创建前的过滤器配置: {initial_filter}")
    print(f"调度器创建前的管道配置: {initial_pipeline}")
    
    # 初始化调度器
    print("正在初始化调度器...")
    await scheduler.open()
    
    # 检查配置是否已更新
    updated_filter = crawler.settings.get('FILTER_CLASS')
    updated_pipeline = crawler.settings.get('DEFAULT_DEDUP_PIPELINE')
    print(f"调度器初始化后的过滤器配置: {updated_filter}")
    print(f"调度器初始化后的管道配置: {updated_pipeline}")
    
    # 获取队列状态
    queue_status = scheduler.queue_manager.get_status()
    print(f"队列类型: {queue_status['type']}")
    print(f"队列健康状态: {queue_status['health']}")
    
    # 验证配置已更新为 Redis 版本
    assert 'aioredis_filter' in updated_filter or 'redis_filter' in updated_filter, \
        f"期望更新后的过滤器为 Redis 版本，实际得到 {updated_filter}"
    assert 'redis_dedup_pipeline' in updated_pipeline, \
        f"期望更新后的管道为 Redis 版本，实际得到 {updated_pipeline}"
    print("✅ 配置已正确更新为 Redis 版本")
    
    # 验证队列类型为 Redis
    assert queue_status['type'] == 'redis', f"期望队列类型为 'redis'，实际得到 '{queue_status['type']}'"
    print("✅ 队列类型正确")
    
    # 清理资源
    await scheduler.close()
    
    print("✅ 调度器配置更新测试完成")


if __name__ == "__main__":
    print("开始测试 QUEUE_TYPE = 'redis' 时的配置一致性...")
    
    try:
        # 运行配置一致性测试
        test_redis_config_consistency()
        
        # 运行调度器配置更新测试
        asyncio.run(test_scheduler_redis_config_update())
        
        print("\n🎉 所有测试通过！QUEUE_TYPE = 'redis' 时的配置一致性已正确实现。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()