#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ThrottleMiddleware Simple Configuration Test
Test the backward compatibility with DOWNLOAD_DELAY configuration
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.throttle import ThrottleMiddleware
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
        print(f"[INFO] {msg}")

    def warning(self, msg):
        self.logs.append(('warning', msg))

    def error(self, msg):
        self.logs.append(('error', msg))


class TestThrottleMiddlewareSimpleConfig(unittest.TestCase):
    """Test ThrottleMiddleware simple configuration mode"""

    def setUp(self):
        """Test setup"""
        self.crawler = Mock()
        self.settings = SettingManager()
        self.crawler.settings = self.settings

    @patch('crawlo.middleware.throttle.get_logger')
    def test_simple_download_delay_config(self, mock_get_logger):
        """Test simple DOWNLOAD_DELAY configuration"""
        mock_get_logger.return_value = MockLogger('ThrottleMiddleware')
        
        # Set simple configuration
        self.settings.set('DOWNLOAD_DELAY', 0.5)
        self.settings.set('RANDOMNESS', False)  # Explicitly disable randomness
        
        # Create middleware instance
        middleware = ThrottleMiddleware.create_instance(self.crawler)
        
        # Verify it uses DOWNLOAD_DELAY
        self.assertEqual(middleware.default_delay, 0.5)
        self.assertFalse(middleware.auto_throttle)
        
    @patch('crawlo.middleware.throttle.get_logger')
    def test_download_delay_with_randomness(self, mock_get_logger):
        """Test DOWNLOAD_DELAY with RANDOMNESS enabled"""
        mock_get_logger.return_value = MockLogger('ThrottleMiddleware')
        
        # Set configuration with randomness
        self.settings.set('DOWNLOAD_DELAY', 2.0)
        self.settings.set('RANDOMNESS', True)
        
        # Create middleware instance
        middleware = ThrottleMiddleware.create_instance(self.crawler)
        
        # Verify auto_throttle is enabled when RANDOMNESS=True
        self.assertEqual(middleware.default_delay, 2.0)
        self.assertTrue(middleware.auto_throttle)
        
    @patch('crawlo.middleware.throttle.get_logger')
    def test_throttle_config_overrides_download_delay(self, mock_get_logger):
        """Test DOWNLOAD_DELAY is the unified configuration"""
        mock_get_logger.return_value = MockLogger('ThrottleMiddleware')
        
        # Set DOWNLOAD_DELAY
        self.settings.set('DOWNLOAD_DELAY', 0.5)
        
        # Create middleware instance
        middleware = ThrottleMiddleware.create_instance(self.crawler)
        
        # Should use DOWNLOAD_DELAY
        self.assertEqual(middleware.default_delay, 0.5)
        
    @patch('crawlo.middleware.throttle.get_logger')
    def test_domain_specific_config(self, mock_get_logger):
        """Test domain-specific configuration"""
        mock_get_logger.return_value = MockLogger('ThrottleMiddleware')
        
        # Set advanced configuration
        self.settings.set('DOWNLOAD_DELAY', 1.0)
        self.settings.set('RANDOMNESS', False)
        self.settings.set('THROTTLE_DOMAIN_OVERRIDES', {
            'example.com': {'delay': 2.0},
            'api.example.com': {'delay': 0.1, 'max_rate': 10},
        })
        
        # Create middleware instance
        middleware = ThrottleMiddleware.create_instance(self.crawler)
        
        # Verify domain configs are set
        self.assertEqual(middleware.default_delay, 1.0)
        self.assertIn('example.com', middleware.throttler._domain_configs)
        self.assertIn('api.example.com', middleware.throttler._domain_configs)
        
    @patch('crawlo.middleware.throttle.get_logger')
    def test_disabled_throttle(self, mock_get_logger):
        """Test disabled throttle"""
        mock_get_logger.return_value = MockLogger('ThrottleMiddleware')
        
        # Disable throttle
        self.settings.set('THROTTLE_ENABLED', False)
        
        # Create middleware instance
        middleware = ThrottleMiddleware.create_instance(self.crawler)
        
        # Should return None
        self.assertIsNone(middleware)


if __name__ == '__main__':
    unittest.main()
