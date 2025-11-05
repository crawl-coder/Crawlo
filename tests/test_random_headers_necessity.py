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
from crawlo.exceptions import NotConfiguredError
from crawlo.data.user_agents import get_random_user_agent


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
    settings.set('RANDOM_USER_AGENT_ENABLED', True)  # 启用随机User-Agent
    settings.set('LOG_LEVEL', 'DEBUG')
    settings.set('RANDOMNESS', True)  # 启用随机功能
    
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
            print(f"     随机User-Agent启用: {middleware.random_user_agent_enabled}")
            print(f"     User-Agent列表数量: {len(middleware.user_agents)}")
            print(f"     User-Agent设备类型: {middleware.user_agent_device_type}")
            
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
                return True
            else:
                print("  ❌ 随机User-Agent未添加")
                return False
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            return False


def test_random_headers_vs_user_agent():
    """比较RANDOM_HEADERS和User-Agent功能的差异"""
    print("\n=== 比较RANDOM_HEADERS和User-Agent功能的差异 ===")
    
    # 测试RANDOM_HEADERS功能
    print("  RANDOM_HEADERS功能:")
    settings1 = SettingManager()
    settings1.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings1.set('RANDOM_HEADERS', {
        'X-Custom-Header': ['Value1', 'Value2', 'Value3'],
        'X-Another-Header': 'FixedValue',
        'X-Random-Header': ['A', 'B', 'C', 'D']
    })
    settings1.set('RANDOMNESS', True)
    settings1.set('LOG_LEVEL', 'DEBUG')
    
    # 测试User-Agent功能
    print("  User-Agent功能:")
    settings2 = SettingManager()
    settings2.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings2.set('RANDOM_USER_AGENT_ENABLED', True)
    settings2.set('LOG_LEVEL', 'DEBUG')
    settings2.set('RANDOMNESS', True)
    
    # 创建crawler对象
    crawler1 = Mock()
    crawler1.settings = settings1
    crawler2 = Mock()
    crawler2.settings = settings2
    
    logger = MockLogger('DefaultHeaderMiddleware')
    
    # 测试RANDOM_HEADERS
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            middleware1 = DefaultHeaderMiddleware.create_instance(crawler1)
            
            # 测试多次请求的随机性
            print("    RANDOM_HEADERS随机性测试:")
            header_values = {}
            for i in range(20):
                test_request = Mock()
                test_request.headers = {}
                test_request.url = f'https://example.com/test{i}'
                
                middleware1.process_request(test_request, Mock())
                
                # 收集各种随机头部的值
                for header in ['X-Custom-Header', 'X-Another-Header', 'X-Random-Header']:
                    if header in test_request.headers:
                        if header not in header_values:
                            header_values[header] = []
                        header_values[header].append(test_request.headers[header])
            
            # 分析随机性
            for header, values in header_values.items():
                unique_values = set(values)
                print(f"      {header}: {len(unique_values)} 个不同值 ({list(unique_values)[:3]}...)")
            
        except Exception as e:
            print(f"    RANDOM_HEADERS测试失败: {e}")
    
    # 测试User-Agent
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            middleware2 = DefaultHeaderMiddleware.create_instance(crawler2)
            
            # 测试多次请求的随机性
            print("    User-Agent随机性测试:")
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
            print(f"    User-Agent测试失败: {e}")


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
    settings.set('RANDOM_USER_AGENT_ENABLED', True)
    settings.set('USER_AGENT_DEVICE_TYPE', 'desktop')
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
            
            return True
        except Exception as e:
            print(f"  ❌ 推荐配置失败: {e}")
            return False


def analyze_necessity():
    """分析RANDOM_HEADERS参数的必要性"""
    print("\n=== 分析RANDOM_HEADERS参数的必要性 ===")
    
    print("功能对比:")
    print("  User-Agent功能:")
    print("    ✓ 专门用于User-Agent随机化")
    print("    ✓ 内置大量真实User-Agent")
    print("    ✓ 支持按设备类型分类")
    print("    ✓ 易于使用和配置")
    
    print("  RANDOM_HEADERS功能:")
    print("    ✓ 可以为任意头部添加随机值")
    print("    ✓ 更加灵活，支持自定义头部")
    print("    ✓ 适用于需要随机化其他头部的场景")
    print("    ✗ 需要用户自己提供头部值列表")
    
    print("\n使用建议:")
    print("  1. 对于User-Agent随机化：使用RANDOM_USER_AGENT_ENABLED")
    print("  2. 对于其他头部随机化：使用RANDOM_HEADERS")
    print("  3. 大多数场景下，User-Agent功能已足够")
    print("  4. RANDOM_HEADERS适用于特殊需求场景")
    
    print("\n结论:")
    print("  RANDOM_HEADERS参数不是必需的，但对于需要随机化其他头部的场景很有用")
    print("  现有的User-Agent功能已经可以满足大多数反爬虫需求")


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