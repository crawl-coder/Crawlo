#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
简单的日志系统测试
"""
import sys
import os
sys.path.insert(0, '/')

# 确保日志目录存在
os.makedirs('/examples/ofweek_standalone/logs', exist_ok=True)

# 测试日志系统
from crawlo.utils.log import LoggerManager, get_logger

print("=== 简单日志系统测试 ===")

# 1. 直接配置日志系统
print("1. 配置日志系统...")
LoggerManager.configure(
    LOG_LEVEL='INFO',
    LOG_FILE='/Users/oscar/projects/Crawlo/examples/ofweek_standalone/logs/simple_test.log'
)

# 2. 创建logger
print("2. 创建logger...")
logger = get_logger('test.logger')
print(f"   Logger: {logger}")
print(f"   Handlers: {len(logger.handlers)}")

for i, handler in enumerate(logger.handlers):
    handler_type = type(handler).__name__
    print(f"     Handler {i}: {handler_type}")
    if hasattr(handler, 'baseFilename'):
        print(f"       File: {handler.baseFilename}")

# 3. 测试日志输出
print("3. 测试日志输出...")
logger.info("这是一条测试INFO日志")
logger.debug("这是一条测试DEBUG日志")
logger.warning("这是一条测试WARNING日志")

print("4. 检查日志文件...")
log_file = '/Users/oscar/projects/Crawlo/examples/ofweek_standalone/logs/simple_test.log'
if os.path.exists(log_file):
    print(f"   日志文件存在: {log_file}")
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"   文件内容长度: {len(content)} 字符")
        if content:
            print("   文件内容:")
            print(content)
        else:
            print("   文件为空")
else:
    print(f"   日志文件不存在: {log_file}")

print("=== 测试完成 ===")