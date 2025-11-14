#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试调度器配置更新日志优化
"""
import asyncio
from unittest.mock import Mock
from crawlo.core.scheduler import Scheduler
from crawlo.network.request import Request
from crawlo.utils.log import get_logger


class MockCrawler:
    """模拟 Crawler 对象"""
    def __init__(self, use_redis=True, filter_class=None, dedup_pipeline=None):
        self.settings = MockSettings(use_redis, filter_class, dedup_pipeline)
        self.stats = Mock()


class MockSettings:
    """模拟 Settings 对象"""
    def __init__(self, use_redis=True, filter_class=None, dedup_pipeline=None):
        self.use_redis = use_redis
        self._settings = {
            'LOG_LEVEL': 'INFO',
            'DEPTH_PRIORITY': 1,
            'SCHEDULER_MAX_QUEUE_SIZE': 100,
            'SCHEDULER_QUEUE_NAME': 'test:crawlo:requests',
            'FILTER_DEBUG': False,
            'PROJECT_NAME': 'test',
        }
        
        # 根据参数设置不同的配置
        if use_redis:
            self._settings.update({
                'REDIS_URL': 'redis://localhost:6379/0',
                'QUEUE_TYPE': 'redis',
                'FILTER_CLASS': filter_class or 'crawlo.filters.memory_filter.MemoryFilter',
                'DEFAULT_DEDUP_PIPELINE': dedup_pipeline or 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
            })
        else:
            self._settings.update({
                'QUEUE_TYPE': 'memory',
                'FILTER_CLASS': filter_class or 'crawlo.filters.memory_filter.MemoryFilter',
                'DEFAULT_DEDUP_PIPELINE': dedup_pipeline or 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline',
            })
        
    def get(self, key, default=None):
        return self._settings.get(key, default)
    
    def get_int(self, key, default=0):
        value = self.get(key, default)
        return int(value) if value is not None else default
        
    def get_bool(self, key, default=False):
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value) if value is not None else default

    def get_float(self, key, default=0.0):
        value = self.get(key, default)
        return float(value) if value is not None else default
        
    def set(self, key, value):
        self._settings[key] = value


class MockFilter:
    """模拟去重过滤器"""
    def __init__(self):
        self.seen = set()
        
    @classmethod
    def create_instance(cls, crawler):
        return cls()
    
    async def requested(self, request):
        if request.url in self.seen:
            return True
        self.seen.add(request.url)
        return False
    
    def log_stats(self, request):
        pass


async def test_config_update_logs():
    """测试配置更新日志优化"""
    print("🔍 测试配置更新日志优化...")
    
    # 模拟从内存模式切换到Redis模式的情况
    crawler = MockCrawler(
        use_redis=True, 
        filter_class='crawlo.filters.memory_filter.MemoryFilter',
        dedup_pipeline='crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline'
    )
    
    scheduler = Scheduler.create_instance(crawler)
    scheduler.dupe_filter = MockFilter()
    
    # 这会触发配置更新
    await scheduler.open()
    
    await scheduler.close()
    print("   配置更新日志测试完成")


async def main():
    """主测试函数"""
    print("开始测试调度器配置更新日志优化...")
    print("=" * 50)
    
    try:
        await test_config_update_logs()
        
        print("=" * 50)
        print("调度器配置更新日志优化测试完成！")
        
    except Exception as e:
        print("=" * 50)
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置日志级别避免过多输出
    import logging
    logging.getLogger('crawlo').setLevel(logging.INFO)
    
    asyncio.run(main())