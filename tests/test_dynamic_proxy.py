#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试动态下载器（Selenium和Playwright）的代理功能
"""

import asyncio
from crawlo.network.request import Request
from crawlo.tools import AuthenticatedProxy


def test_proxy_with_selenium():
    """测试Selenium下载器与认证代理"""
    print("=== 测试Selenium下载器与认证代理 ===")
    
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
    
    # Selenium的代理设置方式
    print(f"Selenium代理设置方式:")
    print(f"  1. 在设置中配置: SELENIUM_PROXY = '{proxy.clean_url}'")
    print(f"  2. 认证信息需要通过其他方式处理")
    
    # 对于带认证的代理，Selenium需要特殊处理
    if proxy.username and proxy.password:
        print(f"  3. 认证信息:")
        print(f"    用户名: {proxy.username}")
        print(f"    密码: {proxy.password}")
        print(f"    认证头: {proxy.get_auth_header()}")
    
    print("Selenium测试完成!")


async def test_proxy_with_playwright():
    """测试Playwright下载器与认证代理"""
    print("\n=== 测试Playwright下载器与认证代理 ===")
    
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
    
    # Playwright的代理设置方式
    print(f"Playwright代理设置方式:")
    print(f"  1. 在启动浏览器时配置代理:")
    print(f"     browser = await playwright.chromium.launch(proxy={{'server': '{proxy.clean_url}'}})")
    
    # 对于带认证的代理，Playwright需要在代理配置中包含认证信息
    if proxy.username and proxy.password:
        print(f"  2. 带认证的代理配置:")
        print(f"     proxy_config = {{")
        print(f"         'server': '{proxy.clean_url}',")
        print(f"         'username': '{proxy.username}',")
        print(f"         'password': '{proxy.password}'")
        print(f"     }}")
        print(f"     browser = await playwright.chromium.launch(proxy=proxy_config)")
    
    print("Playwright测试完成!")


async def main():
    """主测试函数"""
    print("开始测试动态下载器的代理功能...\n")
    
    # 测试各个下载器
    test_proxy_with_selenium()
    await test_proxy_with_playwright()
    
    print("\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())