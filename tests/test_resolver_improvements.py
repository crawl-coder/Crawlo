#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证 spider resolver 改进的测试
测试错误优先级、去重机制、类型校验等功能
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.spider.resolver import SpiderResolver
from crawlo.spider.spider import SpiderDiscoveryState


def test_error_priority():
    """测试错误优先级：导入失败 > 未找到爬虫"""
    print("\n=== 测试 1: 错误优先级 ===")
    
    # 清理之前的状态
    SpiderDiscoveryState.clear()
    
    try:
        # 尝试解析一个不存在的爬虫，其模块也不存在
        SpiderResolver.resolve_spider_class('nonexistent_module.NonexistentSpider', ['nonexistent_module'])
        print("❌ 应该抛出异常")
        return False
    except ValueError as e:
        error_msg = str(e)
        if "Failed to import spider modules" in error_msg:
            print(f"✅ 正确报告导入失败: {error_msg}")
            return True
        elif "not found in registry" in error_msg:
            print(f"⚠️  报告未找到爬虫（但模块不存在时应优先报告导入失败）: {error_msg}")
            return False
        else:
            print(f"❌ 未知错误消息: {error_msg}")
            return False


def test_duplicate_prevention():
    """测试错误去重机制"""
    print("\n=== 测试 2: 错误去重 ===")
    
    # 清理状态
    SpiderDiscoveryState.clear()
    
    try:
        # 多次尝试解析同一个不存在的爬虫
        for i in range(3):
            SpiderResolver.resolve_spider_class('missing.Spider', ['missing_module'])
    except ValueError as e:
        error_msg = str(e)
        # 统计完全相同的错误子串重复次数
        # 应该只有 2 个不同的错误：missing_module 和 missing.Spider
        # 不应该因为循环 3 次而出现 6 个错误
        missing_module_count = error_msg.count("missing_module:")
        missing_spider_count = error_msg.count("missing.Spider:")
        
        if missing_module_count == 1 and missing_spider_count == 1:
            print(f"✅ 错误消息无重复（每个模块各出现 1 次）")
            return True
        else:
            print(f"❌ 错误消息重复（missing_module 出现 {missing_module_count} 次, missing.Spider 出现 {missing_spider_count} 次）: {error_msg}")
            return False


def test_type_validation():
    """测试 Spider 类型校验"""
    print("\n=== 测试 3: Spider 类型校验 ===")
    
    # 清理状态
    SpiderDiscoveryState.clear()
    
    # 创建一个测试模块，其中包含非 Spider 类
    test_module_code = '''
class NotASpider:
    name = "not_a_spider"
'''
    
    # 写入临时模块
    import tempfile
    import importlib.util
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='.') as f:
        f.write(test_module_code)
        temp_module_path = f.name
    
    module_name = os.path.splitext(os.path.basename(temp_module_path))[0]
    
    try:
        # 尝试加载非 Spider 类
        SpiderResolver.resolve_spider_class(f'{module_name}.NotASpider', [])
        print("❌ 应该拒绝非 Spider 类")
        return False
    except ValueError as e:
        error_msg = str(e)
        if "not a Spider subclass" in error_msg:
            print(f"✅ 正确拒绝非 Spider 类: {error_msg}")
            return True
        else:
            print(f"⚠️  错误消息不包含类型校验信息: {error_msg}")
            return False
    finally:
        # 清理临时文件
        os.unlink(temp_module_path)


def test_discovery_tracking():
    """测试模块发现跟踪机制"""
    print("\n=== 测试 4: 模块发现跟踪 ===")
    
    # 清理状态
    SpiderDiscoveryState.clear()
    
    # 标记模块为已发现
    test_module = 'test.module'
    SpiderDiscoveryState.mark_discovered(test_module)
    
    # 检查是否已发现
    if SpiderDiscoveryState.is_discovered(test_module):
        print(f"✅ 正确跟踪模块发现状态: {test_module}")
        return True
    else:
        print(f"❌ 未能跟踪模块发现状态: {test_module}")
        return False


def test_clear_state():
    """测试状态清理"""
    print("\n=== 测试 5: 状态清理 ===")
    
    # 添加一些状态
    SpiderDiscoveryState.mark_discovered('module1')
    SpiderDiscoveryState.add_discovery_error('module1: Error')
    
    # 清理
    SpiderDiscoveryState.clear()
    
    # 验证已清理
    if (not SpiderDiscoveryState.is_discovered('module1') and 
        len(SpiderDiscoveryState.get_discovery_errors()) == 0):
        print("✅ 状态清理成功")
        return True
    else:
        print("❌ 状态清理失败")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Spider Resolver 改进验证测试")
    print("=" * 60)
    
    results = []
    results.append(test_error_priority())
    results.append(test_duplicate_prevention())
    results.append(test_type_validation())
    results.append(test_discovery_tracking())
    results.append(test_clear_state())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
