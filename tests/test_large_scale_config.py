#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模配置工具测试
测试 LargeScaleConfig, apply_large_scale_config
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.large_scale_config import LargeScaleConfig, apply_large_scale_config


class TestLargeScaleConfig(unittest.TestCase):
    """大规模配置工具测试"""

    def test_conservative_config(self):
        """测试保守配置"""
        config = LargeScaleConfig.conservative_config(concurrency=8)
        
        # 验证基本配置
        self.assertEqual(config['CONCURRENCY'], 8)
        self.assertEqual(config['SCHEDULER_MAX_QUEUE_SIZE'], 80)  # 8 * 10
        self.assertEqual(config['DOWNLOAD_DELAY'], 0.2)
        self.assertEqual(config['MAX_RUNNING_SPIDERS'], 1)
        
        # 验证连接池配置
        self.assertEqual(config['CONNECTION_POOL_LIMIT'], 16)  # 8 * 2
        
        # 验证重试配置
        self.assertEqual(config['MAX_RETRY_TIMES'], 2)
        
    def test_balanced_config(self):
        """测试平衡配置"""
        config = LargeScaleConfig.balanced_config(concurrency=16)
        
        # 验证基本配置
        self.assertEqual(config['CONCURRENCY'], 16)
        self.assertEqual(config['SCHEDULER_MAX_QUEUE_SIZE'], 240)  # 16 * 15
        self.assertEqual(config['DOWNLOAD_DELAY'], 0.1)
        self.assertEqual(config['MAX_RUNNING_SPIDERS'], 2)
        
        # 验证连接池配置
        self.assertEqual(config['CONNECTION_POOL_LIMIT'], 48)  # 16 * 3
        
        # 验证重试配置
        self.assertEqual(config['MAX_RETRY_TIMES'], 3)
        
    def test_aggressive_config(self):
        """测试激进配置"""
        config = LargeScaleConfig.aggressive_config(concurrency=32)
        
        # 验证基本配置
        self.assertEqual(config['CONCURRENCY'], 32)
        self.assertEqual(config['SCHEDULER_MAX_QUEUE_SIZE'], 640)  # 32 * 20
        self.assertEqual(config['DOWNLOAD_DELAY'], 0.05)
        self.assertEqual(config['MAX_RUNNING_SPIDERS'], 3)
        
        # 验证连接池配置
        self.assertEqual(config['CONNECTION_POOL_LIMIT'], 128)  # 32 * 4
        
        # 验证重试配置
        self.assertEqual(config['MAX_RETRY_TIMES'], 5)
        
    def test_memory_optimized_config(self):
        """测试内存优化配置"""
        config = LargeScaleConfig.memory_optimized_config(concurrency=12)
        
        # 验证基本配置
        self.assertEqual(config['CONCURRENCY'], 12)
        self.assertEqual(config['SCHEDULER_MAX_QUEUE_SIZE'], 60)  # 12 * 5
        self.assertEqual(config['DOWNLOAD_DELAY'], 0.1)
        self.assertEqual(config['MAX_RUNNING_SPIDERS'], 1)
        
        # 验证连接池配置
        self.assertEqual(config['CONNECTION_POOL_LIMIT'], 12)  # 12 * 1
        
        # 验证内存限制配置
        self.assertEqual(config['DOWNLOAD_MAXSIZE'], 2 * 1024 * 1024)  # 2MB
        self.assertEqual(config['DOWNLOAD_WARN_SIZE'], 512 * 1024)  # 512KB
        
        # 验证重试配置
        self.assertEqual(config['MAX_RETRY_TIMES'], 2)
        
    def test_apply_large_scale_config(self):
        """测试应用大规模配置"""
        settings_dict = {}
        
        # 应用平衡配置
        apply_large_scale_config(settings_dict, "balanced", 16)
        
        # 验证配置已应用
        self.assertEqual(settings_dict['CONCURRENCY'], 16)
        self.assertEqual(settings_dict['SCHEDULER_MAX_QUEUE_SIZE'], 240)
        self.assertEqual(settings_dict['DOWNLOAD_DELAY'], 0.1)
        
    def test_apply_large_scale_config_invalid_type(self):
        """测试应用无效的大规模配置类型"""
        settings_dict = {}
        
        # 应用无效配置类型应该抛出异常
        with self.assertRaises(ValueError) as context:
            apply_large_scale_config(settings_dict, "invalid_type", 16)
            
        self.assertIn("不支持的配置类型", str(context.exception))


if __name__ == '__main__':
    unittest.main()