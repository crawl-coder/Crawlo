#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
增强版代理中间件测试
==================
测试ProxyMiddleware的代理池和健康检查功能
"""

import asyncio
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import AsyncMock, Mock, patch

from crawlo.middleware.proxy import ProxyMiddleware, Proxy
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.settings.setting_manager import SettingManager


def test_proxy_class():
    """测试Proxy类的基本功能"""
    print("=== 测试Proxy类 ===")
    
    # 创建代理对象
    proxy = Proxy("http://127.0.0.1:8080")
    print(f"初始代理: {proxy.proxy_str}")
    print(f"初始成功率: {proxy.success_rate}")
    print(f"是否健康: {proxy.is_healthy}")
    
    # 测试成功标记
    proxy.mark_success()
    print(f"标记成功后 - 成功率: {proxy.success_rate}, 成功次数: {proxy.success_count}")
    
    # 测试失败标记
    proxy.mark_failure()
    print(f"标记失败后 - 成功率: {proxy.success_rate}, 失败次数: {proxy.failure_count}")
    print(f"是否健康: {proxy.is_healthy}")
    
    # 测试多次失败后健康状态
    for _ in range(5):
        proxy.mark_failure()
    print(f"多次失败后 - 成功率: {proxy.success_rate}, 是否健康: {proxy.is_healthy}")
    
    print("Proxy类测试完成\n")


def create_mock_settings():
    """创建模拟设置"""
    settings = SettingManager()
    # 不再需要显式设置 PROXY_ENABLED，只要配置了 PROXY_API_URL 就会启用
    settings.set("PROXY_API_URL", "http://test.proxy.api/get")
    settings.set("LOG_LEVEL", "DEBUG")
    return settings


async def test_proxy_middleware_initialization():
    """测试代理中间件初始化"""
    print("=== 测试代理中间件初始化 ===")
    
    settings = create_mock_settings()
    middleware = ProxyMiddleware(settings, "DEBUG")
    
    print(f"代理中间件已启用: {middleware.enabled}")
    print(f"API URL: {middleware.api_url}")
    print(f"代理池大小: {middleware.proxy_pool_size}")
    print(f"健康检查阈值: {middleware.health_check_threshold}")
    print(f"刷新间隔: {middleware.refresh_interval}")
    
    print("代理中间件初始化测试完成\n")


async def test_proxy_pool_management():
    """测试代理池管理功能"""
    print("=== 测试代理池管理 ===")
    
    settings = create_mock_settings()
    middleware = ProxyMiddleware(settings, "DEBUG")
    
    # 模拟API响应
    mock_proxies = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080", 
        "http://proxy3.example.com:8080"
    ]
    
    # 测试更新代理池
    with patch.object(middleware, '_get_proxy_from_api', AsyncMock(return_value=mock_proxies[0])):
        await middleware._update_proxy_pool()
        print(f"代理池大小: {len(middleware._proxy_pool)}")
        if middleware._proxy_pool:
            print(f"第一个代理: {middleware._proxy_pool[0].proxy_str}")
    
    # 测试获取健康代理
    healthy_proxy = await middleware._get_healthy_proxy()
    if healthy_proxy:
        print(f"获取到健康代理: {healthy_proxy.proxy_str}")
    else:
        print("未获取到健康代理")
        
    print("代理池管理测试完成\n")


async def test_process_request():
    """测试请求处理"""
    print("=== 测试请求处理 ===")
    
    settings = create_mock_settings()
    middleware = ProxyMiddleware(settings, "DEBUG")
    
    # 创建模拟请求
    request = Request(url="http://example.com")
    
    # 创建模拟爬虫对象
    mock_spider = Mock()
    mock_spider.crawler.settings.get.return_value = "aiohttp"
    
    # 添加一些测试代理到池中
    middleware._proxy_pool = [
        Proxy("http://proxy1.example.com:8080"),
        Proxy("http://proxy2.example.com:8080")
    ]
    
    # 处理请求
    result = await middleware.process_request(request, mock_spider)
    print(f"处理结果: {result}")
    print(f"请求代理: {request.proxy}")
    if "_used_proxy" in request.meta:
        print(f"使用的代理对象: {request.meta['_used_proxy'].proxy_str}")
    
    print("请求处理测试完成\n")


def test_process_response():
    """测试响应处理"""
    print("=== 测试响应处理 ===")
    
    settings = create_mock_settings()
    middleware = ProxyMiddleware(settings, "DEBUG")
    
    # 创建带代理信息的请求
    request = Request(url="http://example.com")
    proxy_obj = Proxy("http://proxy1.example.com:8080")
    request.meta["_used_proxy"] = proxy_obj
    
    # 创建响应
    response = Response(
        url="http://example.com",
        status_code=200,
        body=b"test response",
        request=request
    )
    
    # 处理响应前
    print(f"处理前 - 代理成功次数: {proxy_obj.success_count}, 失败次数: {proxy_obj.failure_count}")
    
    # 处理响应
    result = middleware.process_response(request, response, None)
    
    # 处理后
    print(f"处理后 - 代理成功次数: {proxy_obj.success_count}, 失败次数: {proxy_obj.failure_count}")
    print(f"成功率: {proxy_obj.success_rate}")
    
    print("响应处理测试完成\n")


def test_process_exception():
    """测试异常处理"""
    print("=== 测试异常处理 ===")
    
    settings = create_mock_settings()
    middleware = ProxyMiddleware(settings, "DEBUG")
    
    # 创建带代理信息的请求
    request = Request(url="http://example.com")
    proxy_obj = Proxy("http://proxy1.example.com:8080")
    request.meta["_used_proxy"] = proxy_obj
    
    # 处理异常前
    print(f"处理前 - 代理成功次数: {proxy_obj.success_count}, 失败次数: {proxy_obj.failure_count}")
    
    # 处理异常
    result = middleware.process_exception(request, Exception("Test error"), None)
    
    # 处理后
    print(f"处理后 - 代理成功次数: {proxy_obj.success_count}, 失败次数: {proxy_obj.failure_count}")
    print(f"成功率: {proxy_obj.success_rate}")
    print(f"是否健康: {proxy_obj.is_healthy}")
    
    print("异常处理测试完成\n")


async def main():
    """主测试函数"""
    print("开始测试增强版代理中间件...\n")
    
    # 运行各个测试
    test_proxy_class()
    await test_proxy_middleware_initialization()
    await test_proxy_pool_management()
    await test_process_request()
    test_process_response()
    test_process_exception()
    
    print("所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())