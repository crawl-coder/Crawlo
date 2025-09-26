#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
随机User-Agent来源演示
展示当RANDOM_USER_AGENT_ENABLED = True时，随机User-Agent的来源
"""

from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.exceptions import NotConfiguredError
from unittest.mock import Mock


def demo_random_user_agent_sources():
    """演示随机User-Agent的来源"""
    print("=== 随机User-Agent来源演示 ===")
    
    # 测试不同设备类型的User-Agent数量
    device_types = ["all", "desktop", "mobile", "chrome", "firefox", "safari", "edge", "opera"]
    
    for device_type in device_types:
        # 创建设置管理器
        settings = SettingManager()
        settings.set('RANDOM_USER_AGENT_ENABLED', True)
        settings.set('USER_AGENT_DEVICE_TYPE', device_type)
        
        # 创建一个模拟的crawler对象
        crawler = Mock()
        crawler.settings = settings
        
        try:
            # 创建中间件实例
            middleware = DefaultHeaderMiddleware.create_instance(crawler)
            print(f"{device_type:8} 类型 User-Agent 数量: {len(middleware.user_agents)}")
        except NotConfiguredError as e:
            print(f"{device_type:8} 类型配置错误: {e}")
    
    print()
    
    # 演示默认情况下的User-Agent来源
    print("=== 默认情况下的User-Agent来源 ===")
    settings = SettingManager()
    settings.set('RANDOM_USER_AGENT_ENABLED', True)
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print(f"默认类型 User-Agent 数量: {len(middleware.user_agents)}")
        print(f"默认设备类型: {middleware.user_agent_device_type}")
        print()
        
        # 显示前10个User-Agent示例
        print("前10个User-Agent示例:")
        for i, ua in enumerate(middleware.user_agents[:10]):
            print(f"{i+1:2}. {ua[:70]}...")
        
        print()
        
        # 演示随机选择
        print("随机选择5个User-Agent:")
        import random
        for i in range(5):
            random_ua = random.choice(middleware.user_agents)
            print(f"{i+1}. {random_ua[:70]}...")
            
    except NotConfiguredError as e:
        print(f"配置错误: {e}")


def main():
    """主函数"""
    print("开始演示随机User-Agent的来源")
    print()
    
    demo_random_user_agent_sources()
    
    print()
    print("演示完成！")


if __name__ == '__main__':
    main()