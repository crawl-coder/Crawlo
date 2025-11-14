#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis连接泄漏测试
"""

import asyncio
from crawlo.utils.resource_manager import get_resource_manager, ResourceType
from crawlo.utils.redis_manager import get_redis_pool


class MockRedisClient:
    """模拟Redis客户端"""
    def __init__(self):
        self.closed = False
    
    async def close(self):
        self.closed = True
    
    async def ping(self):
        return True


class MockRedisPool:
    """模拟Redis连接池"""
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = MockRedisClient()
    
    async def get_connection(self):
        return self.client
    
    async def close(self):
        await self.client.close()


async def test_redis_connection_leak():
    """测试Redis连接是否正确管理"""
    # 创建资源管理器
    resource_manager = get_resource_manager("redis_test")
    
    # 创建Redis连接池
    redis_pool = MockRedisPool("redis://localhost:6379/0")
    
    # 注册到资源管理器
    resource_manager.register(
        redis_pool,
        lambda pool: pool.close(),
        ResourceType.REDIS_POOL,
        "test_redis_pool"
    )
    
    # 使用连接池
    client = await redis_pool.get_connection()
    await client.ping()
    
    # 检查资源是否正确注册
    active_resources = resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "test_redis_pool"
    
    # 清理资源
    await resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = resource_manager.get_active_resources()
    assert len(active_resources) == 0
    assert redis_pool.client.closed == True
    
    print("Redis连接泄漏测试通过")


if __name__ == "__main__":
    asyncio.run(test_redis_connection_leak())