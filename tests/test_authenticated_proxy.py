#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试带认证代理的功能
"""

import asyncio
import aiohttp
import httpx
from crawlo.network.request import Request
from crawlo.tools import AuthenticatedProxy


async def test_proxy_with_aiohttp():
    """测试AioHttp与认证代理"""
    print("=== 测试AioHttp与认证代理 ===")
    
    # 代理配置
    proxy_config = {
        "http": "http://dwe20241014:Dwe0101014@182.201.243.186:58111",
        "https": "http://dwe20241014:Dwe0101014@182.201.243.186:58111"
    }
    
    # 创建代理对象
    proxy_url = proxy_config["http"]
    proxy = AuthenticatedProxy(proxy_url)
    
    print(f"原始代理URL: {proxy_url}")
    print(f"清洁URL: {proxy.clean_url}")
    print(f"认证信息: {proxy.get_auth_credentials()}")
    
    # 使用aiohttp直接测试
    try:
        auth = proxy.get_auth_credentials()
        if auth:
            basic_auth = aiohttp.BasicAuth(auth['username'], auth['password'])
        else:
            basic_auth = None
            
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://httpbin.org/ip",
                proxy=proxy.clean_url,
                proxy_auth=basic_auth
            ) as response:
                print(f"AioHttp测试成功!")
                print(f"状态码: {response.status}")
                content = await response.text()
                print(f"响应内容: {content[:200]}...")
                
    except Exception as e:
        print(f"AioHttp测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_proxy_with_httpx():
    """测试HttpX与认证代理"""
    print("\n=== 测试HttpX与认证代理 ===")
    
    # 代理配置
    proxy_config = {
        "http": "http://dwe20241014:Dwe0101014@182.201.243.186:58111",
        "https": "http://dwe20241014:Dwe0101014@182.201.243.186:58111"
    }
    
    # 使用httpx直接测试
    try:
        # HttpX可以直接使用带认证的URL作为proxy参数
        proxy_url = proxy_config["http"]
        
        with httpx.Client(proxy=proxy_url) as client:
            response = client.get("https://httpbin.org/ip")
            print(f"HttpX测试成功!")
            print(f"状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")
                
    except Exception as e:
        print(f"HttpX测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_proxy_with_curl_cffi():
    """测试CurlCffi与认证代理"""
    print("\n=== 测试CurlCffi与认证代理 ===")
    
    # 代理配置
    proxy_config = {
        "http": "http://dwe20241014:Dwe0101014@182.201.243.186:58111",
        "https": "http://dwe20241014:Dwe0101014@182.201.243.186:58111"
    }
    
    # 创建代理对象
    proxy_url = proxy_config["http"]
    proxy = AuthenticatedProxy(proxy_url)
    
    print(f"原始代理URL: {proxy_url}")
    print(f"代理字典: {proxy.proxy_dict}")
    print(f"认证头: {proxy.get_auth_header()}")
    
    # 使用curl-cffi直接测试
    try:
        from curl_cffi import requests as curl_requests
        
        # 设置代理和认证头
        proxies = proxy.proxy_dict
        headers = {}
        auth_header = proxy.get_auth_header()
        if auth_header:
            headers["Proxy-Authorization"] = auth_header
            
        response = curl_requests.get(
            "https://httpbin.org/ip",
            proxies=proxies,
            headers=headers
        )
        
        print(f"CurlCffi测试成功!")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:200]}...")
                
    except Exception as e:
        print(f"CurlCffi测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试带认证代理的功能...\n")
    
    # 测试各个库
    await test_proxy_with_aiohttp()
    test_proxy_with_httpx()
    await test_proxy_with_curl_cffi()
    
    print("\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())