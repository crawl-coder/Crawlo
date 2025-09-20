#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证器测试脚本
用于验证配置验证器的功能
"""
import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config_validator import ConfigValidator, validate_config


class TestConfigValidator(unittest.TestCase):
    """配置验证器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.validator = ConfigValidator()
    
    def test_valid_standalone_config(self):
        """测试有效的单机配置"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'DOWNLOAD_DELAY': 1.0,
            'DOWNLOAD_TIMEOUT': 30,
            'CONNECTION_POOL_LIMIT': 50,
            'SCHEDULER_MAX_QUEUE_SIZE': 2000,
            'LOG_LEVEL': 'INFO',
            'MIDDLEWARES': [
                'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
                'crawlo.middleware.download_delay.DownloadDelayMiddleware'
            ],
            'PIPELINES': [
                'crawlo.pipelines.console_pipeline.ConsolePipeline'
            ]
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_valid_distributed_config(self):
        """测试有效的分布式配置"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'redis',
            'CONCURRENCY': 16,
            'DOWNLOAD_DELAY': 1.0,
            'DOWNLOAD_TIMEOUT': 30,
            'CONNECTION_POOL_LIMIT': 50,
            'SCHEDULER_MAX_QUEUE_SIZE': 2000,
            'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
            'REDIS_HOST': '127.0.0.1',
            'REDIS_PORT': 6379,
            'REDIS_URL': 'redis://127.0.0.1:6379/0',
            'LOG_LEVEL': 'INFO',
            'MIDDLEWARES': [
                'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
                'crawlo.middleware.download_delay.DownloadDelayMiddleware'
            ],
            'PIPELINES': [
                'crawlo.pipelines.console_pipeline.ConsolePipeline'
            ]
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_project_name(self):
        """测试无效的项目名称"""
        config = {
            'PROJECT_NAME': '',  # 空字符串
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("PROJECT_NAME 必须是非空字符串", errors)
    
    def test_invalid_concurrency(self):
        """测试无效的并发数"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': -1  # 负数
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("CONCURRENCY 必须是正整数", errors)
    
    def test_invalid_queue_type(self):
        """测试无效的队列类型"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'invalid_type',  # 无效类型
            'CONCURRENCY': 8
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("QUEUE_TYPE 必须是以下值之一: ['memory', 'redis', 'auto']", errors)
    
    def test_invalid_redis_queue_name(self):
        """测试无效的Redis队列名称"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'redis',
            'CONCURRENCY': 8,
            'SCHEDULER_QUEUE_NAME': 'invalid_queue_name'  # 不符合命名规范
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertTrue(is_valid)  # 队列名称错误是警告，不是错误
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("Redis队列名称" in warning for warning in warnings))
    
    def test_missing_redis_queue_name(self):
        """测试缺少Redis队列名称"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'redis',
            'CONCURRENCY': 8
            # 缺少 SCHEDULER_QUEUE_NAME
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("使用Redis队列时，SCHEDULER_QUEUE_NAME 不能为空", errors)
    
    def test_invalid_redis_port(self):
        """测试无效的Redis端口"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'redis',
            'CONCURRENCY': 8,
            'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
            'REDIS_HOST': '127.0.0.1',
            'REDIS_PORT': 99999  # 无效端口
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("REDIS_PORT 必须是1-65535之间的整数", errors)
    
    def test_invalid_log_level(self):
        """测试无效的日志级别"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INVALID_LEVEL'  # 无效日志级别
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("LOG_LEVEL 必须是以下值之一: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']", errors)
    
    def test_convenience_function(self):
        """测试便利函数"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INFO'
        }
        
        is_valid, errors, warnings = validate_config(config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


def main():
    """主测试函数"""
    print("开始配置验证器测试...")
    print("=" * 50)
    
    # 运行测试
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)
    
    print("=" * 50)
    print("配置验证器测试完成")


if __name__ == "__main__":
    main()