#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证演示脚本
演示如何使用配置验证器来验证Crawlo配置
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.config_validator import print_validation_report


def demonstrate_config_validation():
    """演示配置验证功能"""
    print("=== 配置验证功能演示 ===\n")
    
    # 1. 有效的单机配置
    print("1. 有效的单机配置:")
    valid_standalone_config = {
        'PROJECT_NAME': 'demo_project',
        'QUEUE_TYPE': 'memory',
        'CONCURRENCY': 8,
        'DOWNLOAD_DELAY': 1.0,
        'LOG_LEVEL': 'INFO',
        'MIDDLEWARES': [
            'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
            'crawlo.middleware.download_delay.DownloadDelayMiddleware'
        ],
        'PIPELINES': [
            'crawlo.pipelines.console_pipeline.ConsolePipeline'
        ]
    }
    
    print_validation_report(valid_standalone_config)
    print()
    
    # 2. 有效的分布式配置
    print("2. 有效的分布式配置:")
    valid_distributed_config = {
        'PROJECT_NAME': 'demo_project',
        'QUEUE_TYPE': 'redis',
        'CONCURRENCY': 16,
        'DOWNLOAD_DELAY': 1.0,
        'SCHEDULER_QUEUE_NAME': 'crawlo:demo_project:queue:requests',
        'REDIS_HOST': '127.0.0.1',
        'REDIS_PORT': 6379,
        'LOG_LEVEL': 'INFO',
        'MIDDLEWARES': [
            'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
            'crawlo.middleware.download_delay.DownloadDelayMiddleware'
        ],
        'PIPELINES': [
            'crawlo.pipelines.console_pipeline.ConsolePipeline'
        ]
    }
    
    print_validation_report(valid_distributed_config)
    print()
    
    # 3. 无效配置示例
    print("3. 无效配置示例:")
    invalid_config = {
        'PROJECT_NAME': '',  # 空项目名称
        'QUEUE_TYPE': 'invalid_type',  # 无效队列类型
        'CONCURRENCY': -1,  # 负并发数
        'REDIS_PORT': 99999,  # 无效端口
        'LOG_LEVEL': 'INVALID_LEVEL'  # 无效日志级别
    }
    
    print_validation_report(invalid_config)
    print()
    
    # 4. 使用配置工厂创建配置并验证
    print("4. 使用配置工厂创建配置并验证:")
    try:
        # 创建有效的配置
        config = CrawloConfig.standalone(
            concurrency=8,
            download_delay=1.0
        )
        print("✅ 单机模式配置创建成功")
        config.print_summary()
        print()
        
        # 尝试创建无效配置（会抛出异常）
        try:
            invalid_config_dict = {
                'CONCURRENCY': -1  # 负并发数
            }
            invalid_config_obj = CrawloConfig.custom(invalid_config_dict)
        except ValueError as e:
            print(f"✅ 捕获到配置验证异常: {e}")
        
    except Exception as e:
        print(f"❌ 配置创建失败: {e}")


if __name__ == "__main__":
    demonstrate_config_validation()