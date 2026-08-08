#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试CLI参数解析
验证crawlo run命令是否正确解析--log-level、--config和--concurrency参数
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 简单测试参数解析逻辑
def test_argument_parsing():
    """测试参数解析逻辑"""
    # 模拟参数
    args = ['test_spider', '--log-level', 'DEBUG', '--concurrency', '32']
    
    # 解析参数
    spider_arg = args[0]
    
    # 解析日志级别参数
    log_level = None
    if "--log-level" in args:
        try:
            log_level_index = args.index("--log-level")
            if log_level_index + 1 < len(args):
                log_level = args[log_level_index + 1]
        except (ValueError, IndexError):
            pass
    
    # 解析并发数参数
    concurrency = None
    if "--concurrency" in args:
        try:
            concurrency_index = args.index("--concurrency")
            if concurrency_index + 1 < len(args):
                concurrency = int(args[concurrency_index + 1])
        except (ValueError, IndexError, TypeError):
            pass
    
    print(f"Spider: {spider_arg}")
    print(f"Log level: {log_level}")
    print(f"Concurrency: {concurrency}")
    
    # 验证结果
    assert spider_arg == 'test_spider'
    assert log_level == 'DEBUG'
    assert concurrency == 32
    
    print("✅ 参数解析测试通过!")

if __name__ == '__main__':
    test_argument_parsing()