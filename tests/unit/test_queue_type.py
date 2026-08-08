#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 QUEUE_TYPE 配置获取
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.framework import CrawloFramework
from crawlo.core.config import CrawloConfig


def test_queue_type_standalone():
    """测试单机模式下的 QUEUE_TYPE"""
    print("=== 测试单机模式下的 QUEUE_TYPE ===")
    
    # 创建单机模式配置
    config = CrawloConfig.standalone(concurrency=4)
    
    # 创建框架实例
    framework = CrawloFramework(config.to_dict())
    
    # 获取 QUEUE_TYPE
    queue_type = framework.settings.get('QUEUE_TYPE', 'not found')
    run_mode = framework.settings.get('RUN_MODE', 'not found')
    
    print(f"RunMode: {run_mode}")
    print(f"QueueType: {queue_type}")
    
    # 验证是否正确
    assert queue_type == 'memory', f"期望 'memory'，实际得到 '{queue_type}'"
    assert run_mode == 'standalone', f"期望 'standalone'，实际得到 '{run_mode}'"
    
    print("✅ 单机模式测试通过")


def test_queue_type_distributed():
    """测试分布式模式下的 QUEUE_TYPE"""
    print("\n=== 测试分布式模式下的 QUEUE_TYPE ===")
    
    # 创建分布式模式配置
    config = CrawloConfig.distributed(
        redis_host='127.0.0.1',
        redis_port=6379,
        project_name='test_project',
        concurrency=4
    )
    
    # 创建框架实例
    framework = CrawloFramework(config.to_dict())
    
    # 获取 QUEUE_TYPE
    queue_type = framework.settings.get('QUEUE_TYPE', 'not found')
    run_mode = framework.settings.get('RUN_MODE', 'not found')
    
    print(f"RunMode: {run_mode}")
    print(f"QueueType: {queue_type}")
    
    # 验证是否正确
    assert queue_type == 'redis', f"期望 'redis'，实际得到 '{queue_type}'"
    assert run_mode == 'distributed', f"期望 'distributed'，实际得到 '{run_mode}'"
    
    print("✅ 分布式模式测试通过")


def test_queue_type_auto():
    """测试自动模式下的 QUEUE_TYPE"""
    print("\n=== 测试自动模式下的 QUEUE_TYPE ===")
    
    # 创建自动模式配置
    config = CrawloConfig.auto(concurrency=4)
    
    # 创建框架实例
    framework = CrawloFramework(config.to_dict())
    
    # 获取 QUEUE_TYPE
    queue_type = framework.settings.get('QUEUE_TYPE', 'not found')
    run_mode = framework.settings.get('RUN_MODE', 'not found')
    
    print(f"RunMode: {run_mode}")
    print(f"QueueType: {queue_type}")
    
    # 验证是否正确
    assert queue_type == 'auto', f"期望 'auto'，实际得到 '{queue_type}'"
    assert run_mode == 'auto', f"期望 'auto'，实际得到 '{run_mode}'"
    
    print("✅ 自动模式测试通过")


if __name__ == "__main__":
    print("开始测试 QUEUE_TYPE 配置获取...")
    
    try:
        test_queue_type_standalone()
        test_queue_type_distributed()
        test_queue_type_auto()
        
        print("\n🎉 所有测试通过！可以成功获取到 QUEUE_TYPE 配置。")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()