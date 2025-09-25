#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试 QUEUE_TYPE 配置获取
验证我们的日志格式修改是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.framework import CrawloFramework


def test_log_format():
    """测试日志格式修改是否正常工作"""
    print("=== 测试日志格式修改 ===")
    
    # 创建单机模式配置
    config = CrawloConfig.standalone(concurrency=4)
    
    # 创建框架实例，这会触发日志输出
    framework = CrawloFramework(config.to_dict())
    
    # 获取配置信息
    run_mode = framework.settings.get('RUN_MODE', 'not found')
    queue_type = framework.settings.get('QUEUE_TYPE', 'not found')
    
    print(f"从配置中获取到的信息:")
    print(f"  RunMode: {run_mode}")
    print(f"  QueueType: {queue_type}")
    
    print("\n✅ 日志格式修改测试完成")


if __name__ == "__main__":
    print("开始简单测试 QUEUE_TYPE 配置获取...")
    test_log_format()
    print("\n测试结束！")