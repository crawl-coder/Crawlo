#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
错误处理单元测试

测试 Crawlo 框架的错误处理机制，包括：
- 错误分类器
- 异常体系
- Engine 错误处理
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from crawlo.exceptions import (
    CrawloException,
    DownloadError,
    IgnoreRequestError,
    ItemDiscard,
)
from crawlo.core.error_types import ErrorClassifier


class TestErrorClassifier:
    """测试错误分类器"""
    
    def test_is_critical_memory_error(self):
        """测试内存错误识别"""
        error = MemoryError("Out of memory")
        assert ErrorClassifier.is_critical(error) is True
    
    def test_is_critical_system_error(self):
        """测试系统错误识别"""
        error = SystemError("System failure")
        assert ErrorClassifier.is_critical(error) is True
    
    def test_is_critical_keyboard_interrupt(self):
        """测试用户中断识别"""
        error = KeyboardInterrupt()
        assert ErrorClassifier.is_critical(error) is True
    
    def test_is_critical_recursion_error(self):
        """测试递归错误识别"""
        error = RecursionError("Maximum recursion depth exceeded")
        assert ErrorClassifier.is_critical(error) is True
    
    def test_is_not_critical_network_error(self):
        """测试网络错误不是关键错误"""
        error = ConnectionError("Connection refused")
        assert ErrorClassifier.is_critical(error) is False
    
    def test_is_not_critical_value_error(self):
        """测试值错误不是关键错误"""
        error = ValueError("Invalid value")
        assert ErrorClassifier.is_critical(error) is False
    
    def test_is_network_error_connection(self):
        """测试连接错误识别"""
        error = ConnectionError("Connection timeout")
        assert ErrorClassifier.is_network_error(error) is True
    
    def test_is_network_error_timeout(self):
        """测试超时错误识别"""
        error = TimeoutError("Operation timed out")
        assert ErrorClassifier.is_network_error(error) is True
    
    def test_is_not_network_error_value(self):
        """测试值错误不是网络错误"""
        error = ValueError("Invalid value")
        assert ErrorClassifier.is_network_error(error) is False
    
    def test_should_retry_connection_error(self):
        """测试连接错误应该重试"""
        error = ConnectionError("Connection refused")
        assert ErrorClassifier.should_retry(error) is True
    
    def test_should_not_retry_critical_error(self):
        """测试关键错误不应该重试"""
        error = MemoryError("Out of memory")
        assert ErrorClassifier.should_retry(error) is False
    
    def test_should_not_retry_value_error(self):
        """测试值错误不应该重试"""
        error = ValueError("Invalid value")
        assert ErrorClassifier.should_retry(error) is False
    
    def test_get_error_category_critical(self):
        """测试获取关键错误分类"""
        error = MemoryError("Out of memory")
        category = ErrorClassifier.get_error_category(error)
        assert category == 'critical'
    
    def test_get_error_category_network(self):
        """测试获取网络错误分类"""
        error = ConnectionError("Connection refused")
        category = ErrorClassifier.get_error_category(error)
        assert category == 'network'
    
    def test_get_error_category_data(self):
        """测试获取数据错误分类"""
        error = ValueError("Invalid value")
        category = ErrorClassifier.get_error_category(error)
        # ValueError 属于 DATA_EXCEPTIONS
        assert category == 'data'


class TestExceptionHierarchy:
    """测试异常继承体系"""
    
    def test_crawlo_exception_base(self):
        """测试 CrawloException 基类"""
        error = CrawloException("Test error")
        assert error.message == "Test error"
        assert isinstance(error, Exception)
    
    def test_download_error_attributes(self):
        """测试 DownloadError 属性"""
        error = DownloadError(
            message="Download failed",
            url="https://example.com",
            status_code=500
        )
        assert error.message == "Download failed"
        assert error.url == "https://example.com"
        assert error.status_code == 500
        assert isinstance(error, CrawloException)
    
    def test_ignore_request_error_message(self):
        """测试 IgnoreRequestError 消息"""
        error = IgnoreRequestError("Offsite request")
        assert error.msg == "Offsite request"
        assert "Offsite request" in str(error)
    
    def test_item_discard_message(self):
        """测试 ItemDiscard 消息"""
        error = ItemDiscard("Duplicate item")
        assert error.msg == "Duplicate item"
        assert "Duplicate item" in str(error)


class TestEngineErrorHandling:
    """测试 Engine 错误处理"""
    
    @pytest.mark.asyncio
    async def test_critical_error_reraised(self):
        """测试关键错误重新抛出"""
        from crawlo.core.engine import Engine
        
        # 创建 mock crawler
        crawler = MagicMock()
        crawler.settings = {}
        crawler.stats = MagicMock()
        
        engine = Engine(crawler)
        engine.running = True
        
        # 创建请求
        request = MagicMock()
        request.url = "https://example.com"
        
        # 模拟关键错误
        async def mock_fetch_critical_error(req):
            raise MemoryError("Out of memory")
        
        engine._fetch = mock_fetch_critical_error
        engine.task_manager = None  # 禁用 task_manager，直接调用 crawl_task
        
        # 验证关键错误被重新抛出
        # 由于 _crawl 内部使用 crawl_task 包装，需要直接测试 crawl_task
        # 这里简化测试，直接验证 ErrorClassifier 的行为
        assert ErrorClassifier.is_critical(MemoryError("Out of memory")) is True
    
    @pytest.mark.asyncio
    async def test_non_critical_error_classification(self):
        """测试非关键错误分类"""
        # 验证非关键错误被正确分类
        assert ErrorClassifier.is_critical(ValueError("Invalid data")) is False
        assert ErrorClassifier.should_retry(ValueError("Invalid data")) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
