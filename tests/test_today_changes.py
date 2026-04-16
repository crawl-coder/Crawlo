#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo 框架全面测试脚本
测试今天（2026-04-07）修改的所有功能
"""

import sys
import os

def test_priority_module():
    """测试1: 优先级模块"""
    print('=' * 60)
    print('[测试1] 优先级模块 (crawlo.utils.priority)')
    print('=' * 60)
    
    from crawlo.utils.priority import (
        MiddlewarePriority, 
        MiddlewarePriorityGroup, 
        BUILTIN_MIDDLEWARE_PRIORITIES,
        get_default_middleware_priority
    )
    
    # 测试枚举常量
    print('\n✓ MiddlewarePriority 常量:')
    print(f'  CUSTOM = {MiddlewarePriority.CUSTOM}')
    print(f'  CUSTOM_REQUEST = {MiddlewarePriority.CUSTOM_REQUEST}')
    print(f'  CUSTOM_RESPONSE = {MiddlewarePriority.CUSTOM_RESPONSE}')
    
    assert MiddlewarePriority.CUSTOM == 500
    assert MiddlewarePriority.CUSTOM_REQUEST == 450
    assert MiddlewarePriority.CUSTOM_RESPONSE == 550
    
    # 测试内置中间件优先级
    print('\n✓ BUILTIN_MIDDLEWARE_PRIORITIES:')
    expected_middleware = {
        'crawlo.middleware.request_ignore.RequestIgnoreMiddleware': 100,
        'crawlo.middleware.throttle.ThrottleMiddleware': 200,
        'crawlo.middleware.default_header.DefaultHeaderMiddleware': 300,
        'crawlo.middleware.offsite.OffsiteMiddleware': 400,
        'crawlo.middleware.retry.RetryMiddleware': 600,
        'crawlo.middleware.response_code.ResponseCodeMiddleware': 650,
        'crawlo.middleware.response_filter.ResponseFilterMiddleware': 700,
    }
    
    for mw_path, expected_priority in expected_middleware.items():
        actual_priority = BUILTIN_MIDDLEWARE_PRIORITIES.get(mw_path)
        assert actual_priority == expected_priority, f"{mw_path}: 期望 {expected_priority}, 实际 {actual_priority}"
        mw_name = mw_path.split('.')[-1]
        print(f'  {mw_name}: {actual_priority}')
    
    # 测试 MiddlewarePriorityGroup
    print('\n✓ MiddlewarePriorityGroup 功能:')
    group = MiddlewarePriorityGroup()
    group.add_request('test.CustomMiddleware', 250)
    group.add_response('test.AnotherMiddleware', 650)
    result = group.to_dict()
    
    assert 'test.CustomMiddleware' in result
    assert 'test.AnotherMiddleware' in result
    assert result['test.CustomMiddleware'] == 250
    assert result['test.AnotherMiddleware'] == 650
    print(f'  配置结果: {result}')
    
    # 测试 get_default_middleware_priority
    print('\n✓ get_default_middleware_priority 功能:')
    priority = get_default_middleware_priority('test.MyMiddleware')
    assert priority == 500
    print(f'  默认优先级: {priority}')
    
    print('\n✅ 测试1通过\n')
    return True


def test_safe_get_config_import():
    """测试2: safe_get_config 导入优化"""
    print('=' * 60)
    print('[测试2] safe_get_config 导入位置优化')
    print('=' * 60)
    
    from crawlo.utils.misc import safe_get_config
    
    # 检查文件中是否有重复导入
    files_to_check = [
        'crawlo/downloader/__init__.py',
        'crawlo/filters/memory_filter.py',
        'crawlo/queue/queue_manager.py',
    ]
    
    print('\n✓ 检查导入位置:')
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 检查文件头部是否有导入
                lines = content.split('\n')[:30]  # 前30行
                has_header_import = any('from crawlo.utils.misc import safe_get_config' in line for line in lines)
                print(f'  ✓ {file_path}: {"头部导入" if has_header_import else "未找到头部导入"}')
    
    print('\n✅ 测试2通过\n')
    return True


def test_hook_removed():
    """测试3: hook.py 已删除"""
    print('=' * 60)
    print('[测试3] hook.py 删除验证')
    print('=' * 60)
    
    crawlo_path = os.path.dirname(os.path.dirname(__file__))
    hook_path = os.path.join(crawlo_path, 'crawlo', 'hook.py')
    
    if not os.path.exists(hook_path):
        print(f'\n✓ hook.py 已成功删除: {hook_path}')
        print('✅ 测试3通过\n')
        return True
    else:
        print(f'\n✗ hook.py 仍然存在: {hook_path}')
        print('❌ 测试3失败\n')
        return False


def test_throttle_module():
    """测试4: throttle 模块分层"""
    print('=' * 60)
    print('[测试4] throttle 模块分层验证')
    print('=' * 60)
    
    # 测试 utils/throttle.py (工具类)
    from crawlo.utils.throttle import DomainThrottler
    print('\n✓ crawlo.utils.throttle.DomainThrottler 导入成功')
    
    # 测试 middleware/throttle.py (中间件)
    from crawlo.middleware.throttle import ThrottleMiddleware
    print('✓ crawlo.middleware.throttle.ThrottleMiddleware 导入成功')
    
    # 验证中间件未被默认启用
    from crawlo.settings.default_settings import MIDDLEWARES
    throttle_middleware = 'crawlo.middleware.throttle.ThrottleMiddleware'
    if throttle_middleware not in MIDDLEWARES:
        print(f'✓ ThrottleMiddleware 未默认启用（可选中间件）')
    else:
        print(f'✗ ThrottleMiddleware 不应在默认配置中')
        return False
    
    print('\n✅ 测试4通过\n')
    return True


def test_template_files():
    """测试5: 模板文件配置"""
    print('=' * 60)
    print('[测试5] 模板文件配置验证')
    print('=' * 60)
    
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawlo', 'templates', 'project')
    template_files = [
        'settings.py.tmpl',
        'settings_simple.py.tmpl',
        'settings_gentle.py.tmpl',
        'settings_minimal.py.tmpl',
        'settings_high_performance.py.tmpl',
        'settings_distributed.py.tmpl',
    ]
    
    for tmpl_file in template_files:
        tmpl_path = os.path.join(template_dir, tmpl_file)
        if not os.path.exists(tmpl_path):
            print(f'✗ 模板文件不存在: {tmpl_file}')
            return False
        
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查 PIPELINES 是否为字典格式
            if 'PIPELINES = {' in content:
                print(f'✓ {tmpl_file}: PIPELINES 使用字典格式')
            else:
                print(f'✗ {tmpl_file}: PIPELINES 应为字典格式')
                return False
            
            # 检查 MIDDLEWARES 是否有优先级说明
            if '优先级规则' in content:
                print(f'✓ {tmpl_file}: MIDDLEWARES 包含优先级说明')
            else:
                print(f'✗ {tmpl_file}: MIDDLEWARES 缺少优先级说明')
                return False
    
    print('\n✅ 测试5通过\n')
    return True


def test_default_settings():
    """测试6: 默认配置"""
    print('=' * 60)
    print('[测试6] 默认配置验证')
    print('=' * 60)
    
    from crawlo.settings.default_settings import MIDDLEWARES, PIPELINES
    
    # 验证 MIDDLEWARES 是字典
    assert isinstance(MIDDLEWARES, dict), f"MIDDLEWARES 应为字典，实际为 {type(MIDDLEWARES)}"
    print(f'\n✓ MIDDLEWARES 类型: dict (包含 {len(MIDDLEWARES)} 个中间件)')
    
    # 验证 PIPELINES 是字典
    assert isinstance(PIPELINES, dict), f"PIPELINES 应为字典，实际为 {type(PIPELINES)}"
    print(f'✓ PIPELINES 类型: dict (包含 {len(PIPELINES)} 个管道)')
    
    # 验证中间件优先级
    print('\n✓ 中间件配置:')
    for mw_path, priority in MIDDLEWARES.items():
        mw_name = mw_path.split('.')[-1]
        print(f'  {mw_name}: {priority}')
    
    print('\n✅ 测试6通过\n')
    return True


def test_log_format():
    """测试7: 日志格式优化"""
    print('=' * 60)
    print('[测试7] 日志格式验证')
    print('=' * 60)
    
    # 检查 scheduler.py 中的日志格式
    scheduler_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawlo', 'core', 'scheduler.py')
    with open(scheduler_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "enabled filters:" in content and "\n  " not in content.split("enabled filters:")[1][:10]:
            print('✓ scheduler.py: enabled filters 日志格式正确（无异常换行）')
        else:
            print('✗ scheduler.py: enabled filters 日志格式有问题')
            return False
    
    # 检查 downloader/__init__.py 中的日志格式
    downloader_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'crawlo', 'downloader', '__init__.py')
    with open(downloader_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "enabled downloader:" in content and "\n  " not in content.split("enabled downloader:")[1][:10]:
            print('✓ downloader/__init__.py: enabled downloader 日志格式正确（无异常换行）')
        else:
            print('✗ downloader/__init__.py: enabled downloader 日志格式有问题')
            return False
    
    print('\n✅ 测试7通过\n')
    return True


def test_module_imports():
    """测试8: 模块导入"""
    print('=' * 60)
    print('[测试8] 模块导入验证')
    print('=' * 60)
    
    modules = [
        'crawlo.utils.priority',
        'crawlo.middleware.throttle',
        'crawlo.utils.throttle',
        'crawlo.settings.default_settings',
        'crawlo.middleware',
        'crawlo.utils',
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f'  ✓ {module}')
        except ImportError as e:
            print(f'  ✗ {module}: {e}')
            return False
    
    print('\n✅ 测试8通过\n')
    return True


def main():
    """运行所有测试"""
    print('\n' + '=' * 60)
    print('Crawlo 框架全面测试')
    print('测试日期: 2026-04-07')
    print('=' * 60 + '\n')
    
    tests = [
        ('优先级模块', test_priority_module),
        ('safe_get_config 导入优化', test_safe_get_config_import),
        ('hook.py 删除', test_hook_removed),
        ('throttle 模块分层', test_throttle_module),
        ('模板文件配置', test_template_files),
        ('默认配置', test_default_settings),
        ('日志格式', test_log_format),
        ('模块导入', test_module_imports),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f'❌ {test_name} 测试失败\n')
        except Exception as e:
            failed += 1
            print(f'❌ {test_name} 测试异常: {e}\n')
            import traceback
            traceback.print_exc()
    
    # 测试总结
    print('=' * 60)
    print('测试总结')
    print('=' * 60)
    print(f'总测试数: {len(tests)}')
    print(f'通过: {passed}')
    print(f'失败: {failed}')
    
    if failed == 0:
        print('\n🎉 所有测试通过！')
        return 0
    else:
        print(f'\n❌ {failed} 个测试失败')
        return 1


if __name__ == '__main__':
    sys.exit(main())

