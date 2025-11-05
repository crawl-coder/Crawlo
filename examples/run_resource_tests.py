#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
资源泄漏测试运行脚本
运行长期运行和多Spider场景的测试
"""

import asyncio
import sys
import os
sys.path.insert(0, '/Users/oscar/projects/Crawlo')

# 初始化框架
from crawlo.initialization import initialize_framework
settings = initialize_framework()

from long_running_test import simulate_long_running
from multi_spider_test import test_hundreds_of_spiders


async def run_all_tests():
    """运行所有资源泄漏测试"""
    print("开始运行资源泄漏测试...")
    
    # 测试1: 长期运行场景
    print("\n" + "="*60)
    print("测试1: 长期运行场景")
    print("="*60)
    
    try:
        trend = await simulate_long_running(hours_to_run=0.1)  # 运行6分钟测试
        long_running_success = trend.get('status') != 'leak_detected'
        print(f"长期运行测试结果: {'通过' if long_running_success else '失败'}")
    except Exception as e:
        print(f"长期运行测试异常: {e}")
        import traceback
        traceback.print_exc()
        long_running_success = False
    
    # 测试2: 多Spider场景
    print("\n" + "="*60)
    print("测试2: 多Spider场景")
    print("="*60)
    
    try:
        multi_spider_success = await test_hundreds_of_spiders(count=20)  # 测试20个Spider
        print(f"多Spider测试结果: {'通过' if multi_spider_success else '失败'}")
    except Exception as e:
        print(f"多Spider测试异常: {e}")
        import traceback
        traceback.print_exc()
        multi_spider_success = False
    
    # 总结结果
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"长期运行测试: {'✅ 通过' if long_running_success else '❌ 失败'}")
    print(f"多Spider测试: {'✅ 通过' if multi_spider_success else '❌ 失败'}")
    
    overall_success = long_running_success and multi_spider_success
    print(f"\n总体结果: {'🎉 所有测试通过!' if overall_success else '⚠️  部分测试失败!'}")
    
    return overall_success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)