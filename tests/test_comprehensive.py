#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试
验证所有改进的集成效果
"""
import sys
import os
import asyncio
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.env_config import get_env_var, get_redis_config, get_runtime_config
from crawlo.utils.error_handler import ErrorHandler, handle_exception
from crawlo.core.engine import Engine
from crawlo.settings.setting_manager import SettingManager
from crawlo.settings import default_settings
from crawlo.queue.queue_manager import QueueManager, QueueConfig, QueueType


class TestComprehensiveIntegration(unittest.TestCase):
    """综合集成测试"""

    def setUp(self):
        """测试前准备"""
        # 设置测试环境变量
        self.test_env = {
            'PROJECT_NAME': 'test_project',
            'CONCURRENCY': '4',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379'
        }
        self.original_env = {}
        for key, value in self.test_env.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value

    def tearDown(self):
        """测试后清理"""
        # 恢复原始环境变量
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_env_config_integration(self):
        """测试环境变量配置集成"""
        # 验证环境变量工具正常工作
        project_name = get_env_var('PROJECT_NAME', 'default', str)
        self.assertEqual(project_name, 'test_project')
        
        concurrency = get_env_var('CONCURRENCY', 1, int)
        self.assertEqual(concurrency, 4)
        
        # 验证Redis配置工具
        redis_config = get_redis_config()
        self.assertEqual(redis_config['REDIS_HOST'], 'localhost')
        self.assertEqual(redis_config['REDIS_PORT'], 6379)

    def test_error_handler_integration(self):
        """测试错误处理集成"""
        # 验证错误处理模块正常工作
        error_handler = ErrorHandler("test")
        
        # 测试错误处理
        try:
            error_handler.handle_error(ValueError("Test error"), raise_error=False)
        except Exception:
            self.fail("Error handler should not raise exception when raise_error=False")
        
        # 测试安全调用
        result = error_handler.safe_call(lambda x: x*2, 5, default_return=0)
        self.assertEqual(result, 10)
        
        # 测试装饰器
        @handle_exception(raise_error=False)
        def failing_function():
            raise RuntimeError("Test")
        
        try:
            failing_function()
        except Exception:
            self.fail("Decorated function should not raise exception")

    def test_settings_integration(self):
        """测试设置管理器集成"""
        # 重新加载默认设置以获取环境变量
        import importlib
        import crawlo.settings.default_settings
        importlib.reload(crawlo.settings.default_settings)
        
        # 创建设置管理器
        settings = SettingManager()
        settings.set_settings(crawlo.settings.default_settings)
        
        # 验证设置正确加载
        self.assertEqual(settings.get('PROJECT_NAME'), 'test_project')
        self.assertEqual(settings.get_int('CONCURRENCY'), 4)
        self.assertEqual(settings.get('REDIS_HOST'), 'localhost')

    def test_queue_manager_config(self):
        """测试队列管理器配置"""
        # 重新加载默认设置
        import importlib
        import crawlo.settings.default_settings
        importlib.reload(crawlo.settings.default_settings)
        
        # 创建设置管理器
        settings = SettingManager()
        settings.set_settings(crawlo.settings.default_settings)
        
        # 从设置创建队列配置
        queue_config = QueueConfig.from_settings(settings)
        
        # 验证配置正确
        self.assertEqual(queue_config.queue_type, QueueType.AUTO)
        self.assertIn('test_project', queue_config.queue_name)

    async def test_async_components(self):
        """测试异步组件"""
        # 测试异步错误处理装饰器
        @handle_exception(raise_error=False)
        async def async_failing_function():
            raise RuntimeError("Async test")
        
        try:
            await async_failing_function()
        except Exception:
            self.fail("Async decorated function should not raise exception")


if __name__ == '__main__':
    # 运行同步测试
    unittest.main(exit=False)
    
    # 运行异步测试
    async def run_async_tests():
        test_instance = TestComprehensiveIntegration()
        test_instance.setUp()
        await test_instance.test_async_components()
        test_instance.tearDown()
    
    asyncio.run(run_async_tests())