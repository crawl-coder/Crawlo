#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量配置工具测试
"""
import os
import sys
import unittest
from unittest.mock import patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.env_config import EnvConfigManager, get_env_var, get_redis_config, get_runtime_config


class TestEnvConfigManager(unittest.TestCase):
    """环境变量配置管理器测试"""

    def test_get_env_var_str(self):
        """测试字符串环境变量获取"""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            result = EnvConfigManager.get_env_var('TEST_VAR', 'default', str)
            self.assertEqual(result, 'test_value')
        
        # 测试默认值
        result = EnvConfigManager.get_env_var('NON_EXISTENT_VAR', 'default', str)
        self.assertEqual(result, 'default')

    def test_get_env_var_int(self):
        """测试整数环境变量获取"""
        with patch.dict(os.environ, {'TEST_INT': '42'}):
            result = EnvConfigManager.get_env_var('TEST_INT', 0, int)
            self.assertEqual(result, 42)
        
        # 测试默认值
        result = EnvConfigManager.get_env_var('NON_EXISTENT_VAR', 10, int)
        self.assertEqual(result, 10)
        
        # 测试无效值
        with patch.dict(os.environ, {'INVALID_INT': 'not_a_number'}):
            result = EnvConfigManager.get_env_var('INVALID_INT', 5, int)
            self.assertEqual(result, 5)

    def test_get_env_var_float(self):
        """测试浮点数环境变量获取"""
        with patch.dict(os.environ, {'TEST_FLOAT': '3.14'}):
            result = EnvConfigManager.get_env_var('TEST_FLOAT', 0.0, float)
            self.assertEqual(result, 3.14)
        
        # 测试默认值
        result = EnvConfigManager.get_env_var('NON_EXISTENT_VAR', 2.5, float)
        self.assertEqual(result, 2.5)

    def test_get_env_var_bool(self):
        """测试布尔环境变量获取"""
        # 测试 True 值
        for true_val in ['1', 'true', 'True', 'TRUE', 'yes', 'on']:
            with patch.dict(os.environ, {'TEST_BOOL': true_val}):
                result = EnvConfigManager.get_env_var('TEST_BOOL', False, bool)
                self.assertTrue(result)
        
        # 测试 False 值
        for false_val in ['0', 'false', 'False', 'FALSE', 'no', 'off', '']:
            with patch.dict(os.environ, {'TEST_BOOL': false_val}):
                result = EnvConfigManager.get_env_var('TEST_BOOL', True, bool)
                self.assertFalse(result)
        
        # 测试默认值
        result = EnvConfigManager.get_env_var('NON_EXISTENT_VAR', True, bool)
        self.assertTrue(result)

    def test_get_redis_config(self):
        """测试 Redis 配置获取"""
        with patch.dict(os.environ, {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6380',
            'REDIS_PASSWORD': 'secret',
            'REDIS_DB': '1'
        }):
            config = get_redis_config()
            self.assertEqual(config['REDIS_HOST'], 'localhost')
            self.assertEqual(config['REDIS_PORT'], 6380)
            self.assertEqual(config['REDIS_PASSWORD'], 'secret')
            self.assertEqual(config['REDIS_DB'], 1)
        
        # 测试默认值
        with patch.dict(os.environ, {}):
            config = get_redis_config()
            self.assertEqual(config['REDIS_HOST'], '127.0.0.1')
            self.assertEqual(config['REDIS_PORT'], 6379)
            self.assertEqual(config['REDIS_PASSWORD'], '')
            self.assertEqual(config['REDIS_DB'], 0)

    def test_get_runtime_config(self):
        """测试运行时配置获取"""
        with patch.dict(os.environ, {
            'CRAWLO_MODE': 'distributed',
            'PROJECT_NAME': 'test_project',
            'CONCURRENCY': '20'
        }):
            config = get_runtime_config()
            self.assertEqual(config['CRAWLO_MODE'], 'distributed')
            self.assertEqual(config['PROJECT_NAME'], 'test_project')
            self.assertEqual(config['CONCURRENCY'], 20)
        
        # 测试默认值
        with patch.dict(os.environ, {}):
            config = get_runtime_config()
            self.assertEqual(config['CRAWLO_MODE'], 'standalone')
            self.assertEqual(config['PROJECT_NAME'], 'crawlo')
            self.assertEqual(config['CONCURRENCY'], 8)

    def test_convenience_functions(self):
        """测试便捷函数"""
        with patch.dict(os.environ, {'TEST_CONVENIENCE': 'convenience_value'}):
            result = get_env_var('TEST_CONVENIENCE', 'default')
            self.assertEqual(result, 'convenience_value')


if __name__ == '__main__':
    unittest.main()