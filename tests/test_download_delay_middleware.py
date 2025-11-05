#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DownloadDelayMiddleware 测试文件
用于测试下载延迟中间件的功能
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.download_delay import DownloadDelayMiddleware
from crawlo.exceptions import NotConfiguredError
from crawlo.settings.setting_manager import SettingManager


class MockLogger:
    """Mock Logger 类，用于测试日志输出"""
    def __init__(self, name, level=None):
        self.name = name
        self.level = level
        self.logs = []

    def debug(self, msg):
        self.logs.append(('debug', msg))

    def info(self, msg):
        self.logs.append(('info', msg))

    def warning(self, msg):
        self.logs.append(('warning', msg))

    def error(self, msg):
        self.logs.append(('error', msg))


class MockStats:
    """Mock Stats 类，用于测试统计信息"""
    def __init__(self):
        self.stats = {}

    def inc_value(self, key, value=1):
        if key in self.stats:
            self.stats[key] += value
        else:
            self.stats[key] = value


class TestDownloadDelayMiddleware(unittest.TestCase):
    """DownloadDelayMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings
        
        # 创建请求和爬虫模拟对象
        self.request = Mock()
        self.spider = Mock()

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_without_delay(self, mock_get_logger):
        """测试没有设置DOWNLOAD_DELAY时中间件初始化"""
        # 设置DOWNLOAD_DELAY为0
        self.settings.set('DOWNLOAD_DELAY', 0)
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')
        
        # 应该抛出NotConfiguredError异常
        with self.assertRaises(NotConfiguredError) as context:
            DownloadDelayMiddleware.create_instance(self.crawler)
        
        self.assertIn("DOWNLOAD_DELAY not set or is zero", str(context.exception))

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_delay(self, mock_get_logger):
        """测试正确设置DOWNLOAD_DELAY时中间件初始化"""
        # 设置DOWNLOAD_DELAY
        self.settings.set('DOWNLOAD_DELAY', 2.0)
        self.settings.set('RANDOMNESS', False)
        self.settings.set('RANDOM_RANGE', [0.5, 1.5])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')
        
        # 应该正常创建实例
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, DownloadDelayMiddleware)
        self.assertEqual(middleware.delay, 2.0)
        self.assertFalse(middleware.randomness)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_randomness(self, mock_get_logger):
        """测试启用随机延迟时中间件初始化"""
        # 设置DOWNLOAD_DELAY和随机配置
        self.settings.set('DOWNLOAD_DELAY', 1.0)
        self.settings.set('RANDOMNESS', True)
        self.settings.set('RANDOM_RANGE', [0.5, 2.0])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')
        
        # 应该正常创建实例
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, DownloadDelayMiddleware)
        self.assertEqual(middleware.delay, 1.0)
        self.assertTrue(middleware.randomness)
        self.assertEqual(middleware.floor, 0.5)
        self.assertEqual(middleware.upper, 2.0)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_invalid_random_range(self, mock_get_logger):
        """测试随机范围配置无效时中间件初始化"""
        # 设置DOWNLOAD_DELAY和无效的随机配置
        self.settings.set('DOWNLOAD_DELAY', 1.0)
        self.settings.set('RANDOMNESS', True)
        self.settings.set('RANDOM_RANGE', ['invalid', 'range'])
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')
        
        # 应该正常创建实例，使用默认随机范围
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, DownloadDelayMiddleware)
        self.assertEqual(middleware.floor, 0.5)
        self.assertEqual(middleware.upper, 1.5)

    @patch('crawlo.utils.log.get_logger')
    def test_middleware_initialization_with_incomplete_random_range(self, mock_get_logger):
        """测试随机范围配置不完整时中间件初始化"""
        # 设置DOWNLOAD_DELAY和不完整的随机配置
        self.settings.set('DOWNLOAD_DELAY', 1.0)
        self.settings.set('RANDOMNESS', True)
        self.settings.set('RANDOM_RANGE', [0.8])  # 只有一个值
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')
        
        # 应该正常创建实例，使用默认随机范围
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        self.assertIsInstance(middleware, DownloadDelayMiddleware)
        self.assertEqual(middleware.floor, 0.5)
        self.assertEqual(middleware.upper, 1.5)

    @patch('crawlo.middleware.download_delay.sleep')
    @patch('crawlo.utils.log.get_logger')
    def test_process_request_without_randomness(self, mock_get_logger, mock_sleep):
        """测试不启用随机延迟时的请求处理"""
        # 设置DOWNLOAD_DELAY
        self.settings.set('DOWNLOAD_DELAY', 1.5)
        self.settings.set('RANDOMNESS', False)
        self.settings.set('LOG_LEVEL', 'DEBUG')  # 使用DEBUG级别以启用日志
        
        mock_logger = MockLogger('DownloadDelayMiddleware')
        mock_get_logger.return_value = mock_logger
        
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        
        # 执行请求处理
        asyncio.run(middleware.process_request(self.request, self.spider))
        
        # 验证sleep被调用且参数正确
        mock_sleep.assert_called_once_with(1.5)

    @patch('crawlo.middleware.download_delay.sleep')
    @patch('crawlo.middleware.download_delay.uniform')
    @patch('crawlo.utils.log.get_logger')
    def test_process_request_with_randomness(self, mock_get_logger, mock_uniform, mock_sleep):
        """测试启用随机延迟时的请求处理"""
        # 设置DOWNLOAD_DELAY和随机配置
        self.settings.set('DOWNLOAD_DELAY', 2.0)
        self.settings.set('RANDOMNESS', True)
        self.settings.set('RANDOM_RANGE', [0.5, 1.5])
        self.settings.set('LOG_LEVEL', 'DEBUG')  # 使用DEBUG级别以启用日志
        
        mock_logger = MockLogger('DownloadDelayMiddleware')
        mock_get_logger.return_value = mock_logger
        mock_uniform.return_value = 2.5  # 模拟随机数返回2.5
        
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        
        # 执行请求处理
        asyncio.run(middleware.process_request(self.request, self.spider))
        
        # 验证uniform被调用且参数正确
        mock_uniform.assert_called_once_with(1.0, 3.0)  # 2.0*0.5=1.0, 2.0*1.5=3.0
        # 验证sleep被调用且参数正确
        mock_sleep.assert_called_once_with(2.5)

    @patch('crawlo.middleware.download_delay.sleep')
    @patch('crawlo.utils.log.get_logger')
    def test_process_request_with_stats(self, mock_get_logger, mock_sleep):
        """测试带统计信息的请求处理"""
        # 设置DOWNLOAD_DELAY
        self.settings.set('DOWNLOAD_DELAY', 1.0)
        self.settings.set('RANDOMNESS', False)
        self.settings.set('LOG_LEVEL', 'INFO')
        
        # 添加统计收集器到爬虫
        mock_stats = MockStats()
        self.crawler.stats = mock_stats
        
        mock_logger = MockLogger('DownloadDelayMiddleware')
        mock_get_logger.return_value = mock_logger
        
        middleware = DownloadDelayMiddleware.create_instance(self.crawler)
        
        # 执行请求处理
        asyncio.run(middleware.process_request(self.request, self.spider))
        
        # 验证统计信息
        self.assertIn('download_delay/fixed_count', mock_stats.stats)
        self.assertEqual(mock_stats.stats['download_delay/fixed_count'], 1)
        self.assertIn('download_delay/fixed_total_time', mock_stats.stats)
        self.assertEqual(mock_stats.stats['download_delay/fixed_total_time'], 1.0)


if __name__ == '__main__':
    unittest.main()