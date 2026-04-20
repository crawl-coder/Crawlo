#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MemoryFilter 异步安全测试
"""
import pytest
import asyncio
import sys
import os
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockSettings:
    """模拟设置对象"""
    def __init__(self, **kwargs):
        self._data = kwargs
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def get_bool(self, key, default=False):
        val = self._data.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ('true', '1', 'yes', 'on')
        return bool(val)


class MockCrawler:
    """模拟爬虫对象"""
    def __init__(self):
        self.settings = MockSettings(
            FILTER_DEBUG=False,
            MEMORY_FILTER_MAX_CAPACITY=10000,
            MEMORY_FILTER_CLEANUP_THRESHOLD=0.8
        )
        self.stats = None


class MockRequest:
    """模拟请求对象"""
    def __init__(self, url, method='GET', body=None, headers=None, meta=None):
        self.url = url
        self.method = method
        self.body = body or b''
        self.headers = headers or {}
        self.meta = meta or {}


from crawlo.filters.memory_filter import MemoryFilter, MemoryFileFilter


class TestMemoryFilterAsync:
    """测试 MemoryFilter 异步安全"""
    
    @pytest.fixture
    def filter_instance(self):
        """创建过滤器实例"""
        crawler = MockCrawler()
        return MemoryFilter(crawler)
    
    @pytest.mark.asyncio
    async def test_requested_async(self, filter_instance):
        """测试异步请求检查"""
        request = MockRequest("http://example.com/1")
        
        # 第一次应该返回 False（新增）
        result = await filter_instance.requested_async(request)
        assert result == False
        
        # 第二次应该返回 True（重复）
        result = await filter_instance.requested_async(request)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, filter_instance):
        """测试并发请求检查"""
        requests = [MockRequest(f"http://example.com/{i}") for i in range(100)]
        
        # 并发检查
        results = await asyncio.gather(*[
            filter_instance.requested_async(req) for req in requests
        ])
        
        # 第一次都应该是新增
        assert all(r == False for r in results)
        
        # 再次检查应该都是重复
        results = await asyncio.gather(*[
            filter_instance.requested_async(req) for req in requests
        ])
        assert all(r == True for r in results)
    
    @pytest.mark.asyncio
    async def test_add_fingerprint_async(self, filter_instance):
        """测试异步添加指纹"""
        await filter_instance.add_fingerprint_async("fp1")
        assert "fp1" in filter_instance
        
        await filter_instance.add_fingerprint_async("fp1")  # 重复添加
        
        assert filter_instance._unique_count == 1
    
    @pytest.mark.asyncio
    async def test_clear_async(self, filter_instance):
        """测试异步清空"""
        for i in range(10):
            await filter_instance.add_fingerprint_async(f"fp{i}")
        
        await filter_instance.clear_async()
        
        assert len(filter_instance.fingerprints) == 0
        assert filter_instance._unique_count == 0
    
    def test_deprecated_requested(self, filter_instance):
        """测试废弃警告"""
        request = MockRequest("http://example.com/test")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            filter_instance.requested(request)
            
            # requested 和内部调用的 add_fingerprint 都会产生警告
            assert len(w) >= 1
            # 至少有一个是 DeprecationWarning
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
            assert any("deprecated" in str(warning.message).lower() for warning in w)


class TestMemoryFileFilterAsync:
    """测试 MemoryFileFilter 异步安全"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """创建临时目录"""
        return str(tmp_path / "test_fingerprints")
    
    @pytest.fixture
    def filter_instance(self, temp_dir):
        """创建过滤器实例"""
        crawler = MockCrawler()
        crawler.settings._data["REQUEST_DIR"] = temp_dir
        return MemoryFileFilter(crawler)
    
    @pytest.mark.asyncio
    async def test_add_fingerprint_async(self, filter_instance):
        """测试异步添加指纹"""
        await filter_instance.add_fingerprint_async("fp1")
        assert "fp1" in filter_instance
        
        await filter_instance.add_fingerprint_async("fp2")
        assert "fp2" in filter_instance
    
    @pytest.mark.asyncio
    async def test_contains_async(self, filter_instance):
        """测试异步 contains"""
        await filter_instance.add_fingerprint_async("fp1")
        
        result = await filter_instance.contains_async("fp1")
        assert result == True
        
        result = await filter_instance.contains_async("fp2")
        assert result == False
    
    @pytest.mark.asyncio
    async def test_close_async(self, filter_instance):
        """测试异步关闭"""
        await filter_instance.add_fingerprint_async("fp1")
        await filter_instance.close_async()
        
        # 关闭后文件应该已关闭


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
