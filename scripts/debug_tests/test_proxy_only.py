#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代理中间件测试脚本
测试指定的代理URL功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.settings.setting_manager import SettingManager
from crawlo.middleware.proxy import ProxyMiddleware
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
        
        # 测试代理提取功能
        if proxy:
            print(f"代理格式正确: {proxy.startswith('http://') or proxy.startswith('https://')}")
            
            # 测试处理请求
            print("\n测试处理请求...")
            request = Request(url="https://httpbin.org/ip")
            
            class MockSpider:
                def __init__(self):
                    self.name = "test_spider"
            
            spider = MockSpider()
            
            await proxy_middleware.process_request(request, spider)
            
            if request.proxy:
                print(f"请求代理设置成功: {request.proxy}")
            else:
                print("请求代理设置失败")
        else:
            print("未能从API获取有效代理")
    else:
        print("代理中间件未启用或模式不正确")
        
    return proxy_middleware


async def main():
    """主测试函数"""
    print("开始测试代理中间件...")
    
    # 测试代理中间件
    await test_proxy_middleware()
    
    print("\n测试完成")


if __name__ == "__main__":
    asyncio.run(main())