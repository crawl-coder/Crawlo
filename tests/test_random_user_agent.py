#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试随机User-Agent功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.data.user_agents import get_random_user_agent
from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.settings.setting_manager import SettingManager


def test_random_user_agent_function():
    """测试随机User-Agent函数"""
    print("=== 随机User-Agent函数测试 ===")
    
    # 测试各种设备类型的随机User-Agent
    device_types = ["desktop", "mobile", "all", "chrome", "firefox", "safari", "edge", "opera"]
    
    for device_type in device_types:
        print(f"\n{device_type}类型随机User-Agent:")
        for i in range(3):
            ua = get_random_user_agent(device_type)
            print(f"  {i+1}. {ua}")
    
    print()


def test_default_header_middleware_with_random_ua():
    """测试DefaultHeaderMiddleware与随机User-Agent"""
    print("=== DefaultHeaderMiddleware与随机User-Agent测试 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set("LOG_LEVEL", "INFO")
    settings.set("RANDOM_USER_AGENT_ENABLED", True)
    settings.set("USER_AGENT_DEVICE_TYPE", "all")
    # 添加一个默认请求头以启用中间件
    settings.set("DEFAULT_REQUEST_HEADERS", {"Accept": "text/html"})
    
    # 创建中间件实例
    middleware = DefaultHeaderMiddleware(settings, "INFO")
    
    print(f"随机User-Agent功能已启用: {middleware.random_user_agent_enabled}")
    print(f"User-Agent设备类型: {middleware.user_agent_device_type}")
    print(f"内置User-Agent列表数量: {len(middleware.user_agents)}")
    
    # 测试获取随机User-Agent
    print("\n随机User-Agent测试:")
    for i in range(5):
        random_ua = middleware._get_random_user_agent()
        print(f"  {i+1}. {random_ua}")
    
    print()


def main():
    """主测试函数"""
    print("开始测试随机User-Agent功能...\n")
    
    test_random_user_agent_function()
    test_default_header_middleware_with_random_ua()
    
    print("所有测试完成!")


if __name__ == "__main__":
    main()