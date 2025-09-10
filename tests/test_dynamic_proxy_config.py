#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试动态下载器（Selenium和Playwright）的代理配置逻辑
"""

from crawlo.tools import AuthenticatedProxy


def test_selenium_proxy_logic():
    """测试Selenium下载器的代理配置逻辑"""
    print("=== 测试Selenium下载器的代理配置逻辑 ===")
    
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
    
    # 模拟Selenium的代理配置逻辑
    print(f"\nSelenium代理配置逻辑:")
    print(f"  1. 在爬虫设置中配置:")
    print(f"     settings = {{")
    print(f"         'SELENIUM_PROXY': '{proxy.clean_url}',")
    print(f"     }}")
    
    # 对于带认证的代理，需要特殊处理
    if proxy.username and proxy.password:
        print(f"\n  2. 带认证代理的处理逻辑:")
        print(f"     - 用户名: {proxy.username}")
        print(f"     - 密码: {proxy.password}")
        print(f"     - 认证头: {proxy.get_auth_header()}")
        print(f"     - 处理方式: 通过浏览器扩展或手动输入认证信息")
    
    print("\nSelenium配置逻辑测试完成!")


def test_playwright_proxy_logic():
    """测试Playwright下载器的代理配置逻辑"""
    print("\n=== 测试Playwright下载器的代理配置逻辑 ===")
    
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
    
    # 模拟Playwright的代理配置逻辑
    print(f"\nPlaywright代理配置逻辑:")
    print(f"  1. 简单代理配置:")
    print(f"     settings = {{")
    print(f"         'PLAYWRIGHT_PROXY': '{proxy.clean_url}',")
    print(f"     }}")
    
    # 对于带认证的代理，Playwright可以直接在代理配置中包含认证信息
    if proxy.username and proxy.password:
        print(f"\n  2. 带认证的代理配置逻辑:")
        print(f"     settings = {{")
        print(f"         'PLAYWRIGHT_PROXY': {{")
        print(f"             'server': '{proxy.clean_url}',")
        print(f"             'username': '{proxy.username}',")
        print(f"             'password': '{proxy.password}'")
        print(f"         }}")
        print(f"     }}")
        print(f"     实现方式: 在启动浏览器时传递proxy参数")
    
    print("\nPlaywright配置逻辑测试完成!")


def show_proxy_configuration_examples():
    """显示代理配置示例"""
    print("\n=== 代理配置示例 ===")
    
    # 不同类型的代理配置示例
    examples = [
        {
            "name": "带认证HTTP代理",
            "url": "http://username:password@proxy.example.com:8080",
            "selenium_config": "SELENIUM_PROXY = 'http://proxy.example.com:8080'",
            "playwright_config": "PLAYWRIGHT_PROXY = {'server': 'http://proxy.example.com:8080', 'username': 'username', 'password': 'password'}"
        },
        {
            "name": "带认证HTTPS代理",
            "url": "https://user:pass@secure-proxy.example.com:443",
            "selenium_config": "SELENIUM_PROXY = 'https://secure-proxy.example.com:443'",
            "playwright_config": "PLAYWRIGHT_PROXY = {'server': 'https://secure-proxy.example.com:443', 'username': 'user', 'password': 'pass'}"
        },
        {
            "name": "SOCKS5代理",
            "url": "socks5://username:password@socks-proxy.example.com:1080",
            "selenium_config": "SELENIUM_PROXY = 'socks5://socks-proxy.example.com:1080'",
            "playwright_config": "PLAYWRIGHT_PROXY = {'server': 'socks5://socks-proxy.example.com:1080', 'username': 'username', 'password': 'password'}"
        },
        {
            "name": "不带认证代理",
            "url": "http://proxy.example.com:8080",
            "selenium_config": "SELENIUM_PROXY = 'http://proxy.example.com:8080'",
            "playwright_config": "PLAYWRIGHT_PROXY = 'http://proxy.example.com:8080'"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n示例 {i}: {example['name']}")
        print(f"  代理URL: {example['url']}")
        proxy = AuthenticatedProxy(example['url'])
        print(f"  清洁URL: {proxy.clean_url}")
        print(f"  用户名: {proxy.username or '无'}")
        print(f"  密码: {proxy.password or '无'}")
        print(f"  Selenium配置: {example['selenium_config']}")
        print(f"  Playwright配置: {example['playwright_config']}")


def main():
    """主函数"""
    print("开始测试动态下载器的代理配置逻辑...\n")
    
    # 测试各个下载器的配置逻辑
    test_selenium_proxy_logic()
    test_playwright_proxy_logic()
    show_proxy_configuration_examples()
    
    print("\n所有配置逻辑测试完成!")
    print("\n总结:")
    print("1. Selenium和Playwright都支持代理配置")
    print("2. 带认证的代理需要特殊处理")
    print("3. Playwright对带认证代理的支持更直接")
    print("4. Selenium需要通过扩展或其他方式处理认证")


if __name__ == "__main__":
    main()