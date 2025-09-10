#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
框架环境变量使用测试
验证整个框架中环境变量的正确使用
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.env_config import get_env_var, get_redis_config, get_runtime_config
from crawlo.settings.setting_manager import SettingManager
from crawlo.settings import default_settings
from crawlo.mode_manager import from_env


class TestFrameworkEnvUsage(unittest.TestCase):
    """框架环境变量使用测试"""

    def test_default_settings_env_usage(self):
        """测试 default_settings.py 中的环境变量使用"""
        # 验证 default_settings.py 不直接使用 os.getenv
        import inspect
        import crawlo.settings.default_settings as default_settings_module
        
        source_code = inspect.getsource(default_settings_module)
        # 检查是否还有直接使用 os.getenv 的地方
        self.assertNotIn('os.getenv', source_code, 
                         "default_settings.py 不应该直接使用 os.getenv")
        
        # 但应该使用 env_config 工具
        self.assertIn('get_redis_config', source_code,
                      "default_settings.py 应该使用 get_redis_config")
        self.assertIn('get_runtime_config', source_code,
                      "default_settings.py 应该使用 get_runtime_config")

    def test_env_config_tool(self):
        """测试环境变量配置工具"""
        # 测试获取Redis配置
        with patch.dict(os.environ, {
            'REDIS_HOST': 'test.redis.com',
            'REDIS_PORT': '6380',
            'REDIS_PASSWORD': 'test_pass',
            'REDIS_DB': '2'
        }):
            redis_config = get_redis_config()
            self.assertEqual(redis_config['REDIS_HOST'], 'test.redis.com')
            self.assertEqual(redis_config['REDIS_PORT'], 6380)
            self.assertEqual(redis_config['REDIS_PASSWORD'], 'test_pass')
            self.assertEqual(redis_config['REDIS_DB'], 2)
        
        # 测试获取运行时配置
        with patch.dict(os.environ, {
            'PROJECT_NAME': 'test_project',
            'CRAWLO_MODE': 'distributed',
            'CONCURRENCY': '16'
        }):
            runtime_config = get_runtime_config()
            self.assertEqual(runtime_config['PROJECT_NAME'], 'test_project')
            self.assertEqual(runtime_config['CRAWLO_MODE'], 'distributed')
            self.assertEqual(runtime_config['CONCURRENCY'], 16)

    def test_settings_manager_with_env(self):
        """测试设置管理器与环境变量的集成"""
        # 设置环境变量
        env_vars = {
            'PROJECT_NAME': 'env_test_project',
            'CONCURRENCY': '12',
            'REDIS_HOST': 'env.redis.test',
            'REDIS_PORT': '6381'
        }
        
        with patch.dict(os.environ, env_vars):
            # 重新导入 default_settings 模块以获取最新的环境变量
            import importlib
            import crawlo.settings.default_settings
            importlib.reload(crawlo.settings.default_settings)
            
            # 创建设置管理器
            settings = SettingManager()
            settings.set_settings(crawlo.settings.default_settings)
            
            # 验证环境变量被正确使用
            redis_config = get_redis_config()
            self.assertEqual(settings.get('REDIS_HOST'), redis_config['REDIS_HOST'])
            
            runtime_config = get_runtime_config()
            self.assertEqual(settings.get('PROJECT_NAME'), runtime_config['PROJECT_NAME'])

    def test_mode_manager_env_usage(self):
        """测试 mode_manager.py 中的环境变量使用"""
        # 验证 from_env 函数现在会抛出异常
        with self.assertRaises(RuntimeError) as context:
            from_env()
        
        self.assertIn("环境变量配置已移除", str(context.exception))


if __name__ == '__main__':
    unittest.main()