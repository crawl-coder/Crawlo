#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证器测试
测试 Crawlo 框架的配置验证功能
"""

import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config_validator import ConfigValidator


class TestConfigValidator(unittest.TestCase):
    """配置验证器测试类"""

    def setUp(self):
        """测试初始化"""
        self.validator = ConfigValidator()

    def test_valid_standalone_config(self):
        """测试有效的单机模式配置"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'DOWNLOAD_DELAY': 1.0,
            'LOG_LEVEL': 'INFO',
            'MIDDLEWARES': [
                'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
                'crawlo.middleware.download_delay.DownloadDelayMiddleware',
            ],
            'PIPELINES': [
                'crawlo.pipelines.console_pipeline.ConsolePipeline',
            ]
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_valid_distributed_config(self):
        """测试有效的分布式模式配置"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'redis',
            'CONCURRENCY': 16,
            'DOWNLOAD_DELAY': 0.5,
            'LOG_LEVEL': 'INFO',
            'REDIS_HOST': '127.0.0.1',
            'REDIS_PORT': 6379,
            'REDIS_PASSWORD': '',
            'SCHEDULER_QUEUE_NAME': 'crawlo:test_project:queue:requests',
            'MIDDLEWARES': [
                'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
                'crawlo.middleware.download_delay.DownloadDelayMiddleware',
            ],
            'PIPELINES': [
                'crawlo.pipelines.console_pipeline.ConsolePipeline',
                'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
            ],
            'EXTENSIONS': [
                'crawlo.extension.memory_monitor.MemoryMonitorExtension',
            ]
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_invalid_project_name(self):
        """测试无效的项目名称"""
        config = {
            'PROJECT_NAME': '',  # 空项目名称
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INFO'
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("PROJECT_NAME 必须是非空字符串", errors)

    def test_invalid_queue_type(self):
        """测试无效的队列类型"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'invalid_type',  # 无效队列类型
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INFO'
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("QUEUE_TYPE 必须是以下值之一: ['memory', 'redis', 'auto']", errors)

    def test_invalid_concurrency(self):
        """测试无效的并发数"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': -1,  # 负数并发数
            'LOG_LEVEL': 'INFO'
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("CONCURRENCY 必须是正整数", errors)

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

    def test_invalid_middleware_config(self):
        """测试无效的中间件配置"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INFO',
            'MIDDLEWARES': 'not_a_list'  # 不是列表
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("MIDDLEWARES 必须是列表", errors)

    def test_invalid_pipeline_config(self):
        """测试无效的管道配置"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INFO',
            'PIPELINES': 'not_a_list'  # 不是列表
        }
        
        is_valid, errors, warnings = self.validator.validate(config)
        self.assertFalse(is_valid)
        self.assertIn("PIPELINES 必须是列表", errors)

    def test_convenience_function(self):
        """测试便利函数"""
        config = {
            'PROJECT_NAME': 'test_project',
            'QUEUE_TYPE': 'memory',
            'CONCURRENCY': 8,
            'LOG_LEVEL': 'INFO'
        }
        
        from crawlo.config_validator import validate_config
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