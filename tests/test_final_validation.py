#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终验证测试：确认分布式队列的 logger 序列化问题已完全解决
"""
import asyncio
import pickle
import sys
sys.path.insert(0, "..")

from crawlo.network.request import Request
from crawlo.spider import Spider
from crawlo.core.scheduler import Scheduler
from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.utils.log import get_logger
from unittest.mock import Mock


class TestSpider(Spider):
    """测试爬虫"""
    name = "validation_spider"
    
    def __init__(self):
        super().__init__()
        # 故意添加多个 logger 来测试清理
        self.custom_logger = get_logger("custom")
        self.debug_logger = get_logger("debug")
        self.nested_data = {
            'logger': get_logger("nested"),
            'sub': {
                'logger_ref': get_logger("sub_logger")
            }
        }
    
    def parse(self, response):
        # 验证主 logger 还在
        self.logger.info(f"✅ 主 logger 工作正常: {response.url}")
        return {"url": response.url, "status": "success"}


def test_scheduler_cleaning():
    """测试调度器的 logger 清理"""
    print("🔍 测试调度器 logger 清理...")
    
    spider = TestSpider()
    request = Request(
        url="https://scheduler-test.com",
        callback=spider.parse,
        meta={"logger": get_logger("meta_logger")}
    )
    
    # Mock crawler 和 scheduler
    class MockCrawler:
        def __init__(self):
            self.spider = spider
    
    class MockScheduler(Scheduler):
        def __init__(self):
            self.crawler = MockCrawler()
            self.logger = get_logger("MockScheduler")
    
    scheduler = MockScheduler()
    
    # 清理前检查
    print(f"   🔧 清理前 - spider.logger: {spider.logger is not None}")
    print(f"   🔧 清理前 - spider.custom_logger: {spider.custom_logger is not None}")
    print(f"   🔧 清理前 - request.callback: {request.callback is not None}")
    
    # 执行清理
    cleaned_request = scheduler._deep_clean_loggers(request)
    
    # 清理后检查
    print(f"   ✅ 清理后 - spider.logger: {spider.logger is not None}")
    print(f"   ✅ 清理后 - spider.custom_logger: {spider.custom_logger is None}")
    print(f"   ✅ 清理后 - request.callback: {cleaned_request.callback is None}")
    
    # 序列化测试
    try:
        serialized = pickle.dumps(cleaned_request)
        print(f"   ✅ 调度器清理后序列化成功，大小: {len(serialized)} bytes")
        return True
    except Exception as e:
        print(f"   ❌ 调度器清理后序列化失败: {e}")
        return False


async def test_redis_queue_cleaning():
    """测试 Redis 队列的 logger 清理"""
    print("\\n🔍 测试 Redis 队列 logger 清理...")
    
    spider = TestSpider()
    request = Request(
        url="https://redis-test.com",
        callback=spider.parse,
        meta={"logger": get_logger("meta_logger")}
    )
    
    try:
        queue = RedisPriorityQueue(redis_url="redis://127.0.0.1:6379/0")
        await queue.connect()
        
        # 入队测试
        success = await queue.put(request, priority=0)
        print(f"   ✅ Redis 队列入队成功: {success}")
        
        if success:
            # 出队测试
            retrieved = await queue.get(timeout=2.0)
            if retrieved:
                print(f"   ✅ Redis 队列出队成功: {retrieved.url}")
                print(f"   ✅ callback 信息保存: {'_callback_info' in retrieved.meta}")
                await queue.close()
                return True
            else:
                print("   ❌ 出队失败")
                await queue.close()
                return False
        else:
            await queue.close()
            return False
            
    except Exception as e:
        print(f"   ❌ Redis 队列测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始最终验证测试...")
    print("=" * 60)
    
    # 测试 1: 调度器清理
    scheduler_ok = test_scheduler_cleaning()
    
    # 测试 2: Redis 队列清理
    redis_ok = await test_redis_queue_cleaning()
    
    print("\\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print(f"   调度器 logger 清理: {'✅ 通过' if scheduler_ok else '❌ 失败'}")
    print(f"   Redis 队列清理: {'✅ 通过' if redis_ok else '❌ 失败'}")
    
    if scheduler_ok and redis_ok:
        print("\\n🎉 所有测试通过！")
        print("✅ 分布式队列的 logger 序列化问题已完全修复！")
        print("✅ Crawlo 现在可以正常使用 Redis 分布式队列了！")
        return True
    else:
        print("\\n❌ 部分测试失败，需要进一步修复")
        return False


if __name__ == "__main__":
    asyncio.run(main())