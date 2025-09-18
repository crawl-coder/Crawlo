#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DownloadDelayMiddleware 使用示例
展示如何配置和使用下载延迟中间件
"""

import asyncio
from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.download_delay import DownloadDelayMiddleware


def example_with_fixed_delay():
    """固定延迟示例"""
    print("=== 固定延迟示例 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 配置固定延迟
    settings.set('DOWNLOAD_DELAY', 2.0)  # 2秒固定延迟
    settings.set('RANDOMNESS', False)    # 不启用随机延迟
    settings.set('LOG_LEVEL', 'INFO')   # 设置日志级别
    
    # 创建爬虫模拟对象
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
            self.stats = None
    
    crawler = MockCrawler(settings)
    
    # 创建中间件实例
    middleware = DownloadDelayMiddleware.create_instance(crawler)
    
    print(f"延迟设置: {middleware.delay}秒")
    print(f"是否启用随机延迟: {middleware.randomness}")
    print("中间件创建成功！")


def example_with_random_delay():
    """随机延迟示例"""
    print("\n=== 随机延迟示例 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 配置随机延迟
    settings.set('DOWNLOAD_DELAY', 1.0)        # 基础延迟1秒
    settings.set('RANDOMNESS', True)           # 启用随机延迟
    settings.set('RANDOM_RANGE', [0.5, 2.0])   # 随机范围因子
    settings.set('LOG_LEVEL', 'INFO')         # 设置日志级别
    
    # 创建爬虫模拟对象
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
            self.stats = None
    
    crawler = MockCrawler(settings)
    
    # 创建中间件实例
    middleware = DownloadDelayMiddleware.create_instance(crawler)
    
    print(f"基础延迟设置: {middleware.delay}秒")
    print(f"是否启用随机延迟: {middleware.randomness}")
    print(f"随机范围: {middleware.floor} - {middleware.upper}")
    print(f"实际延迟范围: {middleware.delay * middleware.floor} - {middleware.delay * middleware.upper}秒")
    print("中间件创建成功！")


def example_with_invalid_config():
    """无效配置示例"""
    print("\n=== 无效配置示例 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 配置无效的延迟（0值）
    settings.set('DOWNLOAD_DELAY', 0)      # 无效延迟
    settings.set('LOG_LEVEL', 'INFO')     # 设置日志级别
    
    # 创建爬虫模拟对象
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
            self.stats = None
    
    crawler = MockCrawler(settings)
    
    try:
        # 尝试创建中间件实例
        middleware = DownloadDelayMiddleware.create_instance(crawler)
        print("中间件创建成功！")
    except Exception as e:
        print(f"中间件创建失败: {e}")


def example_with_stats():
    """带统计信息的示例"""
    print("\n=== 带统计信息的示例 ===")
    
    # 创建设置管理器
    settings = SettingManager()
    
    # 配置固定延迟
    settings.set('DOWNLOAD_DELAY', 1.0)  # 1秒固定延迟
    settings.set('RANDOMNESS', False)    # 不启用随机延迟
    settings.set('LOG_LEVEL', 'INFO')   # 设置日志级别
    
    # 创建统计收集器模拟对象
    class MockStats:
        def __init__(self):
            self.stats = {}
            
        def inc_value(self, key, value=1):
            if key in self.stats:
                self.stats[key] += value
            else:
                self.stats[key] = value
                
        def __str__(self):
            return str(self.stats)
    
    # 创建爬虫模拟对象
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
            self.stats = MockStats()
    
    crawler = MockCrawler(settings)
    
    # 创建中间件实例
    middleware = DownloadDelayMiddleware.create_instance(crawler)
    
    print(f"延迟设置: {middleware.delay}秒")
    print("中间件创建成功！")
    
    # 模拟处理请求
    class MockRequest:
        pass
        
    class MockSpider:
        pass
        
    request = MockRequest()
    spider = MockSpider()
    
    # 执行请求处理
    asyncio.run(middleware.process_request(request, spider))
    
    print(f"统计信息: {crawler.stats}")


if __name__ == '__main__':
    # 运行所有示例
    example_with_fixed_delay()
    example_with_random_delay()
    example_with_invalid_config()
    example_with_stats()