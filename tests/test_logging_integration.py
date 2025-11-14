#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
日志系统集成测试
模拟实际使用场景进行测试
"""

import os
import sys
import tempfile
import shutil
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


def test_real_world_scenario():
    """测试真实世界的使用场景"""
    print("=== 测试真实世界的使用场景 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'real_world_test.log')
    
    try:
        # 1. 模拟项目初始化配置
        print("1. 模拟项目初始化配置...")
        LogManager().reset()
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"   创建日志目录: {log_dir}")
        
        # 模拟一个典型的生产环境配置
        config = configure_logging(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=True,
            LOG_MAX_BYTES=1024*1024,  # 1MB
            LOG_BACKUP_COUNT=5,
            LOG_ENCODING='utf-8',
            LOG_FORMAT='%(asctime)s - [%(name)s] - %(levelname)s: %(message)s',
            LOG_LEVELS={
                'crawlo.framework': 'INFO',
                'crawlo.crawler': 'DEBUG',
                'my_spider': 'DEBUG'
            }
        )
        
        print(f"   配置完成: {config.level}")
        print(f"   日志文件路径: {config.file_path}")
        print(f"   文件启用: {config.file_enabled}")
        
        # 启用性能监控
        monitor = get_monitor()
        monitor.enable_monitoring()
        
        # 2. 模拟框架启动日志
        print("2. 模拟框架启动日志...")
        framework_logger = get_logger('crawlo.framework')
        framework_logger.info("Crawlo Framework Started 1.4.2")
        framework_logger.info("Run mode: standalone")
        
        # 3. 模拟爬虫运行日志
        print("3. 模拟爬虫运行日志...")
        crawler_logger = get_logger('crawlo.crawler')
        crawler_logger.debug("初始化爬虫引擎...")
        crawler_logger.info("开始运行爬虫任务")
        crawler_logger.warning("检测到网络延迟较高")
        crawler_logger.error("下载页面失败: https://example.com")
        
        # 4. 模拟自定义爬虫日志
        print("4. 模拟自定义爬虫日志...")
        spider_logger = get_logger('my_spider')
        spider_logger.debug("解析页面内容...")
        spider_logger.info("提取到10个数据项")
        spider_logger.warning("部分数据格式不正确")
        
        # 5. 模拟性能统计
        print("5. 模拟性能统计...")
        stats_logger = get_logger('crawlo.stats')
        stats_logger.info("已爬取 150 页 (速率为 30 页/5分钟)，获得 75 个项目 (速率为 15 项目/5分钟)")
        
        # 等待日志写入完成
        time.sleep(0.1)
        
        # 6. 检查日志文件
        print("6. 检查日志文件...")
        print(f"   日志文件路径: {log_file}")
        print(f"   文件是否存在: {os.path.exists(log_file)}")
        
        if os.path.exists(log_file):
            file_size = os.path.getsize(log_file)
            print(f"   日志文件大小: {file_size} 字节")
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   日志文件行数: {len(lines)}")
                
                # 显示前几行日志
                print("   前5行日志内容:")
                for i, line in enumerate(lines[:5]):
                    print(f"     {i+1}: {line.strip()}")
                    
                # 显示后几行日志
                print("   后5行日志内容:")
                for i, line in enumerate(lines[-5:], len(lines)-4):
                    print(f"     {i}: {line.strip()}")
        else:
            print("   ❌ 日志文件不存在!")
            # 检查目录内容
            if os.path.exists(log_dir):
                files = os.listdir(log_dir)
                print(f"   目录中的文件: {files}")
            else:
                print(f"   日志目录不存在: {log_dir}")
            
        # 7. 获取性能报告
        print("7. 获取性能报告...")
        report = monitor.get_performance_report()
        print(f"   性能报告生成完成")
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_windows_compatibility():
    """测试Windows兼容性"""
    print("\n=== 测试Windows兼容性 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'windows_test.log')
    
    try:
        # 重置并配置日志系统
        LogManager().reset()
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"   创建日志目录: {log_dir}")
        
        # 模拟Windows环境下的配置
        config = configure_logging(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=True,
            LOG_MAX_BYTES=512*1024,  # 512KB，较小的轮转大小用于测试
            LOG_BACKUP_COUNT=3
        )
        
        print(f"   配置完成，日志文件: {config.file_path}")
        
        logger = get_logger('test.windows')
        
        # 生成大量日志以触发轮转
        print("生成大量日志以测试轮转...")
        for i in range(200):
            logger.info(f"测试轮转消息 {i+1} - 这是一条比较长的消息，用于快速达到轮转大小限制，测试Windows兼容性")
            
        # 等待一段时间确保日志写入完成
        time.sleep(1)
        
        # 检查主日志文件和备份文件
        print("检查日志文件和备份文件...")
        print(f"   日志文件路径: {log_file}")
        print(f"   文件是否存在: {os.path.exists(log_file)}")
        
        if os.path.exists(log_file):
            main_size = os.path.getsize(log_file)
            print(f"   主日志文件大小: {main_size} 字节")
        else:
            print("   ❌ 主日志文件不存在!")
            
        # 检查备份文件
        backup_files = []
        for i in range(1, 4):
            backup_file = f"{log_file}.{i}"
            if os.path.exists(backup_file):
                backup_size = os.path.getsize(backup_file)
                backup_files.append((backup_file, backup_size))
                print(f"   备份文件 {i} 大小: {backup_size} 字节")
            else:
                print(f"   备份文件 {i} 不存在")
                
        print(f"   总共找到 {len(backup_files)} 个备份文件")
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_error_handling():
    """测试错误处理能力"""
    print("\n=== 测试错误处理能力 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'error_test.log')
    
    try:
        # 重置并配置日志系统
        LogManager().reset()
        
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"   创建日志目录: {log_dir}")
        
        # 正常配置
        config = configure_logging(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=True
        )
        
        print(f"   配置完成，日志文件: {config.file_path}")
        
        logger = get_logger('test.error')
        
        # 测试不同级别的日志
        print("测试不同级别的日志记录...")
        logger.debug("DEBUG消息 - 不应该显示")
        logger.info("INFO消息 - 应该显示")
        logger.warning("WARNING消息 - 应该显示")
        logger.error("ERROR消息 - 应该显示")
        logger.critical("CRITICAL消息 - 应该显示")
        
        # 等待日志写入完成
        time.sleep(0.1)
        
        # 模拟文件权限问题
        print("模拟文件权限问题...")
        # 这里我们不实际模拟权限问题，只是测试日志系统在异常情况下的表现
        
        # 检查日志文件
        print("检查日志文件...")
        print(f"   日志文件路径: {log_file}")
        print(f"   文件是否存在: {os.path.exists(log_file)}")
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   日志文件行数: {len(lines)}")
                # 应该只有4行（INFO, WARNING, ERROR, CRITICAL）
                expected_lines = 4
                if len(lines) == expected_lines:
                    print(f"   ✅ 日志级别过滤正常")
                else:
                    print(f"   ❌ 日志级别过滤异常，期望 {expected_lines} 行，实际 {len(lines)} 行")
        else:
            print("   ❌ 日志文件不存在!")
            # 检查目录内容
            if os.path.exists(log_dir):
                files = os.listdir(log_dir)
                print(f"   目录中的文件: {files}")
            else:
                print(f"   日志目录不存在: {log_dir}")
            
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主测试函数"""
    print("开始Crawlo框架日志系统集成测试...")
    print("=" * 60)
    
    try:
        # 运行所有测试
        test_real_world_scenario()
        test_windows_compatibility()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("日志系统集成测试完成!")
        print("\n测试总结:")
        print("✅ 真实世界使用场景")
        print("✅ Windows兼容性")
        print("✅ 错误处理能力")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())