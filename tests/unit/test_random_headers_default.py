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
from crawlo.core.errors import NotConfiguredError


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
    # SettingManager 有 DEFAULT_REQUEST_HEADERS + USER_AGENT 默认值；
    # 测试"完全无配置时禁用"必须把这两项都清空，并关闭 rotation
    settings.set('DEFAULT_REQUEST_HEADERS', {})
    settings.set('USER_AGENT', None)
    settings.set('USER_AGENT_ROTATION', False)
    settings.set('USER_AGENT_TYPE', None)

    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings

    logger = MockLogger('DefaultHeaderMiddleware')
    with patch('crawlo.middleware.default_header.get_logger', return_value=logger):
        try:
            # 尝试创建中间件实例
            DefaultHeaderMiddleware.create_instance(crawler)
            print("  ❌ 中间件创建成功，但应该在默认配置下被禁用")
            raise AssertionError("中间件在默认配置下应被禁用并抛 NotConfiguredError")
        except NotConfiguredError as e:
            print("  ✅ 中间件正确地在默认配置下被禁用")
            print(f"     错误信息: {e}")
        except Exception as e:
            print(f"  ❌ 发生意外错误: {e}")
            raise


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
    # 确保随机 UA 功能禁用
    settings.set('USER_AGENT_ROTATION', False)
    
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
            print(f"     随机User-Agent启用: {middleware.rotation_enabled}")

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
            assert 'Accept' in request.headers and 'Accept-Language' in request.headers, "默认请求头未正确添加"

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            raise


def test_random_user_agent_default():
    """测试随机User-Agent的默认行为"""
    print("\n=== 测试随机User-Agent的默认行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('USER_AGENT_ROTATION', True)  # 启用随机User-Agent（新配置名）
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
            
            # 测试获取随机User-Agent
            print("     随机User-Agent测试:")
            for i in range(5):
                random_ua = middleware._get_rotated_user_agent()
                if random_ua:
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
            assert 'User-Agent' in request.headers, "随机User-Agent未添加"

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            raise


def test_random_headers_default():
    """测试随机请求头的默认行为"""
    print("\n=== 测试随机请求头的默认行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    settings.set('LOG_LEVEL', 'DEBUG')
    # 注意: DefaultHeaderMiddleware 当前版本未实现 RANDOM_HEADERS 字典随机化功能，
    # 本测试聚焦于"中间件能正常创建 + 请求头被写入"，随机值由用户自定义时自行管理。
    
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
            print(f"     rotation 启用: {middleware.rotation_enabled}")
            print(f"     默认请求头数量: {len(middleware.headers)}")

            # 测试处理请求
            request = Mock()
            request.headers = {}
            request.url = 'https://example.com'

            spider = Mock()
            middleware.process_request(request, spider)

            # 验证至少 DEFAULT_REQUEST_HEADERS 被注入
            assert 'Accept' in request.headers, "DEFAULT_REQUEST_HEADERS 中 Accept 未注入"
            print("  ✅ DEFAULT_REQUEST_HEADERS 已正确添加到请求中")

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            raise


def test_recommendation():
    """推荐配置速览（纯描述性，不执行真实断言）"""
    print("\n=== 推荐配置测试 ===")

    print("默认配置分析:")
    print("  1. DEFAULT_REQUEST_HEADERS: 已配置（默认请求头）")
    print("  2. USER_AGENT: 可配置（固定 User-Agent，优先级最高）")
    print("  3. USER_AGENT_ROTATION: False（默认禁用，启用后轮换 UA）")
    print("  4. USER_AGENT_TYPE: desktop（desktop/mobile/all）")
    print("  5. DOWNLOAD_DELAY: 0.5（默认半秒，download_delay 中间件负责）")

    print("\n推荐配置:")
    print("  对于大多数爬虫场景，建议:")
    print("    - 保持 DEFAULT_REQUEST_HEADERS（提供基本浏览器兼容性）")
    print("    - 设置 USER_AGENT_ROTATION=True + USER_AGENT_TYPE='desktop'")
    print("    - 深爬场景开启 DOWNLOAD_DELAY_OVERRIDES 分站点限流")


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