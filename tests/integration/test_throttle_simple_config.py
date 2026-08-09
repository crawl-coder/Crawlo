#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
DownloadDelayMiddleware 简单配置测试
覆盖 DOWNLOAD_DELAY / RANDOMNESS / DOWNLOAD_DELAY_OVERRIDES 配置路径。
（原 ThrottleMiddleware 已在重构中移除，此文件按当前 API 重写）
"""

import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.download_delay import DownloadDelayMiddleware
from crawlo.settings.setting_manager import SettingManager


class MockLogger:
    """Mock Logger for testing"""

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


class TestDownloadDelaySimpleConfig(unittest.TestCase):
    """Test DownloadDelayMiddleware simple configuration mode"""

    def setUp(self):
        """Test setup"""
        self.crawler = Mock()
        self.settings = SettingManager()
        self.crawler.settings = self.settings

    @patch('crawlo.middleware.download_delay.get_logger')
    def test_simple_download_delay_config(self, mock_get_logger):
        """Test simple DOWNLOAD_DELAY configuration"""
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')

        self.settings.set('DOWNLOAD_DELAY', 0.5)
        self.settings.set('RANDOMNESS', False)

        middleware = DownloadDelayMiddleware.create_instance(self.crawler)

        self.assertEqual(middleware.default_delay, 0.5)
        self.assertFalse(middleware.randomness)

    @patch('crawlo.middleware.download_delay.get_logger')
    def test_download_delay_with_randomness(self, mock_get_logger):
        """Test DOWNLOAD_DELAY with RANDOMNESS enabled"""
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')

        self.settings.set('DOWNLOAD_DELAY', 2.0)
        self.settings.set('RANDOMNESS', True)

        middleware = DownloadDelayMiddleware.create_instance(self.crawler)

        self.assertEqual(middleware.default_delay, 2.0)
        self.assertTrue(middleware.randomness)

    @patch('crawlo.middleware.download_delay.get_logger')
    def test_delay_without_explicit_randomness(self, mock_get_logger):
        """Test DOWNLOAD_DELAY is the unified configuration"""
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')

        self.settings.set('DOWNLOAD_DELAY', 0.5)

        middleware = DownloadDelayMiddleware.create_instance(self.crawler)

        self.assertEqual(middleware.default_delay, 0.5)

    @patch('crawlo.middleware.download_delay.get_logger')
    def test_domain_specific_config(self, mock_get_logger):
        """Test domain-specific configuration"""
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')

        self.settings.set('DOWNLOAD_DELAY', 1.0)
        self.settings.set('DOWNLOAD_DELAY_OVERRIDES', {
            'example.com': 2.0,
            'api.example.com': 0.1,
        })

        middleware = DownloadDelayMiddleware.create_instance(self.crawler)

        self.assertEqual(middleware.default_delay, 1.0)
        self.assertEqual(middleware.domain_overrides.get('example.com'), 2.0)
        self.assertEqual(middleware.domain_overrides.get('api.example.com'), 0.1)

    @patch('crawlo.middleware.download_delay.get_logger')
    def test_disabled_delay(self, mock_get_logger):
        """Test disabled delay (DOWNLOAD_DELAY=0)"""
        mock_get_logger.return_value = MockLogger('DownloadDelayMiddleware')

        self.settings.set('DOWNLOAD_DELAY', 0)

        middleware = DownloadDelayMiddleware.create_instance(self.crawler)

        self.assertEqual(middleware.default_delay, 0)


if __name__ == '__main__':
    unittest.main()
