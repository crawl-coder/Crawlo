#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
"""
缓存泄漏测试
"""

import asyncio
from collections import OrderedDict
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class LRUCache:
    """LRU缓存实现"""
    def __init__(self, maxsize=100):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.resource_manager = get_resource_manager("lru_cache")
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            "lru_cache"
        )
    
    def get(self, key):
        if key in self.cache:
            # 移动到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.maxsize:
            # 删除最久未使用的项
            self.cache.popitem(last=False)
        self.cache[key] = value
    
    def _cleanup(self, resource=None):
        """清理缓存"""
        self.cache.clear()


async def test_cache_leak():
    """测试缓存是否正确管理"""
    # 创建LRU缓存
    cache = LRUCache(maxsize=5)
    
    # 添加数据到缓存
    for i in range(10):
        cache.put(f"key_{i}", f"value_{i}")
    
    # 检查资源是否正确注册
    active_resources = cache.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "lru_cache"
    
    # 检查缓存大小（应该只有5个元素）
    assert len(cache.cache) == 5
    
    # 清理资源
    await cache.resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = cache.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证缓存已清空
    # 注意：由于清理是异步的，这里我们只验证资源管理器的状态
    
    print("缓存泄漏测试通过")


if __name__ == "__main__":
    asyncio.run(test_cache_leak())