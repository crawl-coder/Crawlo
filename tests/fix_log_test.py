#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试日志配置修复
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import configure_logging as configure, get_logger, LogManager
from crawlo.logging.config import LogConfig


def test_correct_configuration():
    """测试正确的配置方式"""
    print("=== 测试正确的配置方式 ===")
    
    # 1. 使用配置字典（推荐方式）
    print("1. 使用配置字典...")
    LogManager().reset()
    
    config_dict = {
        'level': 'DEBUG',
        'file_path': 'fix_test.log',
        'max_bytes': 2048,
        'backup_count': 2,
        'console_enabled': True,
        'file_enabled': True,
        'encoding': 'utf-8'
    }
    
    config = configure(**config_dict)
    print(f"   配置文件路径: {config.file_path}")
    
    logger = get_logger('test.fix')
    file_handler_found = False
    for handler in logger.handlers:
        if 'FileHandler' in type(handler).__name__:
            file_handler_found = True
            print(f"   文件处理器文件名: {handler.baseFilename}")
    
    print(f"   文件处理器找到: {file_handler_found}")
    logger.info("修复测试消息")
    
    # 2. 使用LogConfig对象
    print("2. 使用LogConfig对象...")
    LogManager().reset()
    
    log_config = LogConfig(
        level='INFO',
        file_path='object_test.log',
        max_bytes=1024,
        backup_count=1,
        console_enabled=True,
        file_enabled=True
    )
    
    config = configure(log_config)
    print(f"   配置文件路径: {config.file_path}")
    
    logger = get_logger('test.object')
    file_handler_found = False
    for handler in logger.handlers:
        if 'FileHandler' in type(handler).__name__:
            file_handler_found = True
            print(f"   文件处理器文件名: {handler.baseFilename}")
    
    print(f"   文件处理器找到: {file_handler_found}")
    logger.info("对象配置测试消息")


def create_settings_class():
    """创建一个模拟的settings类来测试from_settings方法"""
    print("\n=== 测试from_settings方法 ===")
    
    class MockSettings:
        def __init__(self):
            self.LOG_LEVEL = 'DEBUG'
            self.LOG_FILE = 'settings_test.log'
            self.LOG_MAX_BYTES = 1024
            self.LOG_BACKUP_COUNT = 2
            self.LOG_ENCODING = 'utf-8'
            self.LOG_CONSOLE_ENABLED = True
            self.LOG_FILE_ENABLED = True
            self.LOG_LEVELS = {}
    
    # 测试from_settings方法
    settings = MockSettings()
    config = LogConfig.from_settings(settings)
    
    print(f"   从settings创建的配置:")
    print(f"     级别: {config.level}")
    print(f"     文件路径: {config.file_path}")
    print(f"     轮转大小: {config.max_bytes}")
    print(f"     备份数量: {config.backup_count}")
    print(f"     控制台启用: {config.console_enabled}")
    print(f"     文件启用: {config.file_enabled}")
    
    # 应用配置
    LogManager().reset()
    configure(config)
    
    logger = get_logger('test.settings')
    file_handler_found = False
    for handler in logger.handlers:
        if 'FileHandler' in type(handler).__name__:
            file_handler_found = True
            print(f"   文件处理器文件名: {handler.baseFilename}")
    
    print(f"   文件处理器找到: {file_handler_found}")
    logger.info("Settings配置测试消息")


def main():
    """主函数"""
    print("测试日志配置修复...")
    
    try:
        test_correct_configuration()
        create_settings_class()
        
        print("\n=== 修复测试完成 ===")
        print("\n推荐的日志配置方式:")
        print("1. 使用配置字典: configure(level='DEBUG', file_path='test.log', ...)")
        print("2. 使用LogConfig对象: configure(LogConfig(...))")
        print("3. 使用settings对象: configure(settings_object)")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())