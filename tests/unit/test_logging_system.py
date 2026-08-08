#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
全面测试Crawlo框架日志系统的所有功能
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


def test_basic_logging():
    """测试基本日志功能"""
    print("=== 测试基本日志功能 ===")
    
    # 1. 测试默认配置
    print("1. 测试默认配置...")
    configure()
    config = LogManager().config
    print(f"   默认级别: {config.level}")
    print(f"   默认格式: {config.format}")
    
    # 2. 测试获取logger
    logger = get_logger('test.basic')
    print(f"   Logger名称: {logger.name}")
    print(f"   Handlers数量: {len(logger.handlers)}")
    
    # 3. 测试日志输出
    logger.info("这是一条INFO级别日志")
    logger.warning("这是一条WARNING级别日志")
    logger.error("这是一条ERROR级别日志")
    print("   日志输出完成")


def test_file_logging():
    """测试文件日志功能"""
    print("\n=== 测试文件日志功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'test.log')
    
    try:
        # 1. 配置文件日志
        print("1. 配置文件日志...")
        configure(
            LOG_LEVEL='DEBUG',
            LOG_FILE=log_file,
            LOG_MAX_BYTES=1024,  # 小的轮转大小用于测试
            LOG_BACKUP_COUNT=3
        )
        
        config = LogManager().config
        print(f"   日志文件: {config.file_path}")
        print(f"   轮转大小: {config.max_bytes}")
        print(f"   备份数量: {config.backup_count}")
        
        # 2. 获取logger并测试输出
        logger = get_logger('test.file')
        print("2. 测试日志输出...")
        
        # 输出多条日志以触发轮转
        for i in range(50):
            logger.debug(f"这是第{i+1}条DEBUG日志，用于测试轮转功能")
            logger.info(f"这是第{i+1}条INFO日志，用于测试轮转功能")
        
        # 3. 检查日志文件
        print("3. 检查日志文件...")
        if os.path.exists(log_file):
            file_size = os.path.getsize(log_file)
            print(f"   主日志文件大小: {file_size} 字节")
        else:
            print("   主日志文件不存在!")
            
        # 检查备份文件
        for i in range(1, 4):
            backup_file = f"{log_file}.{i}"
            if os.path.exists(backup_file):
                backup_size = os.path.getsize(backup_file)
                print(f"   备份文件 {i} 大小: {backup_size} 字节")
            else:
                print(f"   备份文件 {i} 不存在")
                
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_console_logging():
    """测试控制台日志功能"""
    print("\n=== 测试控制台日志功能 ===")
    
    # 1. 配置仅控制台日志
    print("1. 配置仅控制台日志...")
    configure(
        LOG_LEVEL='INFO',
        LOG_CONSOLE_ENABLED=True,
        LOG_FILE_ENABLED=False
    )
    
    config = LogManager().config
    print(f"   控制台启用: {config.console_enabled}")
    print(f"   文件日志启用: {config.file_enabled}")
    
    # 2. 测试日志输出
    logger = get_logger('test.console')
    print("2. 测试日志输出...")
    logger.info("这条日志应该只在控制台显示")
    logger.debug("这条DEBUG日志不应该显示（级别低于INFO）")


def test_module_level_logging():
    """测试模块级别日志功能"""
    print("\n=== 测试模块级别日志功能 ===")
    
    # 1. 配置模块级别
    print("1. 配置模块级别...")
    configure(
        LOG_LEVEL='WARNING',
        LOG_LEVELS={
            'test.module.high': 'DEBUG',
            'test.module.low': 'ERROR'
        }
    )
    
    config = LogManager().config
    print(f"   默认级别: {config.level}")
    print(f"   模块级别配置: {config.module_levels}")
    
    # 2. 测试不同模块的日志级别
    print("2. 测试不同模块的日志级别...")
    
    # 高级别模块（DEBUG）
    high_logger = get_logger('test.module.high')
    print(f"   high_logger 级别: {logging.getLevelName(high_logger.handlers[0].level)}")
    high_logger.debug("这条DEBUG日志应该显示")
    high_logger.info("这条INFO日志应该显示")
    
    # 低级别模块（ERROR）
    low_logger = get_logger('test.module.low')
    print(f"   low_logger 级别: {logging.getLevelName(low_logger.handlers[0].level)}")
    low_logger.info("这条INFO日志不应该显示")
    low_logger.error("这条ERROR日志应该显示")
    
    # 默认级别模块（WARNING）
    default_logger = get_logger('test.module.default')
    print(f"   default_logger 级别: {logging.getLevelName(default_logger.handlers[0].level)}")
    default_logger.info("这条INFO日志不应该显示")
    default_logger.warning("这条WARNING日志应该显示")


def test_log_config_from_settings():
    """测试从settings对象创建配置"""
    print("\n=== 测试从settings对象创建配置 ===")
    
    # 1. 创建模拟settings对象
    class MockSettings:
        def __init__(self):
            self.LOG_LEVEL = 'DEBUG'
            self.LOG_FILE = 'test_settings.log'
            self.LOG_MAX_BYTES = 5 * 1024 * 1024
            self.LOG_BACKUP_COUNT = 2
            self.LOG_ENCODING = 'utf-8'
            self.LOG_CONSOLE_ENABLED = True
            self.LOG_FILE_ENABLED = True
            self.LOG_LEVELS = {'test.custom': 'INFO'}
    
    # 2. 从settings创建配置
    print("2. 从settings创建配置...")
    settings = MockSettings()
    config = LogConfig.from_settings(settings)
    
    print(f"   级别: {config.level}")
    print(f"   文件: {config.file_path}")
    print(f"   轮转大小: {config.max_bytes}")
    print(f"   备份数量: {config.backup_count}")
    print(f"   编码: {config.encoding}")
    print(f"   控制台启用: {config.console_enabled}")
    print(f"   文件启用: {config.file_enabled}")
    print(f"   模块级别: {config.module_levels}")


def test_log_config_validation():
    """测试日志配置验证功能"""
    print("\n=== 测试日志配置验证功能 ===")
    
    # 1. 测试有效配置
    print("1. 测试有效配置...")
    valid_config = LogConfig(
        level='INFO',
        file_path='test_valid.log'
    )
    is_valid = valid_config.validate()
    print(f"   有效配置验证结果: {is_valid}")
    
    # 2. 测试无效级别
    print("2. 测试无效级别...")
    invalid_config = LogConfig(
        level='INVALID',
        file_path='test_invalid.log'
    )
    is_valid = invalid_config.validate()
    print(f"   无效级别验证结果: {is_valid}")
    
    # 3. 测试目录创建
    print("3. 测试目录创建...")
    temp_dir = tempfile.mkdtemp()
    nested_log_file = os.path.join(temp_dir, 'subdir', 'test.log')
    
    config = LogConfig(
        level='INFO',
        file_path=nested_log_file
    )
    is_valid = config.validate()
    print(f"   目录创建验证结果: {is_valid}")
    
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_logger_caching():
    """测试Logger缓存功能"""
    print("\n=== 测试Logger缓存功能 ===")
    
    # 重置配置以确保测试环境干净
    LogManager().reset()
    
    # 1. 获取同一个logger多次
    print("1. 测试缓存...")
    logger1 = get_logger('test.cache')
    logger2 = get_logger('test.cache')
    
    print(f"   第一次获取: {id(logger1)}")
    print(f"   第二次获取: {id(logger2)}")
    print(f"   是否为同一对象: {logger1 is logger2}")
    
    # 2. 测试配置更新后缓存刷新
    print("2. 测试配置更新...")
    configure(LOG_LEVEL='ERROR')
    logger3 = get_logger('test.cache')
    print(f"   更新配置后获取: {id(logger3)}")
    print(f"   是否与之前相同: {logger1 is logger3}")


def main():
    """主测试函数"""
    print("开始全面测试Crawlo框架日志系统...")
    
    try:
        # 运行所有测试
        test_basic_logging()
        test_file_logging()
        test_console_logging()
        test_module_level_logging()
        test_log_config_from_settings()
        test_log_config_validation()
        test_logger_caching()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


# 导入logging模块用于测试
import logging

if __name__ == '__main__':
    sys.exit(main())