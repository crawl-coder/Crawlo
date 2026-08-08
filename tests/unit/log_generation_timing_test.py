#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试日志文件的生成时机
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import configure_logging as configure, get_logger


def test_log_file_generation_timing():
    """测试日志文件的生成时机"""
    print("=== 测试日志文件的生成时机 ===")
    
    # 设置日志文件路径
    log_file = "logs/timing_test.log"
    
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)
    
    # 删除可能存在的旧日志文件
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"已删除旧日志文件: {log_file}")
    
    print(f"日志文件路径: {log_file}")
    print(f"日志文件是否存在: {os.path.exists(log_file)}")
    
    # 配置日志系统
    print("\n1. 配置日志系统...")
    configure(
        level='INFO',
        file_path=log_file,
        console_enabled=True,
        file_enabled=True
    )
    
    print(f"配置后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 获取logger
    print("\n2. 获取logger...")
    logger = get_logger('timing.test')
    print(f"获取logger后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 立即写入日志
    print("\n3. 立即写入日志...")
    logger.info("立即写入的第一条日志")
    print(f"写入第一条日志后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 检查文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"日志文件内容行数: {len(content.splitlines())}")
            print(f"日志文件大小: {os.path.getsize(log_file)} 字节")
    
    # 等待一小段时间
    print("\n4. 等待1秒...")
    time.sleep(1)
    print(f"等待后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 再写入一些日志
    print("\n5. 再写入一些日志...")
    for i in range(5):
        logger.info(f"第{i+1}条测试日志")
        time.sleep(0.1)
    
    print(f"写入多条日志后日志文件是否存在: {os.path.exists(log_file)}")
    
    # 检查最终文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"\n最终日志文件内容:")
            print(f"  总行数: {len(lines)}")
            print(f"  文件大小: {os.path.getsize(log_file)} 字节")
            if lines:
                print(f"  第一行: {lines[0].strip()}")
                print(f"  最后一行: {lines[-1].strip()}")
    
    print("\n=== 测试完成 ===")


def test_buffering_behavior():
    """测试日志缓冲行为"""
    print("\n=== 测试日志缓冲行为 ===")
    
    # 设置日志文件路径
    log_file = "logs/buffering_test.log"
    
    # 删除可能存在的旧日志文件
    if os.path.exists(log_file):
        os.remove(log_file)
    
    # 配置日志系统
    configure(
        level='INFO',
        file_path=log_file,
        console_enabled=True,
        file_enabled=True
    )
    
    logger = get_logger('buffering.test')
    
    print("1. 写入日志后立即检查文件...")
    logger.info("缓冲测试日志1")
    print(f"   写入后文件是否存在: {os.path.exists(log_file)}")
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   文件内容: '{content.strip()}'")
    
    print("2. 强制刷新并检查...")
    # 获取文件处理器并强制刷新
    for handler in logger.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
    
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"   刷新后文件内容: '{content.strip()}'")


def main():
    """主函数"""
    print("开始测试日志文件的生成时机...")
    
    try:
        test_log_file_generation_timing()
        test_buffering_behavior()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())