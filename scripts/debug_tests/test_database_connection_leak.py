#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
"""
数据库连接泄漏测试
"""

import asyncio
from crawlo.utils.resource_manager import get_resource_manager, ResourceType


class MockDatabaseConnection:
    """模拟数据库连接"""
    def __init__(self):
        self.closed = False
        self.cursor = None
    
    def close(self):
        self.closed = True
        if self.cursor:
            self.cursor.close()
    
    def get_cursor(self):
        if not self.cursor:
            self.cursor = MockCursor()
        return self.cursor


class MockCursor:
    """模拟数据库游标"""
    def __init__(self):
        self.closed = False
    
    def close(self):
        self.closed = True
    
    def execute(self, query):
        return "query result"


class DatabasePipeline:
    """数据库管道"""
    def __init__(self):
        self.connection = MockDatabaseConnection()
        self.resource_manager = get_resource_manager("db_test")
        self.resource_manager.register(
            self,
            self._close_connection,
            ResourceType.OTHER,
            "database_pipeline"
        )
    
    def _close_connection(self, resource=None):
        """关闭数据库连接"""
        self.connection.close()


async def test_database_connection_leak():
    """测试数据库连接是否正确管理"""
    # 创建数据库管道
    db_pipeline = DatabasePipeline()
    
    # 使用数据库连接
    cursor = db_pipeline.connection.get_cursor()
    result = cursor.execute("SELECT * FROM test")
    
    # 检查资源是否正确注册
    active_resources = db_pipeline.resource_manager.get_active_resources()
    assert len(active_resources) == 1
    assert active_resources[0].name == "database_pipeline"
    
    # 检查连接和游标状态
    assert db_pipeline.connection.closed == False
    assert cursor.closed == False
    
    # 清理资源
    await db_pipeline.resource_manager.cleanup_all()
    
    # 验证资源已清理
    active_resources = db_pipeline.resource_manager.get_active_resources()
    assert len(active_resources) == 0
    
    # 验证连接已标记为关闭（实际关闭由清理函数处理）
    assert db_pipeline.connection.closed == True
    
    print("数据库连接泄漏测试通过")


if __name__ == "__main__":
    asyncio.run(test_database_connection_leak())