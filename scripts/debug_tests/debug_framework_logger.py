#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
调试框架logger配置
"""
import sys
import os
sys.path.insert(0, '/')

from crawlo.initialization import initialize_framework, get_framework_initializer
from crawlo.utils.log import get_logger, LoggerManager
import logging

def debug_framework_logger():
    print("=== 调试框架logger配置 ===")
    
    # 1. 初始化框架，模拟ofweek_standalone的配置
    print("1. 初始化框架...")
    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'logs/debug_framework.log',
        'PROJECT_NAME': 'debug_test',
        'RUN_MODE': 'standalone'
    }
    
    # 确保日志目录存在
    os.makedirs('../logs', exist_ok=True)
    
    settings = initialize_framework(custom_settings)
    print(f"   LOG_LEVEL: {settings.get('LOG_LEVEL')}")
    print(f"   LOG_FILE: {settings.get('LOG_FILE')}")
    
    # 2. 获取框架初始化管理器
    init_manager = get_framework_initializer()
    print(f"   框架是否就绪: {init_manager.is_ready}")
    print(f"   初始化阶段: {init_manager.phase}")
    
    # 3. 测试框架logger
    framework_logger = init_manager.logger
    print(f"   框架logger: {framework_logger}")
    if framework_logger:
        print(f"     名称: {framework_logger.name}")
        print(f"     级别: {framework_logger.level} ({logging.getLevelName(framework_logger.level)})")
        print(f"     处理器数量: {len(framework_logger.handlers)}")
        
        for i, handler in enumerate(framework_logger.handlers):
            handler_type = type(handler).__name__
            handler_level = handler.level
            print(f"       处理器{i}: {handler_type}, 级别: {handler_level} ({logging.getLevelName(handler_level)})")
            if hasattr(handler, 'baseFilename'):
                print(f"         文件: {handler.baseFilename}")
    
    # 4. 手动创建一个crawlo.framework logger对比
    manual_logger = get_logger('crawlo.framework')
    print(f"   手动创建的logger: {manual_logger}")
    if manual_logger:
        print(f"     名称: {manual_logger.name}")
        print(f"     级别: {manual_logger.level} ({logging.getLevelName(manual_logger.level)})")
        print(f"     处理器数量: {len(manual_logger.handlers)}")
        
        for i, handler in enumerate(manual_logger.handlers):
            handler_type = type(handler).__name__
            handler_level = handler.level
            print(f"       处理器{i}: {handler_type}, 级别: {handler_level} ({logging.getLevelName(handler_level)})")
            if hasattr(handler, 'baseFilename'):
                print(f"         文件: {handler.baseFilename}")
    
    # 5. 测试日志输出
    print("2. 测试日志输出...")
    
    if framework_logger:
        framework_logger.info("这是框架logger测试消息 - INFO级别")
        framework_logger.debug("这是框架logger测试消息 - DEBUG级别")
    
    if manual_logger:
        manual_logger.info("这是手动logger测试消息 - INFO级别")
        manual_logger.debug("这是手动logger测试消息 - DEBUG级别")
    
    # 6. 检查是否同一个实例
    print(f"3. 是否同一实例: {framework_logger is manual_logger}")
    
    print("=== 调试完成 ===")

if __name__ == "__main__":
    debug_framework_logger()