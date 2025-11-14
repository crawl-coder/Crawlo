#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受控爬虫混入类测试
测试 ControlledRequestMixin, AsyncControlledRequestMixin
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.controlled_spider_mixin import ControlledRequestMixin, AsyncControlledRequestMixin


class TestControlledRequestMixin(unittest.TestCase):
    """受控请求混入类测试"""

    def setUp(self):
        """测试前准备"""
        self.mixin = ControlledRequestMixin()
        
    def test_mixin_initialization(self):
        """测试混入类初始化"""
        self.assertEqual(self.mixin.max_pending_requests, 100)
        self.assertEqual(self.mixin.batch_size, 50)
        self.assertEqual(self.mixin.generation_interval, 0.1)
        self.assertEqual(self.mixin.backpressure_threshold, 200)
        
    def test_mixin_configuration(self):
        """测试混入类配置"""
        # 修改配置
        self.mixin.max_pending_requests = 200
        self.mixin.batch_size = 100
        self.mixin.generation_interval = 0.05
        self.mixin.backpressure_threshold = 300
        
        self.assertEqual(self.mixin.max_pending_requests, 200)
        self.assertEqual(self.mixin.batch_size, 100)
        self.assertEqual(self.mixin.generation_interval, 0.05)
        self.assertEqual(self.mixin.backpressure_threshold, 300)
        
    def test_get_generation_stats(self):
        """测试获取生成统计信息"""
        stats = self.mixin.get_generation_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('generated', stats)
        self.assertIn('skipped', stats)
        self.assertIn('backpressure_events', stats)
        self.assertIn('total_generated', stats)
        self.assertIn('last_generation_time', stats)


class TestAsyncControlledRequestMixin(unittest.TestCase):
    """异步受控请求混入类测试"""

    def setUp(self):
        """测试前准备"""
        self.mixin = AsyncControlledRequestMixin()
        
    def test_async_mixin_initialization(self):
        """测试异步混入类初始化"""
        self.assertEqual(self.mixin.max_concurrent_generations, 10)
        self.assertEqual(self.mixin.queue_monitor_interval, 1.0)
        
    def test_async_mixin_configuration(self):
        """测试异步混入类配置"""
        # 修改配置
        self.mixin.max_concurrent_generations = 20
        self.mixin.queue_monitor_interval = 0.5
        
        self.assertEqual(self.mixin.max_concurrent_generations, 20)
        self.assertEqual(self.mixin.queue_monitor_interval, 0.5)


if __name__ == '__main__':
    unittest.main()