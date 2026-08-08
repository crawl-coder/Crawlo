#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代理中间件与下载器配合测试脚本
测试指定的代理URL与下载器的兼容性
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.proxy import ProxyMiddleware
from crawlo.downloader.httpx_downloader import HttpXDownloader
from crawlo.network import Request


async def test_proxy_middleware():
    """测试代理中间件"""
    print("=== 测试代理中间件 ===")
    
    # 创建设置管理器
    settings_manager = SettingManager()
    settings = settings_manager  # SettingManager实例本身就是设置对象
    
    # 配置代理
    settings.set('PROXY_API_URL', 'http://proxy-api.example.com/proxy/getitem/')
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建代理中间件
    proxy_middleware = ProxyMiddleware(settings, "DEBUG")
    
    print(f"代理中间件已创建")
    print(f"模式: {proxy_middleware.mode}")
    print(f"是否启用: {proxy_middleware.enabled}")
    
    if proxy_middleware.enabled and proxy_middleware.mode == "dynamic":
        # 测试从API获取代理
        print("\n尝试从API获取代理...")
        proxy = await proxy_middleware._fetch_proxy_from_api()
        print(f"获取到的代理: {proxy}")
        
    return proxy_middleware


async def test_downloader_with_proxy():
    """测试下载器与代理配合"""
    print("\n=== 测试下载器与代理配合 ===")
    
    # 创建设置管理器
    settings_manager = SettingManager()
    settings = settings_manager  # SettingManager实例本身就是设置对象
    
    # 配置代理
    settings.set('PROXY_API_URL', 'http://proxy-api.example.com/proxy/getitem/')
    settings.set('LOG_LEVEL', 'DEBUG')
    
    # 创建代理中间件
    proxy_middleware = ProxyMiddleware(settings, "DEBUG")
    
    # 创建下载器
    class MockStats:
        def __init__(self):
            pass
            
        def inc_value(self, key, count=1):
            pass
    
    class MockSubscriber:
        def __init__(self):
            pass
            
        def subscribe(self, callback, event):
            pass
    
    class MockSpider:
        def __init__(self):
            self.name = "test_spider"
    
    class MockEngine:
        def __init__(self):
            pass
    
    class MockCrawler:
        def __init__(self, settings):
            self.settings = settings
            self.spider = MockSpider()  # 添加spider属性
            self.stats = MockStats()    # 添加stats属性
            self.subscriber = MockSubscriber()  # 添加subscriber属性
            self.engine = MockEngine()  # 添加engine属性
    
    crawler = MockCrawler(settings)
    downloader = HttpXDownloader(crawler)
    downloader.open()
    
    # 创建测试请求
    test_url = "https://httpbin.org/ip"  # 返回客户端IP的测试站点
    request = Request(url=test_url)
    
    # 创建模拟爬虫
    spider = MockSpider()
    
    try:
        # 通过代理中间件处理请求
        print("通过代理中间件处理请求...")
        await proxy_middleware.process_request(request, spider)
        
        if request.proxy:
            print(f"代理已设置: {request.proxy}")
        else:
            print("未设置代理")
            
        # 使用下载器下载
        print(f"开始下载: {test_url}")
        response = await downloader.download(request)
        
        if response:
            print(f"下载成功，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")  # 只显示前200个字符
        else:
            print("下载失败，响应为空")
            
    except Exception as e:
        print(f"下载过程中出错: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理资源
        try:
            await downloader.close()
        except:
            pass


async def main():
    """主测试函数"""
    print("开始测试代理中间件与下载器的配合...")
    
    # 测试代理中间件
    await test_proxy_middleware()
    
    # 测试下载器与代理配合
    await test_downloader_with_proxy()
    
    print("\n测试完成")


if __name__ == "__main__":
    asyncio.run(main())