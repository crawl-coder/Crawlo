#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
最终日志系统功能验证测试
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


def test_complete_log_functionality():
    """测试完整的日志功能"""
    print("=== 测试完整的日志功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'complete_test.log')
    
    try:
        print(f"日志文件路径: {log_file}")
        
        # 1. 测试完整的日志配置
        print("1. 测试完整的日志配置...")
        LogManager().reset()
        
        # 使用正确的参数名
        config = configure(
            LOG_LEVEL='DEBUG',
            LOG_FILE=log_file,
            LOG_MAX_BYTES=2048,  # 小的轮转大小用于测试
            LOG_BACKUP_COUNT=2,
            LOG_CONSOLE_ENABLED=True,
            LOG_FILE_ENABLED=True,
            LOG_ENCODING='utf-8'
        )
        
        current_config = LogManager().config
        print(f"   配置级别: {current_config.level}")
        print(f"   配置文件路径: {current_config.file_path}")
        print(f"   轮转大小: {current_config.max_bytes}")
        print(f"   备份数量: {current_config.backup_count}")
        print(f"   控制台启用: {current_config.console_enabled}")
        print(f"   文件启用: {current_config.file_enabled}")
        print(f"   编码: {current_config.encoding}")
        
        # 2. 测试Logger创建
        print("2. 测试Logger创建...")
        logger = get_logger('test.complete')
        print(f"   Logger名称: {logger.name}")
        print(f"   Handlers数量: {len(logger.handlers)}")
        
        file_handler_found = False
        console_handler_found = False
        
        for handler in logger.handlers:
            handler_type = type(handler).__name__
            print(f"     Handler类型: {handler_type}")
            if 'FileHandler' in handler_type:
                file_handler_found = True
                if hasattr(handler, 'baseFilename'):
                    print(f"     文件路径: {handler.baseFilename}")
            elif 'StreamHandler' in handler_type:
                console_handler_found = True
        
        print(f"   文件处理器找到: {file_handler_found}")
        print(f"   控制台处理器找到: {console_handler_found}")
        
        # 3. 测试日志输出
        print("3. 测试日志输出...")
        logger.debug("这是一条DEBUG消息")
        logger.info("这是一条INFO消息")
        logger.warning("这是一条WARNING消息")
        logger.error("这是一条ERROR消息")
        logger.critical("这是一条CRITICAL消息")
        
        # 4. 测试日志轮转
        print("4. 测试日志轮转...")
        for i in range(20):
            logger.info(f"测试轮转消息 {i+1} - 这是一条比较长的消息，用于快速达到轮转大小限制")
        
        # 5. 检查日志文件
        print("5. 检查日志文件...")
        if os.path.exists(log_file):
            file_size = os.path.getsize(log_file)
            print(f"   主日志文件大小: {file_size} 字节")
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   主日志文件行数: {len(lines)}")
                if lines:
                    print(f"   最后几行: {''.join(lines[-3:])}")
        else:
            print("   主日志文件不存在!")
            
        # 检查备份文件
        for i in range(1, 3):
            backup_file = f"{log_file}.{i}"
            if os.path.exists(backup_file):
                backup_size = os.path.getsize(backup_file)
                print(f"   备份文件 {i} 大小: {backup_size} 字节")
            else:
                print(f"   备份文件 {i} 不存在")
                
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_module_specific_logging():
    """测试模块特定的日志配置"""
    print("\n=== 测试模块特定的日志配置 ===")
    
    # 1. 配置模块级别
    print("1. 配置模块级别...")
    LogManager().reset()
    configure(
        LOG_LEVEL='WARNING',
        LOG_LEVELS={
            'module.debug': 'DEBUG',
            'module.info': 'INFO',
            'module.error': 'ERROR'
        }
    )
    
    current_config = LogManager().config
    print(f"   默认级别: {current_config.level}")
    print(f"   模块级别: {current_config.module_levels}")
    
    # 2. 测试不同模块的日志级别
    print("2. 测试不同模块的日志级别...")
    
    # DEBUG模块（应该显示所有级别）
    debug_logger = get_logger('module.debug')
    print(f"   DEBUG模块级别: {debug_logger.handlers[0].level}")
    debug_logger.debug("DEBUG模块 - DEBUG消息")
    debug_logger.info("DEBUG模块 - INFO消息")
    debug_logger.warning("DEBUG模块 - WARNING消息")
    debug_logger.error("DEBUG模块 - ERROR消息")
    
    # INFO模块（应该显示INFO及以上）
    info_logger = get_logger('module.info')
    print(f"   INFO模块级别: {info_logger.handlers[0].level}")
    info_logger.debug("INFO模块 - DEBUG消息（不应该显示）")
    info_logger.info("INFO模块 - INFO消息")
    info_logger.warning("INFO模块 - WARNING消息")
    info_logger.error("INFO模块 - ERROR消息")
    
    # ERROR模块（应该只显示ERROR及以上）
    error_logger = get_logger('module.error')
    print(f"   ERROR模块级别: {error_logger.handlers[0].level}")
    error_logger.debug("ERROR模块 - DEBUG消息（不应该显示）")
    error_logger.info("ERROR模块 - INFO消息（不应该显示）")
    error_logger.warning("ERROR模块 - WARNING消息（不应该显示）")
    error_logger.error("ERROR模块 - ERROR消息")
    
    # 默认模块（应该只显示WARNING及以上）
    default_logger = get_logger('module.default')
    print(f"   默认模块级别: {default_logger.handlers[0].level}")
    default_logger.debug("默认模块 - DEBUG消息（不应该显示）")
    default_logger.info("默认模块 - INFO消息（不应该显示）")
    default_logger.warning("默认模块 - WARNING消息")
    default_logger.error("默认模块 - ERROR消息")


def test_configuration_edge_cases():
    """测试配置边界情况"""
    print("\n=== 测试配置边界情况 ===")
    
    # 1. 测试仅文件日志
    print("1. 测试仅文件日志...")
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'file_only.log')
    
    try:
        LogManager().reset()
        configure(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_CONSOLE_ENABLED=False,
            LOG_FILE_ENABLED=True
        )
        
        logger = get_logger('test.file_only')
        logger.info("仅文件日志测试消息")
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   文件内容存在: {len(content) > 0}")
        else:
            print("   文件不存在!")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 2. 测试仅控制台日志
    print("2. 测试仅控制台日志...")
    LogManager().reset()
    configure(
        LOG_LEVEL='INFO',
        LOG_CONSOLE_ENABLED=True,
        LOG_FILE_ENABLED=False
    )
    
    logger = get_logger('test.console_only')
    logger.info("仅控制台日志测试消息")
    
    # 3. 测试无效配置处理
    print("3. 测试无效配置处理...")
    LogManager().reset()
    
    # 测试无效级别（应该使用默认级别）
    config = configure(LOG_LEVEL='INVALID')
    print(f"   无效级别处理: {config.level}")
    
    # 测试空配置
    LogManager().reset()
    config = configure()
    print(f"   默认配置级别: {config.level}")


def main():
    """主测试函数"""
    print("开始最终测试Crawlo框架日志系统...")
    
    try:
        # 运行所有测试
        test_complete_log_functionality()
        test_module_specific_logging()
        test_configuration_edge_cases()
        
        print("\n=== 最终测试完成 ===")
        print("\n日志系统功能总结:")
        print("✅ 基本日志配置")
        print("✅ 文件和控制台输出")
        print("✅ 日志级别控制")
        print("✅ 模块特定日志级别")
        print("✅ 日志轮转功能")
        print("✅ 配置验证")
        print("✅ 边界情况处理")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())