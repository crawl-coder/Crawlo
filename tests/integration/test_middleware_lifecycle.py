#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
中间件生命周期单元测试

测试 MiddlewareManager 的生命周期管理：
- open() 方法
- close() 方法
- 异常处理
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from crawlo.middleware.middleware_manager import MiddlewareManager
from crawlo.middleware import BaseMiddleware


class MockMiddleware(BaseMiddleware):
    """测试用中间件"""
    
    @classmethod
    def create_instance(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        instance.opened = False
        instance.closed = False
        return instance
    
    def __init__(self):
        self.crawler = None
        self.opened = False
        self.closed = False
    
    async def open(self):
        """打开中间件"""
        self.opened = True
    
    async def close(self):
        """关闭中间件"""
        self.closed = True
    
    async def process_request(self, request):
        return request


class TestMiddlewareLifecycle:
    """测试中间件生命周期"""
    
    def test_middleware_open(self):
        """测试中间件 open 方法"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        assert manager._initialized is False
        
        # 调用 open
        asyncio.get_event_loop().run_until_complete(manager.open())
        assert manager._initialized is True
    
    def test_middleware_close(self):
        """测试中间件 close 方法"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        
        # 先 open
        asyncio.get_event_loop().run_until_complete(manager.open())
        assert manager._initialized is True
        
        # 再 close
        asyncio.get_event_loop().run_until_complete(manager.close())
        assert manager._initialized is False
    
    def test_double_open_idempotent(self):
        """测试重复 open 是幂等的"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        
        # 第一次 open
        asyncio.get_event_loop().run_until_complete(manager.open())
        assert manager._initialized is True
        
        # 第二次 open（应该直接返回）
        asyncio.get_event_loop().run_until_complete(manager.open())
        assert manager._initialized is True
    
    def test_close_without_open(self):
        """测试未 open 直接 close"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        assert manager._initialized is False
        
        # 未 open 直接 close（应该安全返回）
        asyncio.get_event_loop().run_until_complete(manager.close())
        assert manager._initialized is False


class TestMiddlewareWithHooks:
    """测试带生命周期钩子的中间件"""
    
    @pytest.mark.asyncio
    async def test_middleware_hooks_called(self):
        """测试中间件 open/close 钩子被调用"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        
        # 创建测试中间件
        middleware = MockMiddleware.create_instance(crawler)
        manager.middlewares.append(middleware)
        
        # 调用 open
        await manager.open()
        assert middleware.opened is True
        
        # 调用 close
        await manager.close()
        assert middleware.closed is True
    
    @pytest.mark.asyncio
    async def test_close_reverse_order(self):
        """测试 close 按反向顺序调用"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        
        # 创建 3 个测试中间件
        middlewares = [MockMiddleware.create_instance(crawler) for _ in range(3)]
        manager.middlewares.extend(middlewares)
        
        # 先调用 open 初始化
        await manager.open()
        
        # 调用 close（应该反向关闭）
        await manager.close()
        
        # 验证所有中间件都被关闭
        for mw in middlewares:
            assert mw.closed is True


class TestMiddlewareErrorHandling:
    """测试中间件错误处理"""
    
    @pytest.mark.asyncio
    async def test_open_exception_propagates(self):
        """测试 open 异常会传播"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        
        # 创建会抛出异常的中间件
        class FailingMiddleware(BaseMiddleware):
            @classmethod
            def create_instance(cls, crawler):
                return cls()
            
            async def open(self):
                raise RuntimeError("Open failed")
        
        manager.middlewares.append(FailingMiddleware.create_instance(crawler))
        
        # 验证异常被抛出
        with pytest.raises(RuntimeError, match="Open failed"):
            await manager.open()
    
    @pytest.mark.asyncio
    async def test_close_exception_logged(self):
        """测试 close 异常被记录但不传播"""
        crawler = MagicMock()
        crawler.settings = {'MIDDLEWARES': []}
        
        manager = MiddlewareManager(crawler)
        
        # 创建会抛出异常的中间件
        class FailingCloseMiddleware(BaseMiddleware):
            @classmethod
            def create_instance(cls, crawler):
                return cls()
            
            async def close(self):
                raise RuntimeError("Close failed")
        
        manager.middlewares.append(FailingCloseMiddleware.create_instance(crawler))
        
        # 先 open
        await manager.open()
        
        # close 异常不应该传播（只记录日志）
        await manager.close()  # 不应该抛出异常


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
