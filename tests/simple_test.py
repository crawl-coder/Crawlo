#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化的框架测试
"""
import os
import sys
sys.path.insert(0, '/')

# 设置基本配置
test_log_file = '/Users/oscar/projects/Crawlo/simple_test.log'
if os.path.exists(test_log_file):
    os.remove(test_log_file)

# 最简单的测试
try:
    from crawlo.utils.log import LoggerManager
    
    print("配置日志系统...")
    LoggerManager.configure(
        LOG_LEVEL='INFO',
        LOG_FILE=test_log_file
    )
    
    from crawlo.utils.log import get_logger
    logger = get_logger('test.simple')
    
    print("测试日志输出...")
    logger.info("这是一条测试信息")
    logger.info("Crawlo框架初始化完成")
    logger.info("Crawlo Framework Started 1.3.3")
    
    print("检查日志文件...")
    if os.path.exists(test_log_file):
        with open(test_log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"日志文件内容: {len(content)} 字符")
            print("内容:")
            print(content)
    else:
        print("日志文件未创建")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("测试完成")