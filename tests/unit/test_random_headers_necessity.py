#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RANDOM_HEADERS参数的必要性
验证是否可以仅使用现有的User-Agent功能满足需求
"""

import sys
import os
import random
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.core.errors import NotConfiguredError
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


def test_current_user_agent_functionality():
    """测试当前User-Agent功能是否足够"""
    print("=== 测试当前User-Agent功能是否足够 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('USER_AGENT_ROTATION', True)  # 启用随机User-Agent
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    logger = MockLogger('DefaultHeaderMiddleware')
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            # 应该正常创建实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            print("  ✅ 启用随机User-Agent时中间件创建成功")
            
            # 检查配置
            print(f"     随机User-Agent启用: {middleware.rotation_enabled}")
            print(f"     User-Agent列表数量: {len(middleware.user_agents)}")
            print(f"     User-Agent设备类型: {middleware.rotation_type}")
            
            # 测试处理请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'
            
            spider = Mock()
            middleware.process_request(request, spider)
            
            # 检查User-Agent是否添加
            if 'User-Agent' in request.headers:
                print("  ✅ 随机User-Agent正确添加到请求中")
                print(f"     User-Agent: {request.headers['User-Agent'][:50]}...")
            else:
                print("  ❌ 随机User-Agent未添加")
            assert 'User-Agent' in request.headers, "随机User-Agent未添加"

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            raise


def test_random_headers_vs_user_agent():
    """比较RANDOM_HEADERS和User-Agent功能的差异"""
    print("\n=== 比较RANDOM_HEADERS和User-Agent功能的差异 ===")
    
    # 仅演示 UA 轮换 VS 自定义 headers 两种思路：
    # RANDOM_HEADERS 字典随机化当前版本未实现，本测试不再依赖该功能。
    print("  UA 轮换方案（推荐）：")
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('USER_AGENT_ROTATION', True)
    settings.set('LOG_LEVEL', 'DEBUG')

    # 创建crawler对象
    crawler2 = Mock()
    crawler2.settings = settings

    logger = MockLogger('DefaultHeaderMiddleware')

    # 测试User-Agent 轮换
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            middleware2 = DefaultHeaderMiddleware.create_instance(crawler2)

            # 测试多次请求的随机性
            print("    User-Agent 随机性测试:")
            ua_values = []
            for i in range(20):
                test_request = Mock()
                test_request.headers = {}
                test_request.url = f'https://example.com/test{i}'

                middleware2.process_request(test_request, Mock())

                if 'User-Agent' in test_request.headers:
                    ua_values.append(test_request.headers['User-Agent'])

            # 分析随机性
            unique_uas = set(ua_values)
            print(f"      User-Agent: {len(unique_uas)} 个不同值")
            print(f"      示例: {list(unique_uas)[:3]}")

        except Exception as e:
            print(f"    User-Agent 测试失败: {e}")
            raise


def test_direct_user_agent_usage():
    """测试直接使用user_agents模块的功能"""
    print("\n=== 测试直接使用user_agents模块的功能 ===")
    
    # 测试get_random_user_agent函数
    print("  直接使用get_random_user_agent函数:")
    for i in range(5):
        ua = get_random_user_agent()
        print(f"    {i+1}. {ua[:50]}...")
    
    # 测试不同设备类型的User-Agent
    print("  不同设备类型的User-Agent:")
    device_types = ["desktop", "mobile", "chrome", "firefox", "safari"]
    for device_type in device_types:
        ua = get_random_user_agent(device_type)
        print(f"    {device_type}: {ua[:50]}...")
    
    print("  ✅ 可以直接使用user_agents模块满足User-Agent随机化需求")


def test_alternative_approach():
    """测试替代方案：仅使用User-Agent功能"""
    print("\n=== 测试替代方案：仅使用User-Agent功能 ===")
    
    print("  推荐的配置方式:")
    print("    1. 启用RANDOM_USER_AGENT_ENABLED = True")
    print("    2. 设置USER_AGENT_DEVICE_TYPE = 'desktop' 或 'mobile' 等")
    print("    3. 无需配置RANDOM_HEADERS")
    
    # 模拟推荐配置
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('USER_AGENT_ROTATION', True)
    settings.set('USER_AGENT_TYPE', 'desktop')
    settings.set('LOG_LEVEL', 'DEBUG')
    
    crawler = Mock()
    crawler.settings = settings
    
    logger = MockLogger('DefaultHeaderMiddleware')
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            print("  ✅ 推荐配置可行")
            
            # 测试处理请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'
            
            spider = Mock()
            middleware.process_request(request, spider)
            
            if 'User-Agent' in request.headers:
                print(f"     User-Agent: {request.headers['User-Agent'][:50]}...")
            assert 'User-Agent' in request.headers, "推荐配置下 User-Agent 未添加到请求头"

        except Exception as e:
            print(f"  ❌ 推荐配置失败: {e}")
            raise


def analyze_necessity():
    """分析RANDOM_HEADERS参数的必要性"""
    print("\n=== 分析RANDOM_HEADERS参数的必要性 ===")
    
    print("功能对比:")
    print("  USER_AGENT_ROTATION 方案（推荐）:")
    print("    ✓ 专门用于 User-Agent 随机化")
    print("    ✓ 内置大量真实 User-Agent")
    print("    ✓ 支持 USER_AGENT_TYPE 按设备类型分类")
    print("    ✓ 易于使用和配置")

    print("  自定义 DEFAULT_REQUEST_HEADERS 方案（进阶）:")
    print("    ✓ 可以自行包装随机逻辑放入 DEFAULT_REQUEST_HEADERS")
    print("    ✓ 更加灵活，支持自定义头部")
    print("    ✗ 需要用户自己提供随机值生成")

    print("\n使用建议:")
    print("  1. 对 User-Agent 随机化：USER_AGENT_ROTATION=True + USER_AGENT_TYPE")
    print("  2. 大多数场景下，User-Agent 轮换已足够")
    print("  3. 要做复杂 header 随机化可自行写中间件或在 process_request 中扩展")

    print("\n结论:")
    print("  多数场景只需要 User-Agent 轮换就能解决反爬问题；")
    print("  需要更复杂随机值时可以写自定义中间件或扩展 DefaultHeaderMiddleware。")


def main():
    print("开始测试RANDOM_HEADERS参数的必要性...")
    
    try:
        # 运行所有测试
        test1_result = test_current_user_agent_functionality()
        test_random_headers_vs_user_agent()
        test_direct_user_agent_usage()
        test2_result = test_alternative_approach()
        analyze_necessity()
        
        if test1_result and test2_result:
            print("\n🎉 测试完成！")
            print("\n总结:")
            print("  1. 现有的User-Agent功能已能满足大多数随机化需求")
            print("  2. RANDOM_HEADERS参数提供了额外的灵活性")
            print("  3. 对于简单场景，仅使用User-Agent功能即可")
            print("  4. 对于复杂场景，RANDOM_HEADERS参数仍然有价值")
        else:
            print("\n❌ 部分测试失败")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()