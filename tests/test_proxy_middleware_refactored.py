#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
ProxyMiddleware 重构测试文件
用于测试重构后的代理中间件功能，特别是修复的重复逻辑
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.proxy import ProxyMiddleware, Proxy
from crawlo.exceptions import NotConfiguredError
from crawlo.settings.setting_manager import SettingManager


class TestProxyMiddlewareRefactored(unittest.TestCase):
    """ProxyMiddleware 重构测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()
        
        # 创建爬虫模拟对象
        self.crawler = Mock()
        self.crawler.settings = self.settings

    def test_parse_proxy_data_with_string(self):
        """测试解析字符串代理数据"""
        middleware = ProxyMiddleware(
            settings=self.settings,
            log_level='INFO'
        )
        
        # 测试有效的HTTP代理URL
        result = middleware._parse_proxy_data("http://proxy.example.com:8080")
        self.assertEqual(result, ["http://proxy.example.com:8080"])
        
        # 测试有效的HTTPS代理URL
        result = middleware._parse_proxy_data("https://proxy.example.com:8080")
        self.assertEqual(result, ["https://proxy.example.com:8080"])
        
        # 测试无效的代理URL
        result = middleware._parse_proxy_data("invalid-proxy")
        self.assertEqual(result, [])

    def test_parse_proxy_data_with_dict(self):
        """测试解析字典代理数据"""
        middleware = ProxyMiddleware(
            settings=self.settings,
            log_level='INFO'
        )
        
        # 测试包含字符串代理的字典
        proxy_data = {
            "proxy": "http://proxy1.example.com:8080"
        }
        result = middleware._parse_proxy_data(proxy_data)
        self.assertEqual(result, ["http://proxy1.example.com:8080"])
        
        # 测试包含列表代理的字典
        proxy_data = {
            "proxies": [
                "http://proxy1.example.com:8080",
                "https://proxy2.example.com:8080"
            ]
        }
        result = middleware._parse_proxy_data(proxy_data)
        self.assertEqual(result, [
            "http://proxy1.example.com:8080",
            "https://proxy2.example.com:8080"
        ])
        
        # 测试混合数据
        proxy_data = {
            "proxy": "http://proxy1.example.com:8080",
            "proxies": [
                "https://proxy2.example.com:8080",
                "invalid-proxy"
            ]
        }
        result = middleware._parse_proxy_data(proxy_data)
        self.assertEqual(result, [
            "http://proxy1.example.com:8080",
            "https://proxy2.example.com:8080"
        ])

    def test_get_healthy_proxies(self):
        """测试获取健康代理"""
        middleware = ProxyMiddleware(
            settings=self.settings,
            log_level='INFO'
        )
        
        # 创建测试代理
        proxy1 = Proxy("http://proxy1.example.com:8080")
        proxy2 = Proxy("http://proxy2.example.com:8080")
        proxy3 = Proxy("http://proxy3.example.com:8080")
        
        # 设置代理池
        middleware._proxy_pool = [proxy1, proxy2, proxy3]
        
        # 所有代理都是健康的
        healthy_proxies = middleware._get_healthy_proxies()
        self.assertEqual(len(healthy_proxies), 3)
        
        # 标记一个代理为不健康
        proxy2.is_healthy = False
        healthy_proxies = middleware._get_healthy_proxies()
        self.assertEqual(len(healthy_proxies), 2)
        self.assertIn(proxy1, healthy_proxies)
        self.assertNotIn(proxy2, healthy_proxies)
        self.assertIn(proxy3, healthy_proxies)
        
        # 标记一个代理成功率低于阈值
        proxy3.mark_failure()
        proxy3.mark_failure()
        proxy3.mark_failure()
        proxy3.mark_failure()  # 4次失败，0次成功，成功率=0 < 0.5(默认阈值)
        healthy_proxies = middleware._get_healthy_proxies()
        self.assertEqual(len(healthy_proxies), 1)
        self.assertIn(proxy1, healthy_proxies)
        self.assertNotIn(proxy3, healthy_proxies)

    @patch('crawlo.utils.log.get_logger')
    def test_update_proxy_pool_with_parsed_data(self, mock_get_logger):
        """测试使用解析后的代理数据更新代理池"""
        # 不再需要 PROXY_ENABLED，只要配置了 PROXY_API_URL 就会启用
        self.settings.set('PROXY_API_URL', 'http://proxy-api.example.com')
        self.settings.set('LOG_LEVEL', 'INFO')
        
        mock_get_logger.return_value = Mock()
        
        middleware = ProxyMiddleware.create_instance(self.crawler)
        
        # 测试解析字符串代理数据
        new_proxies = middleware._parse_proxy_data("http://proxy1.example.com:8080")
        self.assertEqual(new_proxies, ["http://proxy1.example.com:8080"])
        
        # 测试解析字典代理数据
        proxy_data = {
            "proxies": [
                "http://proxy1.example.com:8080",
                "https://proxy2.example.com:8080",
                "http://proxy3.example.com:8080"
            ]
        }
        new_proxies = middleware._parse_proxy_data(proxy_data)
        self.assertEqual(new_proxies, [
            "http://proxy1.example.com:8080",
            "https://proxy2.example.com:8080",
            "http://proxy3.example.com:8080"
        ])

    def test_get_healthy_proxy_with_refactored_logic(self):
        """测试使用重构后的逻辑获取健康代理"""
        middleware = ProxyMiddleware(
            settings=self.settings,
            log_level='INFO'
        )
        
        # 创建测试代理
        proxy1 = Proxy("http://proxy1.example.com:8080")
        proxy2 = Proxy("http://proxy2.example.com:8080")
        
        # 设置代理池
        middleware._proxy_pool = [proxy1, proxy2]
        middleware._current_proxy_index = 0
        
        # 获取第一个健康代理（由于轮询逻辑，第一次调用会得到索引1的代理）
        healthy_proxy = asyncio.run(middleware._get_healthy_proxy())
        self.assertEqual(healthy_proxy.proxy_str, proxy2.proxy_str)
        
        # 获取第二个健康代理（轮询回到索引0）
        healthy_proxy = asyncio.run(middleware._get_healthy_proxy())
        self.assertEqual(healthy_proxy.proxy_str, proxy1.proxy_str)
        
        # 再次获取第一个健康代理（轮询到索引1）
        healthy_proxy = asyncio.run(middleware._get_healthy_proxy())
        self.assertEqual(healthy_proxy.proxy_str, proxy2.proxy_str)

    def test_proxy_middleware_initialization(self):
        """测试代理中间件初始化"""
        # 不再需要 PROXY_ENABLED，只要配置了 PROXY_API_URL 就会启用
        self.settings.set('PROXY_API_URL', 'http://test-proxy-api.com')
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertIsInstance(middleware, ProxyMiddleware)
        self.assertTrue(middleware.enabled)
        self.assertEqual(middleware.api_url, 'http://test-proxy-api.com')

    def test_proxy_middleware_enabled_with_api_url(self):
        """测试配置了代理API URL时中间件启用"""
        # 不再需要 PROXY_ENABLED，只要配置了 PROXY_API_URL 就会启用
        self.settings.set('PROXY_API_URL', 'http://test-proxy-api.com')
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertTrue(middleware.enabled)
        self.assertEqual(middleware.api_url, 'http://test-proxy-api.com')

    def test_proxy_middleware_disabled_without_api_url(self):
        """测试未配置代理API URL时中间件禁用"""
        # 不再需要 PROXY_ENABLED，只要不配置 PROXY_API_URL 就会禁用
        self.settings.set('PROXY_API_URL', None)
        middleware = ProxyMiddleware(self.settings, "DEBUG")
        self.assertFalse(middleware.enabled)

if __name__ == '__main__':
    unittest.main()