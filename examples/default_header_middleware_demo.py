#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 演示文件
演示默认请求头中间件的功能，包括随机更换header功能
"""

from unittest.mock import Mock
from crawlo.middleware.default_header import DefaultHeaderMiddleware
from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.log import get_logger


class SimpleLogger:
    """简单的日志记录器"""
    def __init__(self, name, level=None):
        self.name = name
        self.level = level

    def debug(self, msg):
        print(f"[DEBUG] {self.name}: {msg}")

    def info(self, msg):
        print(f"[INFO] {self.name}: {msg}")

    def warning(self, msg):
        print(f"[WARNING] {self.name}: {msg}")

    def error(self, msg):
        print(f"[ERROR] {self.name}: {msg}")

    def isEnabledFor(self, level):
        return True


def demo_default_headers():
    """演示默认请求头功能"""
    print("=== 演示默认请求头功能 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
    })
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    # 创建中间件实例
    middleware = DefaultHeaderMiddleware.create_instance(crawler)
    
    # 创建请求
    request = Mock()
    request.headers = {}
    request.url = 'https://example.com'
    
    spider = Mock()
    
    print(f"处理前的请求头: {request.headers}")
    
    # 处理请求
    middleware.process_request(request, spider)
    
    print(f"处理后的请求头: {request.headers}")
    print()


def demo_random_user_agent():
    """演示随机User-Agent功能"""
    print("=== 演示随机User-Agent功能 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('RANDOM_USER_AGENT_ENABLED', True)
    settings.set('USER_AGENTS', [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0',
    ])
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    # 创建中间件实例
    middleware = DefaultHeaderMiddleware.create_instance(crawler)
    
    print(f"User-Agent列表长度: {len(middleware.user_agents)}")
    
    # 创建多个请求来演示随机性
    for i in range(5):
        request = Mock()
        request.headers = {}
        request.url = f'https://example.com/page{i}'
        
        spider = Mock()
        
        # 处理请求
        middleware.process_request(request, spider)
        
        print(f"请求 {i+1} 的User-Agent: {request.headers.get('User-Agent', '未设置')}")
    print()


def demo_existing_headers():
    """演示已有请求头不被覆盖的功能"""
    print("=== 演示已有请求头不被覆盖的功能 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    settings.set('DEFAULT_REQUEST_HEADERS', {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建一个模拟的crawler对象
    crawler = Mock()
    crawler.settings = settings
    
    # 创建中间件实例
    middleware = DefaultHeaderMiddleware.create_instance(crawler)
    
    # 创建已有请求头的请求
    request = Mock()
    request.headers = {
        'Accept': 'application/json',  # 已存在的请求头
    }
    request.url = 'https://example.com'
    
    spider = Mock()
    
    print(f"处理前的请求头: {request.headers}")
    
    # 处理请求
    middleware.process_request(request, spider)
    
    print(f"处理后的请求头: {request.headers}")
    print("注意：已存在的Accept头没有被覆盖，但添加了Accept-Language头")
    print()


def main():
    """主函数"""
    print("开始演示DefaultHeaderMiddleware的功能")
    print()
    
    # 演示默认请求头功能
    demo_default_headers()
    
    # 演示随机User-Agent功能
    demo_random_user_agent()
    
    # 演示已有请求头不被覆盖的功能
    demo_existing_headers()
    
    print("演示完成！")


if __name__ == '__main__':
    main()