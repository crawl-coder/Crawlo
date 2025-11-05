#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具测试
测试 PerformanceMonitor, PerformanceTimer, performance_monitor_decorator
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 尝试导入性能监控工具
try:
    from crawlo.utils.performance_monitor import PerformanceMonitor, PerformanceTimer, performance_monitor_decorator
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    PerformanceMonitor = None
    PerformanceTimer = None
    performance_monitor_decorator = None


class TestPerformanceTimer(unittest.TestCase):
    """性能计时器测试"""

    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def setUp(self):
        """测试前准备"""
        self.timer = PerformanceTimer("test_timer")
        
    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def test_timer_initialization(self):
        """测试计时器初始化"""
        self.assertEqual(self.timer.name, "test_timer")
        self.assertIsNone(self.timer.start_time)
        self.assertIsNone(self.timer.end_time)
        
    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def test_timer_context_manager(self):
        """测试计时器上下文管理器"""
        with self.timer as t:
            # 在这里执行一些操作
            result = 1 + 1
            
        self.assertEqual(result, 2)
        # 验证计时器已启动和停止
        self.assertIsNotNone(t.start_time)
        self.assertIsNotNone(t.end_time)
        
    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def test_timer_start_stop(self):
        """测试计时器启动和停止"""
        self.timer.start()
        self.assertIsNotNone(self.timer.start_time)
        
        # 等待一小段时间
        import time
        time.sleep(0.01)
        
        elapsed = self.timer.stop()
        self.assertIsNotNone(self.timer.end_time)
        self.assertIsInstance(elapsed, float)
        self.assertGreater(elapsed, 0)


class TestPerformanceMonitor(unittest.TestCase):
    """性能监控器测试"""

    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def setUp(self):
        """测试前准备"""
        self.monitor = PerformanceMonitor("test_monitor")
        
    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        self.assertEqual(self.monitor.start_time, self.monitor.start_time)
        self.assertIsInstance(self.monitor.metrics, dict)
        self.assertIn('cpu_usage', self.monitor.metrics)
        self.assertIn('memory_usage', self.monitor.metrics)
        self.assertIn('network_io', self.monitor.metrics)
        self.assertIn('disk_io', self.monitor.metrics)


class TestPerformanceMonitorDecorator(unittest.TestCase):
    """性能监控装饰器测试"""

    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def test_performance_monitor_decorator_sync(self):
        """测试同步函数的性能监控装饰器"""
        @performance_monitor_decorator(name="test_sync_function")
        def sync_function():
            return "test_result"
            
        result = sync_function()
        self.assertEqual(result, "test_result")
        
    @unittest.skipIf(not PSUTIL_AVAILABLE, "psutil not available")
    def test_performance_monitor_decorator_async(self):
        """测试异步函数的性能监控装饰器"""
        @performance_monitor_decorator(name="test_async_function")
        async def async_function():
            await asyncio.sleep(0.01)  # 模拟异步操作
            return "async_result"
            
        # 使用事件循环运行异步函数
        result = asyncio.run(async_function())
        self.assertEqual(result, "async_result")


if __name__ == '__main__':
    unittest.main()