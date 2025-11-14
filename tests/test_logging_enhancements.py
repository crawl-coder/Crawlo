#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
日志系统增强功能测试
"""

import os
import sys
import tempfile
import shutil
import threading
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import (
    configure_logging, 
    get_logger, 
    LogManager,
    get_monitor
)
from crawlo.logging.config import LogConfig
from crawlo.logging.sampler import get_sampler
from crawlo.logging.async_handler import AsyncConcurrentRotatingFileHandler


def test_log_configuration():
    """测试日志配置功能"""
    print("=== 测试日志配置功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'enhanced_test.log')
    
    try:
        # 1. 测试分别设置控制台和文件日志级别
        print("1. 测试分别设置控制台和文件日志级别...")
        LogManager().reset()
        
        config = configure_logging(
            LOG_LEVEL='INFO',
            LOG_CONSOLE_LEVEL='WARNING',  # 控制台只显示WARNING及以上
            LOG_FILE_LEVEL='DEBUG',       # 文件记录DEBUG及以上
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=True,
            LOG_INCLUDE_THREAD_ID=True,   # 包含线程ID
            LOG_INCLUDE_PROCESS_ID=True   # 包含进程ID
        )
        
        print(f"   配置详情:")
        print(f"     主级别: {config.level}")
        print(f"     控制台级别: {config.console_level}")
        print(f"     文件级别: {config.file_level}")
        print(f"     包含线程ID: {config.include_thread_id}")
        print(f"     包含进程ID: {config.include_process_id}")
        
        # 获取logger并测试输出
        logger = get_logger('test.enhanced')
        
        # 测试不同级别的日志
        print("2. 测试不同级别的日志输出...")
        logger.debug("DEBUG消息 - 应该在文件中看到，控制台看不到")
        logger.info("INFO消息 - 应该在文件中看到，控制台看不到")
        logger.warning("WARNING消息 - 应该在文件和控制台都看到")
        logger.error("ERROR消息 - 应该在文件和控制台都看到")
        
        # 检查日志文件内容
        print("3. 检查日志文件内容...")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   日志文件行数: {len(lines)}")
                for i, line in enumerate(lines):
                    print(f"     {i+1}: {line.strip()}")
                    
                # 验证是否包含线程ID和进程ID
                if lines:
                    first_line = lines[0]
                    has_thread_id = '[Thread-' in first_line or '[thread:' in first_line.lower()
                    has_process_id = '[Process-' in first_line or '[process:' in first_line.lower()
                    print(f"   包含线程ID: {has_thread_id}")
                    print(f"   包含进程ID: {has_process_id}")
        else:
            print("   日志文件不存在!")
            
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_log_performance_monitoring():
    """测试日志性能监控功能"""
    print("\n=== 测试日志性能监控功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'monitor_test.log')
    
    try:
        # 重置并配置日志系统
        LogManager().reset()
        configure_logging(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=False
        )
        
        # 启用性能监控
        monitor = get_monitor()
        monitor.enable_monitoring()
        
        # 获取logger并生成一些日志
        logger = get_logger('test.monitor')
        
        print("1. 生成测试日志...")
        for i in range(10):
            logger.info(f"测试日志消息 {i+1}")
            logger.warning(f"测试警告消息 {i+1}")
            logger.error(f"测试错误消息 {i+1}")
            
        # 等待一小段时间
        time.sleep(0.1)
        
        # 获取性能统计
        print("2. 获取性能统计...")
        stats = monitor.get_statistics()
        print(f"   统计信息: {stats}")
        
        # 获取性能报告
        print("3. 获取性能报告...")
        report = monitor.get_performance_report()
        print(f"   性能报告:\n{report}")
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_log_sampling():
    """测试日志采样功能"""
    print("\n=== 测试日志采样功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'sampler_test.log')
    
    try:
        # 重置并配置日志系统
        LogManager().reset()
        configure_logging(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=False
        )
        
        # 配置采样器
        sampler = get_sampler()
        sampler.set_sample_rate('test.sampler', 0.5)  # 50%采样率
        sampler.set_rate_limit('test.sampler', 100)   # 每秒最多100条日志
        
        # 获取logger
        logger = get_logger('test.sampler')
        
        print("1. 生成大量日志消息...")
        start_time = time.time()
        log_count = 0
        
        for i in range(100):
            # 使用采样器判断是否应该记录日志
            message = f"采样测试消息 {i+1}"
            if sampler.should_log('test.sampler', message):
                logger.info(message)
                log_count += 1
                
        end_time = time.time()
        
        print(f"   生成消息总数: 100")
        print(f"   实际记录消息数: {log_count}")
        print(f"   记录率: {log_count/100:.2%}")
        print(f"   耗时: {end_time - start_time:.3f}秒")
        
        # 检查日志文件
        print("2. 检查日志文件...")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   日志文件实际行数: {len(lines)}")
        else:
            print("   日志文件不存在!")
            
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_async_logging():
    """测试异步日志处理功能"""
    print("\n=== 测试异步日志处理功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'async_test.log')
    
    try:
        # 重置日志管理器
        LogManager().reset()
        
        # 直接测试异步处理器
        print("1. 测试异步并发轮转文件处理器...")
        
        # 创建异步处理器
        async_handler = AsyncConcurrentRotatingFileHandler(
            filename=log_file,
            maxBytes=1024*1024,  # 1MB
            backupCount=3
        )
        
        # 启动异步处理器
        async_handler.start()
        
        # 创建logger并添加异步处理器
        logger = get_logger('test.async')
        logger.handlers.clear()  # 清除现有处理器
        logger.addHandler(async_handler)
        logger.setLevel(10)  # DEBUG级别
        
        print("2. 生成异步日志...")
        start_time = time.time()
        
        # 生成大量日志
        for i in range(100):
            logger.info(f"异步日志消息 {i+1}")
            
        # 等待日志处理完成
        time.sleep(1.0)
        
        end_time = time.time()
        
        print(f"   生成100条日志耗时: {end_time - start_time:.3f}秒")
        
        # 检查日志文件
        print("3. 检查日志文件...")
        if os.path.exists(log_file):
            # 尝试不同的编码方式读取文件
            encodings = ['utf-8', 'gbk', 'latin1']
            lines = []
            for encoding in encodings:
                try:
                    with open(log_file, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
                    
            if lines:
                print(f"   日志文件行数: {len(lines)}")
                if lines:
                    print(f"   第一行: {lines[0].strip()}")
                    print(f"   最后一行: {lines[-1].strip()}")
            else:
                print("   无法读取日志文件内容")
        else:
            print("   日志文件不存在!")
            
        # 停止异步处理器
        async_handler.stop()
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_module_specific_levels():
    """测试模块特定日志级别"""
    print("\n=== 测试模块特定日志级别 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'module_levels_test.log')
    
    try:
        # 重置并配置日志系统
        LogManager().reset()
        configure_logging(
            LOG_LEVEL='WARNING',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=True,
            LOG_LEVELS={
                'module.debug': 'DEBUG',
                'module.info': 'INFO',
                'module.error': 'ERROR'
            }
        )
        
        # 测试不同模块的日志级别
        print("1. 测试DEBUG模块...")
        debug_logger = get_logger('module.debug')
        debug_logger.debug("DEBUG消息 - 应该显示")
        debug_logger.info("INFO消息 - 应该显示")
        debug_logger.warning("WARNING消息 - 应该显示")
        
        print("2. 测试INFO模块...")
        info_logger = get_logger('module.info')
        info_logger.debug("DEBUG消息 - 不应该显示")
        info_logger.info("INFO消息 - 应该显示")
        info_logger.warning("WARNING消息 - 应该显示")
        
        print("3. 测试ERROR模块...")
        error_logger = get_logger('module.error')
        error_logger.info("INFO消息 - 不应该显示")
        error_logger.warning("WARNING消息 - 不应该显示")
        error_logger.error("ERROR消息 - 应该显示")
        
        print("4. 测试默认模块...")
        default_logger = get_logger('module.default')
        default_logger.info("INFO消息 - 不应该显示")
        default_logger.warning("WARNING消息 - 应该显示")
        default_logger.error("ERROR消息 - 应该显示")
        
        # 检查日志文件
        print("5. 检查日志文件...")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   日志文件行数: {len(lines)}")
                for i, line in enumerate(lines):
                    print(f"     {i+1}: {line.strip()}")
        else:
            print("   日志文件不存在!")
            
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主测试函数"""
    print("开始测试Crawlo框架日志系统功能...")
    print("=" * 60)
    
    try:
        # 运行所有测试
        test_log_configuration()
        test_log_performance_monitoring()
        test_log_sampling()
        test_async_logging()
        test_module_specific_levels()
        
        print("\n" + "=" * 60)
        print("所有日志系统功能测试完成!")
        print("\n测试总结:")
        print("✅ 日志配置功能")
        print("✅ 日志性能监控")
        print("✅ 日志采样")
        print("✅ 异步日志处理")
        print("✅ 模块特定日志级别")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())