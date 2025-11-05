#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 Redis 连接配置修复
"""
import asyncio
from crawlo.queue.redis_priority_queue import RedisPriorityQueue
from crawlo.settings.default_settings import REDIS_URL

async def test_redis_config():
    """测试修复后的 Redis 配置"""
    print(f"测试 Redis 配置: {REDIS_URL}")
    
    try:
        queue = RedisPriorityQueue(redis_url=REDIS_URL)
        await queue.connect()
        print("Redis 连接成功！")
        await queue.close()
        return True
    except Exception as e:
        print(f"Redis 连接失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_redis_config())
    if success:
        print("配置修复成功！现在可以运行你的爬虫了。")
    else:
        print("❌ 配置仍有问题，请检查 Redis 服务状态。")