#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门测试User-Agent随机性功能
"""

import sys
import os
import random
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.user_agents import get_random_user_agent


class MockLogger:
    """Mock Logger 类，用于测试日志输出"""
    def __init__(self, name, level=None):
        self.name = name
        self.level = level
        self.logs = []

    def debug(self, msg):
        self.logs.append(('debug', msg))

    def info(self, msg):
        self.logs.append(('info', msg))

    def warning(self, msg):
        self.logs.append(('warning', msg))

    def error(self, msg):
        self.logs.append(('error', msg))

    def isEnabledFor(self, level):
        return True


def test_user_agent_randomness():
    """测试User-Agent的随机性"""
    print("=== 测试User-Agent的随机性 ===")
    
    # 收集20次不同中间件实例生成的User-Agent
    ua_values = []
    
    for i in range(20):
        # 每次都创建新的设置和中间件实例
        settings = SettingManager()
        settings.set('DEFAULT_REQUEST_HEADERS', {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        settings.set('RANDOM_USER_AGENT_ENABLED', True)
        settings.set('LOG_LEVEL', 'DEBUG')
        settings.set('RANDOMNESS', True)
        
        crawler = Mock()
        crawler.settings = settings
        
        logger = MockLogger('DefaultHeaderMiddleware')
        with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
            try:
                middleware = DefaultHeaderMiddleware.create_instance(crawler)
                
                # 处理请求
                request = Mock()
                request.headers = {}
                request.url = f'https://example.com/test{i}'
                
                middleware.process_request(request, Mock())
                
                if 'User-Agent' in request.headers:
                    ua_values.append(request.headers['User-Agent'])
                    
            except Exception as e:
                print(f"  测试失败: {e}")
    
    # 分析随机性
    unique_uas = set(ua_values)
    print(f"  生成了 {len(ua_values)} 个User-Agent")
    print(f"  其中有 {len(unique_uas)} 个不同的User-Agent")
    print(f"  示例: {list(unique_uas)[:5]}")
    
    if len(unique_uas) > 1:
        print("  ✅ User-Agent具有良好的随机性")
        return True
    else:
        print("  ❌ User-Agent缺乏随机性")
        return False


def test_direct_function_randomness():
    """测试直接使用函数的随机性"""
    print("\n=== 测试直接使用函数的随机性 ===")
    
    # 收集20次调用的结果
    ua_values = []
    
    for i in range(20):
        ua = get_random_user_agent()
        ua_values.append(ua)
    
    # 分析随机性
    unique_uas = set(ua_values)
    print(f"  生成了 {len(ua_values)} 个User-Agent")
    print(f"  其中有 {len(unique_uas)} 个不同的User-Agent")
    print(f"  示例: {list(unique_uas)[:5]}")
    
    if len(unique_uas) > 1:
        print("  ✅ 直接调用函数具有良好的随机性")
        return True
    else:
        print("  ❌ 直接调用函数缺乏随机性")
        return False


def compare_approaches():
    """比较不同方法的优缺点"""
    print("\n=== 比较不同方法的优缺点 ===")
    
    print("方法1: 使用RANDOM_USER_AGENT_ENABLED")
    print("  优点:")
    print("    ✓ 内置大量真实User-Agent")
    print("    ✓ 支持设备类型分类")
    print("    ✓ 配置简单")
    print("    ✓ 专门优化")
    print("  缺点:")
    print("    ✗ 仅限User-Agent")
    
    print("\n方法2: 使用RANDOM_HEADERS")
    print("  优点:")
    print("    ✓ 可以为任意头部添加随机值")
    print("    ✓ 更加灵活")
    print("    ✓ 适用于多种场景")
    print("  缺点:")
    print("    ✗ 需要用户提供值列表")
    print("    ✗ 配置相对复杂")
    
    print("\n方法3: 直接使用get_random_user_agent()")
    print("  优点:")
    print("    ✓ 最直接")
    print("    ✓ 可编程控制")
    print("    ✓ 无需中间件")
    print("  缺点:")
    print("    ✗ 需要手动实现")
    print("    ✗ 不如中间件方便")


def main():
    print("开始测试User-Agent随机性功能...")
    
    try:
        # 运行所有测试
        test1_result = test_user_agent_randomness()
        test2_result = test_direct_function_randomness()
        compare_approaches()
        
        if test1_result and test2_result:
            print("\n🎉 User-Agent随机性测试通过！")
            print("\n结论:")
            print("  1. 现有的User-Agent功能具有良好的随机性")
            print("  2. 可以满足大多数反爬虫需求")
            print("  3. RANDOM_HEADERS参数提供了额外的灵活性，但不是必需的")
        else:
            print("\n❌ User-Agent随机性测试失败")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()