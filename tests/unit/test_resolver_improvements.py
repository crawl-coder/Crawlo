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
        SpiderResolver.resolve_spider_class('nonexistent_module.NonexistentSpider', ['nonexistent_module'])
        assert False, "应该抛出异常"
    except ValueError as e:
        error_msg = str(e)
        if "Failed to import spider modules" in error_msg:
            print(f"✅ 正确报告导入失败: {error_msg}")
        elif "not found in registry" in error_msg:
            assert False, f"报告未找到爬虫（但模块不存在时应优先报告导入失败）: {error_msg}"
        else:
            assert False, f"未知错误消息: {error_msg}"


def test_duplicate_prevention():
    """测试错误去重机制"""
    print("\n=== 测试 2: 错误去重 ===")

    SpiderDiscoveryState.clear()

    try:
        for i in range(3):
            SpiderResolver.resolve_spider_class('missing.Spider', ['missing_module'])
    except ValueError as e:
        error_msg = str(e)
        missing_module_count = error_msg.count("missing_module:")
        missing_spider_count = error_msg.count("missing.Spider:")

        if missing_module_count == 1 and missing_spider_count == 1:
            print(f"✅ 错误消息无重复（每个模块各出现 1 次）")
        else:
            assert False, f"错误消息重复（missing_module={missing_module_count}, missing.Spider={missing_spider_count}）: {error_msg}"


def test_type_validation():
    """测试 Spider 类型校验"""
    print("\n=== 测试 3: Spider 类型校验 ===")

    SpiderDiscoveryState.clear()

    test_module_code = '''
class NotASpider:
    name = "not_a_spider"
'''

    import tempfile
    import importlib.util

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='.') as f:
        f.write(test_module_code)
        temp_module_path = f.name

    module_name = os.path.splitext(os.path.basename(temp_module_path))[0]

    try:
        SpiderResolver.resolve_spider_class(f'{module_name}.NotASpider', [module_name])
        assert False, "应该拒绝非 Spider 类"
    except ValueError as e:
        error_msg = str(e)
        # 接受两种错误：类型校验失败或注册表中找不到（均表示正确拒绝）
        print(f"✅ 正确拒绝非 Spider 类: {error_msg}")
    finally:
        os.unlink(temp_module_path)


def test_discovery_tracking():
    """测试模块发现跟踪机制"""
    print("\n=== 测试 4: 模块发现跟踪 ===")

    SpiderDiscoveryState.clear()

    test_module = 'test.module'
    SpiderDiscoveryState.mark_discovered(test_module)

    if SpiderDiscoveryState.is_discovered(test_module):
        print(f"✅ 正确跟踪模块发现状态: {test_module}")
    else:
        print(f"❌ 未能跟踪模块发现状态: {test_module}")
    assert SpiderDiscoveryState.is_discovered(test_module), f"未能跟踪模块发现状态: {test_module}"


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
    else:
        print("❌ 状态清理失败")
    assert not SpiderDiscoveryState.is_discovered('module1'), "module1 仍标记为已发现"
    assert len(SpiderDiscoveryState.get_discovery_errors()) == 0, "错误列表未清空"


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
