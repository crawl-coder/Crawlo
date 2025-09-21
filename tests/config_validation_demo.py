#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证演示脚本
演示 Crawlo 框架的配置验证功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config_validator import validate_config


def demo_valid_config():
    """演示有效配置"""
    print("✅ 演示有效配置...")
    
    # 有效的单机模式配置
    valid_config = {
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
    
    is_valid, errors, warnings = validate_config(valid_config)
    
    if is_valid:
        print("   配置验证通过！")
        if warnings:
            print("   警告信息:")
            for warning in warnings:
                print(f"     - {warning}")
    else:
        print("   配置验证失败:")
        for error in errors:
            print(f"     - {error}")
    
    print()


def demo_invalid_config():
    """演示无效配置"""
    print("❌ 演示无效配置...")
    
    # 无效的配置（缺少必需项）
    invalid_config = {
        'PROJECT_NAME': '',  # 项目名称不能为空
        'QUEUE_TYPE': 'invalid_type',  # 无效的队列类型
        'CONCURRENCY': -1,  # 并发数不能为负数
        'DOWNLOAD_DELAY': 'not_a_number',  # 延迟必须是数字
        'LOG_LEVEL': 'INVALID_LEVEL',  # 无效的日志级别
        'MIDDLEWARES': 'not_a_list',  # 中间件必须是列表
        'PIPELINES': ['invalid.pipeline.Class'],  # 无效的管道类名
    }
    
    is_valid, errors, warnings = validate_config(invalid_config)
    
    if is_valid:
        print("   配置验证意外通过！")
    else:
        print("   配置验证正确失败:")
        for error in errors:
            print(f"     - {error}")
    
    if warnings:
        print("   警告信息:")
        for warning in warnings:
            print(f"     - {warning}")
    
    print()


def demo_distributed_config():
    """演示分布式配置"""
    print("🌐 演示分布式配置...")
    
    # 有效的分布式模式配置
    distributed_config = {
        'PROJECT_NAME': 'distributed_test',
        'QUEUE_TYPE': 'redis',
        'CONCURRENCY': 16,
        'DOWNLOAD_DELAY': 0.5,
        'LOG_LEVEL': 'INFO',
        'REDIS_HOST': '127.0.0.1',
        'REDIS_PORT': 6379,
        'REDIS_PASSWORD': '',
        'SCHEDULER_QUEUE_NAME': 'crawlo:distributed_test:queue:requests',  # 添加队列名称
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
    
    is_valid, errors, warnings = validate_config(distributed_config)
    
    if is_valid:
        print("   分布式配置验证通过！")
        if warnings:
            print("   警告信息:")
            for warning in warnings:
                print(f"     - {warning}")
    else:
        print("   分布式配置验证失败:")
        for error in errors:
            print(f"     - {error}")
    
    print()


def main():
    """主函数"""
    print("🚀 开始配置验证演示...")
    print("=" * 50)
    
    demo_valid_config()
    demo_invalid_config()
    demo_distributed_config()
    
    print("=" * 50)
    print("配置验证演示完成！")


if __name__ == "__main__":
    main()