#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试动态下载器（Selenium和Playwright）的代理功能
"""

import asyncio
from crawlo.tools import AuthenticatedProxy


def test_selenium_proxy_configuration():
    """测试Selenium下载器的代理配置"""
    print("=== 测试Selenium下载器的代理配置 ===")
    
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
    print(f"\nSelenium代理设置方式:")
    print(f"  1. 在爬虫设置中配置:")
    print(f"     settings = {{")
    print(f"         'SELENIUM_PROXY': '{proxy.clean_url}',")
    print(f"     }}")
    
    # 对于带认证的代理，需要特殊处理
    if proxy.username and proxy.password:
        print(f"\n  2. 带认证代理的处理:")
        print(f"     - 用户名: {proxy.username}")
        print(f"     - 密码: {proxy.password}")
        print(f"     - 认证头: {proxy.get_auth_header()}")
        print(f"     - 注意: Selenium需要通过扩展或其他方式处理认证")
    
    print("\nSelenium测试完成!")


async def test_playwright_proxy_configuration():
    """测试Playwright下载器的代理配置"""
    print("\n=== 测试Playwright下载器的代理配置 ===")
    
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
    print(f"\nPlaywright代理设置方式:")
    print(f"  1. 简单代理配置:")
    print(f"     settings = {{")
    print(f"         'PLAYWRIGHT_PROXY': '{proxy.clean_url}',")
    print(f"     }}")
    
    # 对于带认证的代理，Playwright可以直接在代理配置中包含认证信息
    if proxy.username and proxy.password:
        print(f"\n  2. 带认证的代理配置:")
        print(f"     settings = {{")
        print(f"         'PLAYWRIGHT_PROXY': {{")
        print(f"             'server': '{proxy.clean_url}',")
        print(f"             'username': '{proxy.username}',")
        print(f"             'password': '{proxy.password}'")
        print(f"         }}")
        print(f"     }}")
    
    print("\nPlaywright测试完成!")


def show_proxy_usage_examples():
    """显示代理使用示例"""
    print("\n=== 代理使用示例 ===")
    
    # 代理配置示例
    proxy_examples = [
        "http://username:password@proxy.example.com:8080",  # 带认证HTTP代理
        "https://user:pass@secure-proxy.example.com:443",   # 带认证HTTPS代理
        "http://proxy.example.com:8080",                    # 不带认证代理
        "socks5://username:password@socks-proxy.example.com:1080"  # SOCKS5代理
    ]
    
    for i, proxy_url in enumerate(proxy_examples, 1):
        print(f"\n示例 {i}: {proxy_url}")
        try:
            proxy = AuthenticatedProxy(proxy_url)
            print(f"  清洁URL: {proxy.clean_url}")
            print(f"  用户名: {proxy.username or '无'}")
            print(f"  密码: {proxy.password or '无'}")
            print(f"  是否有效: {proxy.is_valid()}")
            if proxy.username and proxy.password:
                print(f"  认证头: {proxy.get_auth_header()}")
        except Exception as e:
            print(f"  错误: {e}")


async def main():
    """主测试函数"""
    print("开始测试动态下载器的代理功能...\n")
    
    # 测试各个下载器
    test_selenium_proxy_configuration()
    await test_playwright_proxy_configuration()
    show_proxy_usage_examples()
    
    print("\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())