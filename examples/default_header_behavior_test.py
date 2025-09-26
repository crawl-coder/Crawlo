#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 行为测试
测试DefaultHeaderMiddleware在不同配置下的行为
"""

from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.exceptions import NotConfiguredError
from unittest.mock import Mock


def test_middleware_with_default_settings():
    """测试使用默认设置时中间件的行为"""
    print("=== 测试使用默认设置时中间件的行为 ===")
    
    # 创建设置管理器（使用默认设置）
    settings = SettingManager()
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 尝试创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print("中间件创建成功")
        print(f"默认请求头数量: {len(middleware.headers)}")
        print(f"User-Agent: {middleware.user_agent}")
        print(f"User-Agent列表数量: {len(middleware.user_agents)}")
        print(f"随机头部数量: {len(middleware.random_headers)}")
        print(f"随机User-Agent启用: {middleware.random_user_agent_enabled}")
    except NotConfiguredError as e:
        print(f"中间件未配置: {e}")
    print()


def test_middleware_with_custom_headers():
    """测试使用自定义请求头时中间件的行为"""
    print("=== 测试使用自定义请求头时中间件的行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print("中间件创建成功")
        print(f"默认请求头数量: {len(middleware.headers)}")
        print(f"请求头内容: {middleware.headers}")
    except NotConfiguredError as e:
        print(f"中间件未配置: {e}")
    print()


def test_middleware_with_user_agent():
    """测试使用User-Agent时中间件的行为"""
    print("=== 测试使用User-Agent时中间件的行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print("中间件创建成功")
        print(f"User-Agent: {middleware.user_agent}")
        print(f"默认请求头中的User-Agent: {middleware.headers.get('User-Agent', '未设置')}")
    except NotConfiguredError as e:
        print(f"中间件未配置: {e}")
    print()


def test_middleware_with_random_user_agent():
    """测试启用随机User-Agent时中间件的行为"""
    print("=== 测试启用随机User-Agent时中间件的行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('RANDOM_USER_AGENT_ENABLED', True)
    settings.set('USER_AGENTS', [
        'Custom-Agent/1.0',
        'Custom-Agent/2.0',
        'Custom-Agent/3.0'
    ])
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print("中间件创建成功")
        print(f"随机User-Agent启用: {middleware.random_user_agent_enabled}")
        print(f"User-Agent列表数量: {len(middleware.user_agents)}")
        print(f"User-Agent列表内容: {middleware.user_agents}")
    except NotConfiguredError as e:
        print(f"中间件未配置: {e}")
    print()


def main():
    """主函数"""
    print("开始测试DefaultHeaderMiddleware在不同配置下的行为")
    print()
    
    # 测试使用默认设置时中间件的行为
    test_middleware_with_default_settings()
    
    # 测试使用自定义请求头时中间件的行为
    test_middleware_with_custom_headers()
    
    # 测试使用User-Agent时中间件的行为
    test_middleware_with_user_agent()
    
    # 测试启用随机User-Agent时中间件的行为
    test_middleware_with_random_user_agent()
    
    print("测试完成！")


if __name__ == '__main__':
    main()