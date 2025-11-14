#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试中间件User-Agent随机性问题
"""

import sys
import os
import random
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.data.user_agents import get_user_agents


class MockLogger:
    """Mock Logger 类，用于测试日志输出"""
    def __init__(self, name, level=None):
        self.name = name
        self.level = level
        self.logs = []

    def debug(self, msg):
        self.logs.append(('debug', msg))
        print(f"DEBUG: {msg}")

    def info(self, msg):
        self.logs.append(('info', msg))

    def warning(self, msg):
        self.logs.append(('warning', msg))

    def error(self, msg):
        self.logs.append(('error', msg))

    def isEnabledFor(self, level):
        return True


def debug_middleware_initialization():
    """调试中间件初始化过程"""
    print("=== 调试中间件初始化过程 ===")
    
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
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        
        print(f"随机User-Agent启用: {middleware.random_user_agent_enabled}")
        print(f"User-Agent列表数量: {len(middleware.user_agents)}")
        print(f"User-Agent设备类型: {middleware.user_agent_device_type}")
        
        # 检查前几个User-Agent
        print("前5个User-Agent:")
        for i, ua in enumerate(middleware.user_agents[:5]):
            print(f"  {i+1}. {ua[:50]}...")
        
        # 测试_get_random_user_agent方法
        print("\n测试_get_random_user_agent方法:")
        for i in range(10):
            ua = middleware._get_random_user_agent()
            print(f"  {i+1}. {ua[:50]}...")


def test_multiple_middleware_instances():
    """测试多个中间件实例的随机性"""
    print("\n=== 测试多个中间件实例的随机性 ===")
    
    ua_values = []
    
    for i in range(10):
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
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            
            # 获取随机User-Agent
            ua = middleware._get_random_user_agent()
            if ua:
                ua_values.append(ua)
                print(f"  实例{i+1}: {ua[:50]}...")
    
    unique_uas = set(ua_values)
    print(f"\n生成了 {len(ua_values)} 个User-Agent，其中 {len(unique_uas)} 个不同")


def check_user_agents_module():
    """检查user_agents模块"""
    print("\n=== 检查user_agents模块 ===")
    
    # 获取不同类型的User-Agent
    device_types = ["all", "desktop", "mobile", "chrome", "firefox"]
    
    for device_type in device_types:
        uas = get_user_agents(device_type)
        print(f"{device_type}类型User-Agent数量: {len(uas)}")
        if uas:
            print(f"  示例: {uas[0][:50]}...")


def main():
    print("开始调试中间件User-Agent随机性问题...")
    
    try:
        debug_middleware_initialization()
        test_multiple_middleware_instances()
        check_user_agents_module()
        
        print("\n调试完成！")
        
    except Exception as e:
        print(f"\n调试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()