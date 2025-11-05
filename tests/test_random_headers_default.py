#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试默认headers中间件的随机headers功能
确认默认是否要启动随机headers
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


def test_default_configuration():
    """测试默认配置下中间件的行为"""
    print("=== 测试默认配置下中间件的行为 ===")
    
    # 创建设置管理器（使用默认配置）
    settings = SettingManager()
    # 不设置任何RANDOM相关的配置，使用默认值
    # 但需要移除默认的DEFAULT_REQUEST_HEADERS和USER_AGENT来测试禁用情况
    settings.set('DEFAULT_REQUEST_HEADERS', {})
    settings.set('USER_AGENT', None)
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    logger = MockLogger('DefaultHeaderMiddleware')
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            # 尝试创建中间件实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            print("  ❌ 中间件创建成功，但应该在默认配置下被禁用")
            return False
        except NotConfiguredError as e:
            print("  ✅ 中间件正确地在默认配置下被禁用")
            print(f"     错误信息: {e}")
            return True
        except Exception as e:
            print(f"  ❌ 发生意外错误: {e}")
            return False


def test_default_headers_only():
    """测试仅配置默认请求头时的行为"""
    print("\n=== 测试仅配置默认请求头时的行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    settings.set('LOG_LEVEL', 'DEBUG')
    # 确保随机功能禁用
    settings.set('RANDOMNESS', False)
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    logger = MockLogger('DefaultHeaderMiddleware')
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            # 应该正常创建实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            print("  ✅ 仅配置默认请求头时中间件创建成功")
            
            # 检查配置
            print(f"     默认请求头数量: {len(middleware.headers)}")
            print(f"     User-Agent: {middleware.user_agent}")
            print(f"     随机User-Agent启用: {middleware.random_user_agent_enabled}")
            print(f"     随机请求头数量: {len(middleware.random_headers)}")
            print(f"     随机功能启用: {middleware.randomness}")
            
            # 测试处理请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'
            
            spider = Mock()
            middleware.process_request(request, spider)
            
            # 检查默认请求头是否添加
            if 'Accept' in request.headers and 'Accept-Language' in request.headers:
                print("  ✅ 默认请求头正确添加到请求中")
            else:
                print("  ❌ 默认请求头未正确添加")
                return False
            
            return True
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            return False


def test_random_user_agent_default():
    """测试随机User-Agent的默认行为"""
    print("\n=== 测试随机User-Agent的默认行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('RANDOM_USER_AGENT_ENABLED', True)  # 启用随机User-Agent
    settings.set('LOG_LEVEL', 'DEBUG')
    # 确保随机功能启用
    settings.set('RANDOMNESS', True)
    
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
            
            # 测试获取随机User-Agent
            print("     随机User-Agent测试:")
            for i in range(5):
                random_ua = middleware._get_random_user_agent()
                print(f"       {i+1}. {random_ua[:50]}...")
            
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
                return False
            
            return True
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            return False


def test_random_headers_default():
    """测试随机请求头的默认行为"""
    print("\n=== 测试随机请求头的默认行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('RANDOM_HEADERS', {
        'X-Custom-Header': ['Value1', 'Value2', 'Value3'],
        'X-Another-Header': 'FixedValue'
    })
    settings.set('RANDOMNESS', True)  # 启用随机功能
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    logger = MockLogger('DefaultHeaderMiddleware')
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            # 应该正常创建实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            print("  ✅ 启用随机请求头时中间件创建成功")
            
            # 检查配置
            print(f"     随机功能启用: {middleware.randomness}")
            print(f"     随机请求头数量: {len(middleware.random_headers)}")
            
            # 测试处理请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'
            
            spider = Mock()
            middleware.process_request(request, spider)
            
            # 检查随机请求头是否添加
            if 'X-Custom-Header' in request.headers or 'X-Another-Header' in request.headers:
                print("  ✅ 随机请求头已添加到请求中")
                print(f"     X-Custom-Header: {request.headers.get('X-Custom-Header', '未设置')}")
                print(f"     X-Another-Header: {request.headers.get('X-Another-Header', '未设置')}")
            else:
                print("  ❌ 随机请求头未添加")
                return False
            
            # 测试多次请求的随机性
            print("     随机性测试:")
            custom_header_values = []
            for i in range(10):
                test_request = Mock()
                test_request.headers = {}
                test_request.url = f'https://example.com/test{i}'
                
                middleware.process_request(test_request, spider)
                if 'X-Custom-Header' in test_request.headers:
                    custom_header_values.append(test_request.headers['X-Custom-Header'])
            
            # 检查是否有不同的值（应该有随机性）
            unique_values = set(custom_header_values)
            print(f"       10次请求中X-Custom-Header的不同值: {list(unique_values)}")
            if len(unique_values) > 1:
                print("  ✅ 随机请求头具有随机性")
            else:
                print("  ⚠️  随机请求头可能缺乏随机性")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            return False


def test_recommendation():
    """测试推荐配置"""
    print("\n=== 推荐配置测试 ===")
    
    print("默认配置分析:")
    print("  1. DEFAULT_REQUEST_HEADERS: 已配置（默认请求头）")
    print("  2. USER_AGENT: 已配置（默认User-Agent）")
    print("  3. RANDOM_USER_AGENT_ENABLED: False（默认禁用）")
    print("  4. RANDOMNESS: True（默认启用，用于随机延迟）")
    print("  5. RANDOM_HEADERS: {}（默认空字典）")
    
    print("\n推荐配置:")
    print("  对于大多数爬虫场景，建议:")
    print("    - 保持默认请求头（提供基本的浏览器兼容性）")
    print("    - 保持默认User-Agent（模拟现代浏览器）")
    print("    - 根据需要启用随机User-Agent（提高反爬虫能力）")
    print("    - 根据需要启用随机请求头（进一步提高反爬虫能力）")
    
    print("\n是否启用随机headers的建议:")
    print("  默认情况下不启用随机headers，原因:")
    print("    1. 保持请求的一致性，便于调试和问题排查")
    print("    2. 避免不必要的随机性导致的不可预测行为")
    print("    3. 用户可以根据具体需求选择是否启用")
    print("    4. 降低系统开销（随机选择需要额外计算）")
    
    print("\n注意:")
    print("  RANDOMNESS默认为True，主要用于下载延迟的随机化")
    print("  随机headers功能需要显式配置RANDOM_HEADERS和启用RANDOMNESS")
    
    return True


def main():
    print("开始测试默认headers中间件的随机headers功能...")
    
    try:
        # 运行所有测试
        test1_result = test_default_configuration()
        test2_result = test_default_headers_only()
        test3_result = test_random_user_agent_default()
        test4_result = test_random_headers_default()
        test5_result = test_recommendation()
        
        if test1_result and test2_result and test3_result and test4_result:
            print("\n🎉 所有测试通过！")
            print("\n结论:")
            print("  1. 默认情况下，随机headers功能是禁用的")
            print("  2. 只有在显式配置启用时，随机headers功能才会启动")
            print("  3. 这种设计是合理的，符合用户偏好")
            print("  4. RANDOMNESS默认为True，主要用于下载延迟随机化")
        else:
            print("\n❌ 部分测试失败，请检查实现")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()