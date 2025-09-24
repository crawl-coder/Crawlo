#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证运行模式日志级别修改的简单测试
"""
import os

# 删除旧日志文件
log_file = 'verify_debug.log'
if os.path.exists(log_file):
    os.remove(log_file)

# 简单测试日志级别
from crawlo.utils.log import LoggerManager

# 配置日志系统
LoggerManager.configure(
    LOG_LEVEL='INFO',
    LOG_FILE=log_file
)

from crawlo.utils.log import get_logger

# 创建测试logger
test_logger = get_logger('crawlo.framework')

# 测试输出
test_logger.info("这是INFO级别的测试信息")
test_logger.debug("这是DEBUG级别的测试信息（不应该在INFO级别的日志中出现）")
test_logger.debug("使用单机模式 - 简单快速，适合开发和中小规模爬取")

print("测试完成")

# 检查日志文件
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"日志文件内容（{len(content)} 字符）:")
        print(content)
        
        # 检查是否包含不应该出现的DEBUG信息
        if "DEBUG" in content:
            print("❌ 发现DEBUG级别信息（不应该出现）")
        else:
            print("✅ 没有发现DEBUG级别信息（正确）")
            
        if "使用单机模式" in content:
            print("❌ 发现运行模式信息（不应该出现在INFO级别）")
        else:
            print("✅ 没有发现运行模式信息（正确）")
else:
    print("❌ 日志文件未创建")