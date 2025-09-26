#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 新默认配置测试
验证修改后的默认配置行为
"""

from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.exceptions import NotConfiguredError
from unittest.mock import Mock


def test_middleware_with_new_defaults():
    """测试使用新默认配置时中间件的行为"""
    print("=== 测试使用新默认配置时中间件的行为 ===")
    
    # 创建设置管理器（使用新默认设置）
    settings = SettingManager()
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print("中间件创建成功")
        print(f"默认请求头数量: {len(middleware.headers)}")
        print(f"默认请求头内容: {middleware.headers}")
        print(f"默认User-Agent: {middleware.user_agent}")
        print(f"随机User-Agent启用: {middleware.random_user_agent_enabled}")
        print(f"User-Agent列表数量: {len(middleware.user_agents)}")
    except NotConfiguredError as e:
        print(f"中间件未配置: {e}")
    print()


def test_middleware_with_random_user_agent_enabled():
    """测试启用随机User-Agent时中间件的行为"""
    print("=== 测试启用随机User-Agent时中间件的行为 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('RANDOM_USER_AGENT_ENABLED', True)
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    try:
        # 创建中间件实例
        middleware = DefaultHeaderMiddleware.create_instance(crawler)
        print("中间件创建成功")
        print(f"默认User-Agent: {middleware.user_agent}")
        print(f"随机User-Agent启用: {middleware.random_user_agent_enabled}")
        print(f"User-Agent列表数量: {len(middleware.user_agents)}")
        print("前5个User-Agent:")
        for i, ua in enumerate(middleware.user_agents[:5]):
            print(f"  {i+1}. {ua[:80]}...")
    except NotConfiguredError as e:
        print(f"中间件未配置: {e}")
    print()


def main():
    """主函数"""
    print("开始测试DefaultHeaderMiddleware在新默认配置下的行为")
    print()
    
    # 测试使用新默认配置时中间件的行为
    test_middleware_with_new_defaults()
    
    # 测试启用随机User-Agent时中间件的行为
    test_middleware_with_random_user_agent_enabled()
    
    print("测试完成！")


if __name__ == '__main__':
    main()