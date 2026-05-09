#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Queue 模块修复验证测试
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestDiskQueuePriority:
    """测试 DiskQueue 优先级语义修复"""
    
    def test_disk_queue_priority_sql_order(self):
        """验证 DiskQueue SQL 查询使用 ASC 排序"""
        # 读取 disk_queue.py 文件验证
        with open('crawlo/queue/disk_queue.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证注释已更新
        assert '数值越小优先级越高' in content
        
        # 验证 SQL 使用 ASC
        assert 'ORDER BY priority ASC, created_at ASC' in content
        # 确保没有 DESC
        assert 'ORDER BY priority DESC' not in content


class TestQueueManagerSemaphore:
    """测试 QueueManager 信号量修复"""
    
    def test_semaphore_release_only_when_acquired(self):
        """验证只在已获取信号量时才释放"""
        with open('crawlo/queue/queue_manager.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证有 semaphore_acquired 跟踪
        assert 'semaphore_acquired = False' in content
        assert 'semaphore_acquired = True' in content
        
        # 验证条件释放
        assert 'if semaphore_acquired and self._queue_semaphore:' in content


class TestRedisPriorityQueueTimeAPI:
    """测试 RedisPriorityQueue 时间 API 修复"""
    
    def test_uses_time_time_not_deprecated_api(self):
        """验证使用 time.time() 而非废弃的 asyncio.get_event_loop().time()"""
        with open('crawlo/queue/redis_priority_queue.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证使用 time.time()
        assert 'start_time = time.time()' in content
        
        # 验证没有使用废弃 API
        assert 'asyncio.get_event_loop().time()' not in content


class TestIntelligentBackpressureImport:
    """测试智能背压导入提示"""
    
    def test_import_failure_logs_debug_message(self):
        """验证导入失败时有 debug 日志"""
        with open('crawlo/queue/memory_queue.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证有 debug 日志
        assert 'Intelligent backpressure not available' in content
        assert 'logger.debug' in content


class TestPriorityCalculatorURLEviction:
    """测试 PriorityCalculator URL 淘汰效率"""
    
    def test_uses_iterator_not_list_copy(self):
        """验证使用迭代器而非列表副本"""
        with open('crawlo/queue/priority_calculator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证使用迭代器
        assert 'iter(self.url_stats.keys())' in content
        assert 'next(keys_iterator, None)' in content
        
        # 验证没有创建完整列表副本
        assert 'list(self.url_stats.keys())[:count]' not in content


class TestBackpressureConfigRefactor:
    """测试背压配置重构"""
    
    def test_extracted_method_exists(self):
        """验证提取了通用方法"""
        with open('crawlo/queue/config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证有通用方法
        assert 'def _get_backpressure_config' in content
        
        # 验证三种模式都使用该方法
        assert "cls._get_backpressure_config(" in content
        
        # 验证方法调用次数（应该至少 3 次：redis, memory, auto）
        count = content.count("cls._get_backpressure_config(")
        assert count >= 3


@pytest.mark.asyncio
async def test_disk_queue_priority_semantic_integration():
    """集成测试：DiskQueue 优先级语义"""
    try:
        from crawlo.queue.disk_queue import DiskQueue, DiskQueueConfig
        import tempfile
        import os
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DiskQueueConfig(
                path=tmpdir,
                name='test_queue',
                max_size=100
            )
            
            queue = DiskQueue(config)
            await queue.open()
            
            # 测试优先级：数值越小越优先
            await queue.put("low_priority", priority=10)
            await queue.put("high_priority", priority=1)
            await queue.put("medium_priority", priority=5)
            
            # 出队顺序应该是：high -> medium -> low
            item1 = await queue.get(timeout=0.1)
            item2 = await queue.get(timeout=0.1)
            item3 = await queue.get(timeout=0.1)
            
            assert item1 == "high_priority", f"Expected high_priority, got {item1}"
            assert item2 == "medium_priority", f"Expected medium_priority, got {item2}"
            assert item3 == "low_priority", f"Expected low_priority, got {item3}"
            
            await queue.close()
    except ImportError:
        pytest.skip("DiskQueue dependencies not available")


@pytest.mark.asyncio
async def test_priority_calculator_eviction_efficiency():
    """测试 PriorityCalculator URL 淘汰"""
    from crawlo.queue.priority_calculator import PriorityCalculator
    from unittest.mock import Mock
    
    # 创建子类修改常量（使用足够大的值确保 int(MAX_URLS * 0.1) >= 1）
    class TestPriorityCalculator(PriorityCalculator):
        MAX_URLS = 20  # 设置容量，淘汰数量 = int(20 * 0.1) = 2
    
    calc = TestPriorityCalculator()
    
    # 填充 URL 统计，超过容量
    for i in range(30):
        request = Mock()
        request.url = f"http://example.com/page{i}"
        calc.update_stats(request)
    
    # 验证不超过最大容量
    assert len(calc.url_stats) <= calc.MAX_URLS, f"Expected <= {calc.MAX_URLS}, got {len(calc.url_stats)}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
