#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
调试日志级别配置脚本
"""
import sys
import os
sys.path.insert(0, '/')

from crawlo.initialization import initialize_framework
from crawlo.utils.log import LoggerManager, get_logger
import logging

def main():
    print("=== 开始调试日志级别配置 ===")
    
    # 初始化框架
    print("1. 初始化框架...")
    settings = initialize_framework()
    
    # 打印配置信息
    print(f"2. 配置信息:")
    print(f"   LOG_LEVEL: {settings.get('LOG_LEVEL')}")
    print(f"   LOG_FILE: {settings.get('LOG_FILE')}")
    print(f"   LoggerManager._default_level: {LoggerManager._default_level}")
    print(f"   LoggerManager._default_console_level: {LoggerManager._default_console_level}")
    print(f"   LoggerManager._default_file_level: {LoggerManager._default_file_level}")
    
    # 测试不同组件的日志级别
    components = [
        'crawlo.framework',
        'crawlo.crawler', 
        'QueueManager',
        'Scheduler',
        'AioHttpDownloader',
        'MiddlewareManager',
        'PipelineManager',
        'ExtensionManager',
        'of_week_standalone'
    ]
    
    print("3. 组件日志级别测试:")
    for component_name in components:
        logger = get_logger(component_name)
        print(f"   {component_name}:")
        print(f"     logger.level: {logger.level} ({logging.getLevelName(logger.level)})")
        
        for handler in logger.handlers:
            handler_type = type(handler).__name__
            print(f"     {handler_type}.level: {handler.level} ({logging.getLevelName(handler.level)})")
    
    # 实际测试日志输出
    print("4. 测试日志输出:")
    test_logger = get_logger('TestLogger')
    
    print("   控制台应该看到以下日志:")
    test_logger.debug("这是DEBUG级别日志 - 控制台应该看不到")
    test_logger.info("这是INFO级别日志 - 控制台应该能看到")
    test_logger.warning("这是WARNING级别日志 - 控制台应该能看到")
    
    print("=== 调试完成 ===")

if __name__ == '__main__':
    main()