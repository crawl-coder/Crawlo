#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
详细的日志系统功能测试
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import configure_logging as configure, get_logger, LogManager
from crawlo.logging.config import LogConfig


def test_log_config_creation():
    """测试日志配置创建"""
    print("=== 测试日志配置创建 ===")
    
    # 重置日志管理器
    LogManager().reset()
    
    # 1. 测试通过关键字参数创建配置
    print("1. 测试通过关键字参数创建配置...")
    config = configure(
        LOG_LEVEL='DEBUG',
        LOG_FILE='test.log',
        LOG_MAX_BYTES=1024,
        LOG_BACKUP_COUNT=3
    )
    
    print(f"   配置级别: {config.level}")
    print(f"   配置文件路径: {config.file_path}")
    print(f"   轮转大小: {config.max_bytes}")
    print(f"   备份数量: {config.backup_count}")
    
    # 2. 测试通过字典创建配置
    print("2. 测试通过字典创建配置...")
    LogManager().reset()
    config_dict = {
        'LOG_LEVEL': 'WARNING',
        'LOG_FILE': 'dict_test.log',
        'LOG_CONSOLE_ENABLED': False
    }
    config = configure(**config_dict)
    
    print(f"   配置级别: {config.level}")
    print(f"   配置文件路径: {config.file_path}")
    print(f"   控制台启用: {config.console_enabled}")


def test_logger_factory():
    """测试Logger工厂"""
    print("\n=== 测试Logger工厂 ===")
    
    # 重置并配置
    LogManager().reset()
    configure(LOG_LEVEL='INFO')
    
    # 1. 测试获取Logger
    print("1. 测试获取Logger...")
    logger1 = get_logger('test.factory1')
    logger2 = get_logger('test.factory2')
    logger3 = get_logger('test.factory1')  # 应该是同一个实例
    
    print(f"   Logger1 ID: {id(logger1)}")
    print(f"   Logger2 ID: {id(logger2)}")
    print(f"   Logger3 ID: {id(logger3)}")
    print(f"   Logger1和Logger3是同一对象: {logger1 is logger3}")
    
    # 2. 测试Logger配置
    print("2. 测试Logger配置...")
    print(f"   Logger1名称: {logger1.name}")
    print(f"   Logger1 handlers数量: {len(logger1.handlers)}")
    
    for i, handler in enumerate(logger1.handlers):
        print(f"     Handler {i}: {type(handler).__name__}")


def test_file_and_console_handlers():
    """测试文件和控制台处理器"""
    print("\n=== 测试文件和控制台处理器 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'handler_test.log')
    
    try:
        # 1. 测试文件和控制台都启用
        print("1. 测试文件和控制台都启用...")
        LogManager().reset()
        configure(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_CONSOLE_ENABLED=True,
            LOG_FILE_ENABLED=True
        )
        
        logger = get_logger('test.handlers')
        print(f"   Handlers数量: {len(logger.handlers)}")
        
        has_file_handler = False
        has_console_handler = False
        
        for handler in logger.handlers:
            handler_type = type(handler).__name__
            print(f"     Handler类型: {handler_type}")
            if 'FileHandler' in handler_type:
                has_file_handler = True
                print(f"     文件路径: {getattr(handler, 'baseFilename', 'N/A')}")
            elif 'StreamHandler' in handler_type:
                has_console_handler = True
        
        print(f"   有文件处理器: {has_file_handler}")
        print(f"   有控制台处理器: {has_console_handler}")
        
        # 输出日志
        logger.info("测试文件和控制台处理器")
        
        # 检查文件是否存在
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   文件内容行数: {len(content.splitlines())}")
        else:
            print("   文件不存在!")
            
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_log_levels():
    """测试日志级别"""
    print("\n=== 测试日志级别 ===")
    
    # 1. 测试默认级别
    print("1. 测试默认级别...")
    LogManager().reset()
    configure(LOG_LEVEL='WARNING')
    
    logger = get_logger('test.levels')
    logger.debug("DEBUG消息 - 不应该显示")
    logger.info("INFO消息 - 不应该显示")
    logger.warning("WARNING消息 - 应该显示")
    logger.error("ERROR消息 - 应该显示")
    
    # 2. 测试模块特定级别
    print("2. 测试模块特定级别...")
    LogManager().reset()
    configure(
        LOG_LEVEL='ERROR',
        LOG_LEVELS={
            'test.debug_module': 'DEBUG',
            'test.info_module': 'INFO'
        }
    )
    
    # 默认模块（ERROR级别）
    default_logger = get_logger('test.default')
    default_logger.info("默认模块INFO消息 - 不应该显示")
    default_logger.error("默认模块ERROR消息 - 应该显示")
    
    # DEBUG模块（DEBUG级别）
    debug_logger = get_logger('test.debug_module')
    debug_logger.debug("DEBUG模块DEBUG消息 - 应该显示")
    debug_logger.info("DEBUG模块INFO消息 - 应该显示")
    
    # INFO模块（INFO级别）
    info_logger = get_logger('test.info_module')
    info_logger.debug("INFO模块DEBUG消息 - 不应该显示")
    info_logger.info("INFO模块INFO消息 - 应该显示")


def test_log_config_validation():
    """测试日志配置验证"""
    print("\n=== 测试日志配置验证 ===")
    
    # 1. 测试有效配置
    print("1. 测试有效配置...")
    valid_config = LogConfig(level='INFO', file_path='valid.log')
    is_valid = valid_config.validate()
    print(f"   有效配置验证: {is_valid}")
    
    # 2. 测试无效级别
    print("2. 测试无效级别...")
    invalid_config = LogConfig(level='INVALID', file_path='invalid.log')
    is_valid = invalid_config.validate()
    print(f"   无效级别验证: {is_valid}")
    
    # 3. 测试目录创建
    print("3. 测试目录创建...")
    temp_dir = tempfile.mkdtemp()
    nested_path = os.path.join(temp_dir, 'subdir', 'nested.log')
    
    nested_config = LogConfig(level='INFO', file_path=nested_path)
    is_valid = nested_config.validate()
    print(f"   嵌套目录验证: {is_valid}")
    print(f"   目录存在: {os.path.exists(os.path.dirname(nested_path))}")
    
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主测试函数"""
    print("开始详细测试Crawlo框架日志系统...")
    
    try:
        # 运行所有测试
        test_log_config_creation()
        test_logger_factory()
        test_file_and_console_handlers()
        test_log_levels()
        test_log_config_validation()
        
        print("\n=== 详细测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())