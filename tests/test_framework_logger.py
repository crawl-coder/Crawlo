#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试框架日志系统
"""
import sys
import os
sys.path.insert(0, '/')

from crawlo.core.framework_initializer import initialize_framework, get_framework_initializer
from crawlo.utils.log import get_logger, LoggerManager

def test_framework_logger():
    print("=== 测试框架日志系统 ===")
    
    # 1. 初始化框架，传入基本配置
    print("1. 初始化框架...")
    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'test_framework.log',
        'PROJECT_NAME': 'test_framework',
        'RUN_MODE': 'standalone'
    }
    settings = initialize_framework(custom_settings)
    print(f"   LOG_LEVEL: {settings.get('LOG_LEVEL')}")
    print(f"   LOG_FILE: {settings.get('LOG_FILE')}")
    
    # 2. 获取框架初始化管理器
    init_manager = get_framework_initializer()
    print(f"   框架是否就绪: {init_manager.is_ready}")
    print(f"   初始化阶段: {init_manager.phase}")
    
    # 3. 测试框架logger
    framework_logger = init_manager.logger
    if framework_logger:
        print(f"   框架logger名称: {framework_logger.name}")
        print(f"   框架logger级别: {framework_logger.level}")
        print(f"   框架logger处理器数量: {len(framework_logger.handlers)}")
        
        for i, handler in enumerate(framework_logger.handlers):
            handler_type = type(handler).__name__
            print(f"     处理器{i}: {handler_type}, 级别: {handler.level}")
    else:
        print("   框架logger为None!")
        framework_logger = get_logger('crawlo.framework')
        print(f"   手动创建的框架logger: {framework_logger.name}")
    
    # 4. 测试日志输出
    print("2. 测试日志输出...")
    framework_logger.info("Crawlo框架初始化完成")
    framework_logger.info("Crawlo Framework Started 1.3.3")
    framework_logger.info("使用单机模式 - 简单快速，适合开发和中小规模爬取")
    framework_logger.info("Run Mode: standalone")
    framework_logger.info("Starting running test_spider")
    
    # 5. 测试其他logger
    print("3. 测试其他组件logger...")
    queue_logger = get_logger('QueueManager')
    queue_logger.info("Queue initialized successfully Type: memory")
    
    scheduler_logger = get_logger('Scheduler')
    scheduler_logger.info("enabled filters: crawlo.filters.memory_filter.MemoryFilter")
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_framework_logger()