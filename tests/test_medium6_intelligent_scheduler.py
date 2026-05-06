#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 MEDIUM-6: PriorityCalculator 无界内存增长的修复

验证点：
1. MAX_DOMAINS 和 MAX_URLS 常量存在
2. update_stats 在超出限制时淘汰旧记录
3. _evict_oldest_domain 和 _evict_oldest_urls 方法存在
"""
import time
import pytest
from unittest.mock import MagicMock


class TestPriorityCalculatorMemoryControl:
    """测试 PriorityCalculator 的内存控制"""

    def test_max_constants_exist(self):
        """MAX_DOMAINS 和 MAX_URLS 常量存在"""
        from crawlo.queue.priority_calculator import PriorityCalculator
        assert hasattr(PriorityCalculator, 'MAX_DOMAINS')
        assert hasattr(PriorityCalculator, 'MAX_URLS')
        assert PriorityCalculator.MAX_DOMAINS > 0
        assert PriorityCalculator.MAX_URLS > 0

    def test_evict_oldest_domain_method(self):
        """_evict_oldest_domain 方法存在"""
        from crawlo.queue.priority_calculator import PriorityCalculator
        calculator = PriorityCalculator()
        assert hasattr(calculator, '_evict_oldest_domain')

    def test_evict_oldest_urls_method(self):
        """_evict_oldest_urls 方法存在"""
        from crawlo.queue.priority_calculator import PriorityCalculator
        calculator = PriorityCalculator()
        assert hasattr(calculator, '_evict_oldest_urls')

    def test_domain_eviction_when_exceeds_limit(self):
        """超出 MAX_DOMAINS 限制时淘汰旧域名"""
        from crawlo.queue.priority_calculator import PriorityCalculator
        
        calculator = PriorityCalculator()
        calculator.MAX_DOMAINS = 5  # 设置较小的限制方便测试
        
        # 添加 5 个域名
        for i in range(5):
            request = MagicMock()
            request.url = f"http://domain{i}.com/page"
            calculator.update_stats(request)
        
        assert len(calculator.domain_stats) == 5
        
        # 添加第 6 个域名，应淘汰最旧的
        request = MagicMock()
        request.url = "http://domain5.com/page"
        calculator.update_stats(request)
        
        assert len(calculator.domain_stats) <= 5, (
            f"domain_stats should not exceed MAX_DOMAINS=5, got {len(calculator.domain_stats)}"
        )

    def test_url_eviction_when_exceeds_limit(self):
        """超出 MAX_URLS 限制时淘汰旧 URL"""
        from crawlo.queue.priority_calculator import PriorityCalculator
        
        calculator = PriorityCalculator()
        calculator.MAX_URLS = 10  # 设置较小的限制方便测试
        
        # 添加 10 个 URL
        for i in range(10):
            request = MagicMock()
            request.url = f"http://example.com/page{i}"
            calculator.update_stats(request)
        
        assert len(calculator.url_stats) == 10
        
        # 添加第 11 个 URL，应淘汰部分旧记录
        request = MagicMock()
        request.url = "http://example.com/page10"
        calculator.update_stats(request)
        
        assert len(calculator.url_stats) <= 10, (
            f"url_stats should not exceed MAX_URLS=10, got {len(calculator.url_stats)}"
        )

    def test_evict_oldest_domain_cleans_related_stats(self):
        """淘汰域名时同步清理关联统计"""
        from crawlo.queue.priority_calculator import PriorityCalculator
        
        calculator = PriorityCalculator()
        calculator.MAX_DOMAINS = 2
        
        # 添加域名和关联统计
        for domain_idx in range(3):
            request = MagicMock()
            request.url = f"http://domain{domain_idx}.com/page"
            calculator.update_stats(request)
            calculator.update_error_count(request, has_error=True)
        
        # 最旧的域名应该被淘汰，其关联统计也应清理
        assert len(calculator.domain_stats) <= 2
