#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
HTTP连接泄漏测试
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, '/Users/oscar/projects/Crawlo')

import aiohttp
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


async def test_http_connection_leak():
    """测试HTTP连接是否正确管理"""
    # 创建资源管理器
    resource_manager = get_resource_manager("http_test")
    
    # 创建HTTP会话
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=30)
    )
    
    # 注册到资源管理器
    resource_manager.register(
        session,
        lambda s: s.close() if not s.closed else None,
        ResourceType.SESSION,
        "test_http_session"
    )
    
    # 使用会话
    try:
        async with session.get("https://httpbin.org/get") as response:
            await response.text()
    except Exception:
        pass
    
    # 检查资源是否正确注册
    active_resources = resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "test_http_session"
    
    # 清理资源
    await resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    print("HTTP连接泄漏测试通过")


if __name__ == "__main__":
    # 添加项目根目录到路径
    sys.path.insert(0, '/Users/oscar/projects/Crawlo')
    asyncio.run(test_http_connection_leak())