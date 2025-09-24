#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
简单的日志系统测试
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


def test_file_logging_simple():
    """简单测试文件日志功能"""
    print("=== 简单测试文件日志功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'simple_test.log')
    
    try:
        print(f"日志文件路径: {log_file}")
        
        # 配置文件日志
        configure(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True
        )
        
        config = LogManager().config
        print(f"配置文件路径: {config.file_path}")
        print(f"文件启用: {config.file_enabled}")
        
        # 获取logger并测试输出
        logger = get_logger('test.simple')
        print(f"Logger handlers数量: {len(logger.handlers)}")
        
        for handler in logger.handlers:
            print(f"Handler类型: {type(handler).__name__}")
            if hasattr(handler, 'baseFilename'):
                print(f"Handler文件名: {handler.baseFilename}")
        
        logger.info("这是一条测试日志")
        logger.warning("这是一条警告日志")
        
        # 检查日志文件
        print("检查日志文件...")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"日志文件内容:\n{content}")
        else:
            print("日志文件不存在!")
            
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_console_only():
    """测试仅控制台日志"""
    print("\n=== 测试仅控制台日志 ===")
    
    # 配置仅控制台日志
    configure(
        LOG_LEVEL='INFO',
        LOG_CONSOLE_ENABLED=True,
        LOG_FILE_ENABLED=False
    )
    
    config = LogManager().config
    print(f"控制台启用: {config.console_enabled}")
    print(f"文件启用: {config.file_enabled}")
    
    # 获取logger并测试输出
    logger = get_logger('test.console_only')
    logger.info("这条日志应该只在控制台显示")


def test_module_levels():
    """测试模块级别日志"""
    print("\n=== 测试模块级别日志 ===")
    
    # 配置模块级别
    configure(
        LOG_LEVEL='WARNING',
        LOG_LEVELS={
            'module.debug': 'DEBUG',
            'module.error': 'ERROR'
        }
    )
    
    config = LogManager().config
    print(f"默认级别: {config.level}")
    print(f"模块级别: {config.module_levels}")
    
    # 测试不同模块的日志级别
    debug_logger = get_logger('module.debug')
    debug_logger.debug("这条DEBUG日志应该显示")
    debug_logger.info("这条INFO日志应该显示")
    
    error_logger = get_logger('module.error')
    error_logger.info("这条INFO日志不应该显示")
    error_logger.error("这条ERROR日志应该显示")


def main():
    """主测试函数"""
    print("开始简单测试Crawlo框架日志系统...")
    
    try:
        # 运行测试
        test_file_logging_simple()
        test_console_only()
        test_module_levels()
        
        print("\n=== 简单测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())