#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
测试日志缓冲问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import configure_logging as configure, get_logger
import logging


def test_log_buffering():
    """测试日志缓冲行为"""
    print("=== 测试日志缓冲行为 ===")
    
    # 设置日志文件路径
    log_file = "logs/buffering_test2.log"
    
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
    
    # 获取logger
    logger = get_logger('buffering.test2')
    
    print("1. 检查handler的自动刷新设置...")
    for handler in logger.handlers:
        handler_type = type(handler).__name__
        print(f"   Handler类型: {handler_type}")
        if hasattr(handler, 'stream'):
            print(f"   流类型: {type(handler.stream).__name__}")
            if hasattr(handler.stream, 'flush'):
                print(f"   支持flush方法: True")
        
        # 检查是否有自动刷新设置
        if hasattr(handler, 'flush'):
            print(f"   Handler有flush方法")
    
    print("\n2. 写入日志并强制刷新...")
    logger.info("测试日志1")
    logger.info("测试日志2")
    
    # 强制刷新所有handler
    for handler in logger.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
            print(f"   已刷新 {type(handler).__name__}")
    
    # 检查文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"\n日志文件内容:")
            print(f"  行数: {len(content.splitlines())}")
            print(f"  内容: {repr(content)}")
    
    print("\n3. 测试不同日志级别的缓冲...")
    logger.debug("DEBUG消息（不应显示）")
    logger.info("INFO消息")
    logger.warning("WARNING消息")
    logger.error("ERROR消息")
    
    # 再次强制刷新
    for handler in logger.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
    
    # 检查最终文件内容
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"\n最终日志文件内容:")
            print(f"  总行数: {len(lines)}")
            for i, line in enumerate(lines):
                print(f"  {i+1}: {line.strip()}")


def main():
    """主函数"""
    print("开始测试日志缓冲问题...")
    
    try:
        test_log_buffering()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())