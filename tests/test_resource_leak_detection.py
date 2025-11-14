#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
资源泄漏检测测试用例
====================

测试Crawlo框架的资源泄漏检测功能
"""

import asyncio
import unittest
from unittest.mock import Mock, patch
import tempfile
import os

from crawlo.utils.leak_detector import LeakDetector, get_leak_detector
from crawlo.utils.resource_manager import ResourceManager, get_resource_manager
from crawlo.utils.resource_leak_monitor import ResourceLeakMonitor, monitor_resource_leaks
from crawlo.crawler import Crawler


class TestResourceLeakDetection(unittest.TestCase):
    """资源泄漏检测测试"""
    
    def setUp(self):
        """测试前准备"""
        self.leak_detector = get_leak_detector("test")
        self.resource_manager = get_resource_manager("test")
    
    def tearDown(self):
        """测试后清理"""
        self.leak_detector.clear()
    
    def test_leak_detector_baseline(self):
        """测试泄漏检测器基线设置"""
        # 设置基线
        self.leak_detector.set_baseline("test_baseline")
        
        # 验证基线已设置
        self.assertIsNotNone(self.leak_detector._baseline)
        if self.leak_detector._baseline is not None:
            self.assertEqual(self.leak_detector._baseline.name, "test_baseline")
    
    def test_leak_detector_snapshot(self):
        """测试泄漏检测器快照功能"""
        # 记录快照
        snapshot1 = self.leak_detector.snapshot("test1")
        snapshot2 = self.leak_detector.snapshot("test2")
        
        # 验证快照已记录
        self.assertEqual(len(self.leak_detector._snapshots), 2)
        self.assertEqual(self.leak_detector._snapshots[0].name, "test1")
        self.assertEqual(self.leak_detector._snapshots[1].name, "test2")
    
    def test_resource_manager_registration(self):
        """测试资源管理器注册功能"""
        # 创建测试资源
        test_resource = Mock()
        cleanup_func = Mock()
        
        # 注册资源
        managed = self.resource_manager.register(
            test_resource, 
            cleanup_func, 
            name="test_resource"
        )
        
        # 验证资源已注册
        self.assertEqual(len(self.resource_manager._resources), 1)
        self.assertEqual(managed.name, "test_resource")
        self.assertEqual(managed.resource, test_resource)
    
    def test_resource_leak_monitor(self):
        """测试资源泄漏监控器"""
        # 创建监控器
        monitor = ResourceLeakMonitor("test_monitor")
        
        # 开始监控
        monitor.start_monitoring()
        
        # 验证监控已开始
        self.assertTrue(monitor._is_monitoring)
        
        # 记录快照
        monitor.take_snapshot("test_snapshot")
        
        # 验证快照已记录
        self.assertEqual(len(monitor.leak_detector._snapshots), 1)
        
        # 停止监控
        analysis = monitor.stop_monitoring()
        
        # 验证监控已停止
        self.assertFalse(monitor._is_monitoring)
        self.assertIn('status', analysis)
    
    async def async_test_monitor_decorator(self):
        """测试监控装饰器（异步）"""
        # 创建测试函数
        @monitor_resource_leaks("test_decorator", threshold_mb=1.0, snapshot_interval=0)  # 禁用定期快照避免测试复杂性
        async def test_function():
            await asyncio.sleep(0.1)
            return "test_result"
        
        # 执行函数
        result = await test_function()
        
        # 验证结果
        self.assertEqual(result, "test_result")
    
    def test_monitor_decorator_sync(self):
        """测试监控装饰器（同步）"""
        # 创建测试函数
        @monitor_resource_leaks("test_decorator_sync", threshold_mb=1.0, snapshot_interval=0)  # 禁用定期快照避免异步问题
        def test_function():
            return "test_result"
        
        # 执行函数
        result = test_function()
        
        # 验证结果
        self.assertEqual(result, "test_result")
    
    def test_leak_analysis_no_leak(self):
        """测试无泄漏情况下的分析"""
        # 设置基线
        self.leak_detector.set_baseline("baseline")
        
        # 等待一小段时间
        import time
        time.sleep(0.1)
        
        # 记录快照
        self.leak_detector.snapshot("snapshot1")
        self.leak_detector.snapshot("snapshot2")  # 需要至少2个快照才能分析
        
        # 分析
        analysis = self.leak_detector.analyze()
        
        # 验证分析成功
        self.assertIn(analysis['status'], ['healthy', 'insufficient_data'])  # 允许两种状态


if __name__ == "__main__":
    unittest.main()