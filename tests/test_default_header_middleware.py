#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 测试文件
用于测试默认请求头中间件的功能，包括随机更换header功能
"""

import unittest
from unittest.mock import Mock, patch

from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.exceptions import NotConfiguredError


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

    def isEnabledFor(self, level):
        return True


class TestDefaultHeaderMiddleware(unittest.TestCase):
    """DefaultHeaderMiddleware 测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建设置管理器
        self.settings = SettingManager()

    def test_middleware_initialization_without_config(self):
        """测试没有配置时中间件初始化"""
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            # 应该抛出NotConfiguredError异常
            with self.assertRaises(NotConfiguredError) as context:
                DefaultHeaderMiddleware.create_instance(crawler)
            
            self.assertIn("未配置DEFAULT_REQUEST_HEADERS、USER_AGENT或随机头部配置，DefaultHeaderMiddleware已禁用", str(context.exception))

    def test_middleware_initialization_with_default_headers(self):
        """测试使用默认请求头配置时中间件初始化"""
        # 设置默认请求头
        self.settings.set('DEFAULT_REQUEST_HEADERS', {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
        })
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            # 应该正常创建实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            self.assertIsInstance(middleware, DefaultHeaderMiddleware)
            self.assertEqual(len(middleware.headers), 3)
            self.assertIn('Accept', middleware.headers)
            self.assertIn('Accept-Language', middleware.headers)
            self.assertIn('Accept-Encoding', middleware.headers)

    def test_middleware_initialization_with_user_agent(self):
        """测试使用User-Agent配置时中间件初始化"""
        # 设置User-Agent
        self.settings.set('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            # 应该正常创建实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            self.assertIsInstance(middleware, DefaultHeaderMiddleware)
            self.assertIn('User-Agent', middleware.headers)
            self.assertEqual(middleware.headers['User-Agent'], 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    def test_middleware_initialization_with_random_user_agent_enabled(self):
        """测试启用随机User-Agent时中间件初始化"""
        # 启用随机User-Agent并提供一个User-Agent
        self.settings.set('RANDOM_USER_AGENT_ENABLED', True)
        self.settings.set('USER_AGENTS', ['Test-Agent/1.0'])  # 提供一个User-Agent以通过初始化检查
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            # 应该正常创建实例，使用内置User-Agent列表
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            self.assertIsInstance(middleware, DefaultHeaderMiddleware)
            self.assertTrue(middleware.random_user_agent_enabled)
            # 注意：这里user_agents会被get_user_agents覆盖，所以长度可能不为1

    def test_middleware_initialization_with_custom_user_agents(self):
        """测试使用自定义User-Agent列表时中间件初始化"""
        # 设置自定义User-Agent列表
        custom_user_agents = [
            'Custom-Agent/1.0',
            'Custom-Agent/2.0',
            'Custom-Agent/3.0'
        ]
        self.settings.set('RANDOM_USER_AGENT_ENABLED', True)
        self.settings.set('USER_AGENTS', custom_user_agents)
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            # 应该正常创建实例，使用自定义User-Agent列表
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            self.assertIsInstance(middleware, DefaultHeaderMiddleware)
            self.assertTrue(middleware.random_user_agent_enabled)
            self.assertEqual(middleware.user_agents, custom_user_agents)

    def test_process_request_with_default_headers(self):
        """测试处理请求时添加默认请求头"""
        # 设置默认请求头
        self.settings.set('DEFAULT_REQUEST_HEADERS', {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            # 创建请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'
            
            spider = Mock()
            
            # 处理请求
            middleware.process_request(request, spider)
            
            # 检查默认请求头是否添加
            self.assertIn('Accept', request.headers)
            self.assertIn('Accept-Language', request.headers)
            self.assertEqual(request.headers['Accept'], 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
            self.assertEqual(request.headers['Accept-Language'], 'en-US,en;q=0.5')

    def test_process_request_with_existing_headers(self):
        """测试处理已有请求头的请求"""
        # 设置默认请求头
        self.settings.set('DEFAULT_REQUEST_HEADERS', {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            # 创建已有请求头的请求
            request = Mock()
            request.headers = {
                'Accept': 'application/json',  # 已存在的请求头
            }
            request.url = 'https://example.com'
            
            spider = Mock()
            
            # 处理请求
            middleware.process_request(request, spider)
            
            # 检查已存在的请求头不被覆盖，新请求头被添加
            self.assertEqual(request.headers['Accept'], 'application/json')  # 保持原值
            self.assertIn('Accept-Language', request.headers)  # 新添加的请求头

    def test_process_request_with_random_user_agent(self):
        """测试处理请求时添加随机User-Agent"""
        # 启用随机User-Agent并设置自定义列表
        custom_user_agents = [
            'Custom-Agent/1.0',
            'Custom-Agent/2.0',
            'Custom-Agent/3.0'
        ]
        self.settings.set('RANDOM_USER_AGENT_ENABLED', True)
        self.settings.set('USER_AGENTS', custom_user_agents)
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            # 创建没有User-Agent的请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'
            
            spider = Mock()
            
            # 处理请求
            middleware.process_request(request, spider)
            
            # 检查随机User-Agent是否添加
            self.assertIn('User-Agent', request.headers)
            self.assertIn(request.headers['User-Agent'], custom_user_agents)

    def test_process_request_with_existing_user_agent(self):
        """测试处理已有User-Agent的请求"""
        # 启用随机User-Agent并设置自定义列表
        custom_user_agents = [
            'Custom-Agent/1.0',
            'Custom-Agent/2.0',
            'Custom-Agent/3.0'
        ]
        self.settings.set('RANDOM_USER_AGENT_ENABLED', True)
        self.settings.set('USER_AGENTS', custom_user_agents)
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            # 创建已有User-Agent的请求
            existing_ua = 'Existing-Agent/1.0'
            request = Mock()
            request.headers = {
                'User-Agent': existing_ua,
            }
            request.url = 'https://example.com'
            
            spider = Mock()
            
            # 处理请求
            middleware.process_request(request, spider)
            
            # 检查已存在的User-Agent不被覆盖
            self.assertEqual(request.headers['User-Agent'], existing_ua)

    def test_get_random_user_agent(self):
        """测试获取随机User-Agent功能"""
        # 设置自定义User-Agent列表
        custom_user_agents = [
            'Custom-Agent/1.0',
            'Custom-Agent/2.0',
            'Custom-Agent/3.0'
        ]
        self.settings.set('RANDOM_USER_AGENT_ENABLED', True)
        self.settings.set('USER_AGENTS', custom_user_agents)
        self.settings.set('LOG_LEVEL', 'DEBUG')
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = self.settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            # 获取随机User-Agent
            random_ua = middleware._get_random_user_agent()
            
            # 检查返回的User-Agent在列表中
            self.assertIn(random_ua, custom_user_agents)


if __name__ == '__main__':
    unittest.main()