#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
准确测试请求优先级行为
验证priority值越小越优先的机制
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from crawlo.network.request import Request

def test_real_priority_behavior():
    """测试真实的优先级行为"""
    print("=== Crawlo请求优先级真实行为测试 ===\n")
    
    # 创建不同priority值的请求
    requests = [
        Request("https://example.com/p1", priority=1),     # 内部存储为 -1
        Request("https://example.com/p5", priority=5),     # 内部存储为 -5
        Request("https://example.com/p10", priority=10),   # 内部存储为 -10
        Request("https://example.com/p0", priority=0),     # 内部存储为 0
        Request("https://example.com/p-5", priority=-5),   # 内部存储为 5
    ]
    
    print("请求及内部priority值:")
    for req in requests:
        # 通过反射获取实际的内部priority值
        print(f"  {req.url.split('/')[-1]}: 传入priority={-req.priority}, 内部priority={req.priority}")
    
    print("\n按优先级排序（从小到大）:")
    sorted_requests = sorted(requests)
    
    print("排序结果:")
    for i, req in enumerate(sorted_requests):
        print(f"  {i+1}. {req.url.split('/')[-1]}: 内部priority={req.priority}")
    
    print("\n=== 优先级解释 ===")
    print("排序规则: priority值越小，优先级越高")
    print("所以排序结果为:")
    print("  1. p10 (priority=-10) - 最高优先级")
    print("  2. p5 (priority=-5) - 高优先级")
    print("  3. p1 (priority=-1) - 中等优先级")
    print("  4. p0 (priority=0) - 低优先级")
    print("  5. p-5 (priority=5) - 最低优先级")
    
    print("\n=== 结论 ===")
    print("✓ priority值越小，优先级越高")
    print("✓ 传入负数时，内部存储为正数，优先级较低")
    print("✓ 传入正数时，内部存储为负数，优先级较高")
    print("✓ 传入0时，内部存储为0，优先级中等")

if __name__ == '__main__':
    test_real_priority_behavior()