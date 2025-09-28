#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
调试日志配置问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import configure_logging as configure, get_logger, LogManager
from crawlo.logging.config import LogConfig


def debug_log_configuration():
    """调试日志配置"""
    print("=== 调试日志配置 ===")
    
    # 重置配置
    LogManager().reset()
    
    # 1. 检查初始状态
    print("1. 检查初始状态...")
    print(f"   初始配置状态: {LogManager().is_configured}")
    if LogManager().config:
        print(f"   初始配置: {LogManager().config}")
    
    # 2. 配置日志系统
    print("2. 配置日志系统...")
    config = configure(
        LOG_LEVEL='DEBUG',
        LOG_FILE='debug_test.log',
        LOG_MAX_BYTES=1024,
        LOG_BACKUP_COUNT=2,
        LOG_CONSOLE_ENABLED=True,
        LOG_FILE_ENABLED=True
    )
    
    print(f"   配置返回值: {config}")
    print(f"   配置类型: {type(config)}")
    print(f"   配置级别: {config.level}")
    print(f"   配置文件路径: {config.file_path}")
    print(f"   轮转大小: {config.max_bytes}")
    print(f"   备份数量: {config.backup_count}")
    print(f"   控制台启用: {config.console_enabled}")
    print(f"   文件启用: {config.file_enabled}")
    
    # 3. 检查管理器状态
    print("3. 检查管理器状态...")
    manager = LogManager()
    print(f"   管理器配置状态: {manager.is_configured}")
    if manager.config:
        print(f"   管理器配置: {manager.config}")
        print(f"   管理器配置文件路径: {manager.config.file_path}")
    
    # 4. 测试Logger创建
    print("4. 测试Logger创建...")
    logger = get_logger('test.debug')
    print(f"   Logger handlers数量: {len(logger.handlers)}")
    
    for i, handler in enumerate(logger.handlers):
        handler_type = type(handler).__name__
        print(f"     Handler {i}: {handler_type}")
        if hasattr(handler, 'baseFilename'):
            print(f"       文件名: {handler.baseFilename}")
    
    # 5. 测试日志输出
    print("5. 测试日志输出...")
    logger.info("调试测试消息")


def test_config_from_dict():
    """测试从字典创建配置"""
    print("\n=== 测试从字典创建配置 ===")
    
    LogManager().reset()
    
    # 使用字典配置
    config_dict = {
        'level': 'DEBUG',
        'file_path': 'dict_test.log',
        'max_bytes': 1024,
        'backup_count': 2,
        'console_enabled': True,
        'file_enabled': True
    }
    
    config = LogConfig.from_dict(config_dict)
    print(f"   字典配置: {config}")
    print(f"   验证结果: {config.validate()}")
    
    # 应用配置
    LogManager().configure(config)
    
    logger = get_logger('test.dict')
    print(f"   Logger handlers数量: {len(logger.handlers)}")
    
    for i, handler in enumerate(logger.handlers):
        handler_type = type(handler).__name__
        print(f"     Handler {i}: {handler_type}")


def main():
    """主函数"""
    print("开始调试日志配置问题...")
    
    try:
        debug_log_configuration()
        test_config_from_dict()
        
        print("\n=== 调试完成 ===")
        
    except Exception as e:
        print(f"\n调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())