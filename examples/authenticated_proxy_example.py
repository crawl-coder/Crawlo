#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
带认证代理使用示例
================
展示如何在Crawlo框架中使用带用户名密码认证的代理和非认证代理

支持的代理类型:
1. 带认证的HTTP/HTTPS代理
2. 不带认证的HTTP/HTTPS代理
3. SOCKS代理（带或不带认证）
"""

from crawlo import Spider, Request
from crawlo.tools import (
    AuthenticatedProxy,
    create_proxy_config,
    format_proxy_for_request,
    get_proxy_info,
    validate_proxy_url
)


def demo_proxy_parsing():
    """演示代理URL解析"""
    print("=== 代理URL解析演示 ===\n")
    
    # 测试不同类型的代理URL
    proxy_urls = [
        # 带认证的HTTP代理
        "http://username:password@proxy.example.com:8080",
        # 不带认证的HTTP代理
        "http://proxy.example.com:8080",
        # 带认证的HTTPS代理
        "https://user123:pass456@secure-proxy.com:443",
        # SOCKS5代理
        "socks5://socks-user:socks-pass@socks-proxy.com:1080",
        # 不带认证的SOCKS4代理
        "socks4://socks4-proxy.com:1080"
    ]
    
    for proxy_url in proxy_urls:
        print(f"解析代理URL: {proxy_url}")
        
        # 验证代理URL
        is_valid = validate_proxy_url(proxy_url)
        print(f"  有效性: {'有效' if is_valid else '无效'}")
        
        if is_valid:
            # 获取代理详细信息
            proxy_info = get_proxy_info(proxy_url)
            print(f"  协议: {proxy_info['scheme']}")
            print(f"  主机: {proxy_info['hostname']}")
            print(f"  端口: {proxy_info['port']}")
            print(f"  有认证: {'是' if proxy_info['has_auth'] else '否'}")
            if proxy_info['has_auth']:
                print(f"  用户名: {proxy_info['username']}")
            
            # 创建代理配置
            proxy_config = create_proxy_config(proxy_url)
            print(f"  代理配置: {proxy_config}")
            
            # 格式化为不同下载器的配置
            for downloader in ["aiohttp", "httpx", "curl_cffi"]:
                formatted = format_proxy_for_request(proxy_config, downloader)
                print(f"  {downloader}格式: {formatted}")
        
        print()


def demo_authenticated_proxy_class():
    """演示AuthenticatedProxy类的使用"""
    print("=== AuthenticatedProxy类演示 ===\n")
    
    # 带认证的代理
    auth_proxy = AuthenticatedProxy("http://myuser:mypass@proxy.company.com:8080")
    print(f"代理URL: {auth_proxy}")
    print(f"清洁URL: {auth_proxy.clean_url}")
    print(f"用户名: {auth_proxy.username}")
    print(f"密码: {auth_proxy.password}")
    print(f"代理字典: {auth_proxy.proxy_dict}")
    print(f"认证凭据: {auth_proxy.get_auth_credentials()}")
    print(f"认证头: {auth_proxy.get_auth_header()}")
    print(f"是否有效: {auth_proxy.is_valid()}")
    print()
    
    # 不带认证的代理
    no_auth_proxy = AuthenticatedProxy("http://public.proxy.com:8080")
    print(f"代理URL: {no_auth_proxy}")
    print(f"清洁URL: {no_auth_proxy.clean_url}")
    print(f"用户名: {no_auth_proxy.username}")
    print(f"密码: {no_auth_proxy.password}")
    print(f"代理字典: {no_auth_proxy.proxy_dict}")
    print(f"认证凭据: {no_auth_proxy.get_auth_credentials()}")
    print(f"认证头: {no_auth_proxy.get_auth_header()}")
    print(f"是否有效: {no_auth_proxy.is_valid()}")
    print()


class ProxySpider(Spider):
    """使用代理的爬虫示例"""
    name = 'proxy_spider'
    
    def __init__(self):
        super().__init__()
        # 代理列表
        self.proxies = [
            "http://user1:pass1@proxy1.example.com:8080",
            "http://user2:pass2@proxy2.example.com:8080",
            "http://proxy3.example.com:8080",  # 不带认证
            "https://secureuser:securepass@secure.proxy.com:443"
        ]
        self.current_proxy_index = 0
    
    def get_next_proxy(self):
        """获取下一个代理"""
        proxy_url = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        return proxy_url
    
    def start_requests(self):
        urls = [
            'https://httpbin.org/ip',      # 查看IP地址
            'https://httpbin.org/headers', # 查看请求头
            'https://example.com',         # 普通网站
        ]
        
        for url in urls:
            # 获取代理
            proxy_url = self.get_next_proxy()
            proxy = AuthenticatedProxy(proxy_url)
            
            # 创建请求
            request = Request(url=url, callback=self.parse)
            
            # 根据不同下载器设置代理
            # 这里以AioHttp为例
            if self.crawler.settings.get("DOWNLOADER_TYPE") == "aiohttp":
                request.proxy = proxy.clean_url
                auth = proxy.get_auth_credentials()
                if auth:
                    # AioHttp需要在下载器中处理认证
                    request.meta["proxy_auth"] = auth
            else:
                # 其他下载器
                request.proxy = proxy.proxy_dict
                
            yield request
    
    def parse(self, response):
        """解析响应"""
        print(f"成功访问: {response.url}")
        print(f"状态码: {response.status_code}")
        # 显示前200个字符
        print(f"响应内容: {response.text[:200]}...\n")
        yield {"url": response.url, "status": response.status_code}


def demo_in_spider():
    """演示在爬虫中使用代理"""
    print("=== 在爬虫中使用代理 ===\n")
    print("在爬虫项目中，您可以这样使用带认证的代理:")
    print("""
from crawlo import Spider, Request
from crawlo.tools import AuthenticatedProxy

class MySpider(Spider):
    name = 'my_spider'
    
    def __init__(self):
        super().__init__()
        self.proxy_urls = [
            "http://username:password@proxy1.example.com:8080",
            "http://user:pass@proxy2.example.com:8080",
            "http://proxy3.example.com:8080"  # 不带认证
        ]
    
    def start_requests(self):
        urls = ['https://httpbin.org/ip', 'https://example.com']
        
        for i, url in enumerate(urls):
            # 选择代理
            proxy_url = self.proxy_urls[i % len(self.proxy_urls)]
            proxy = AuthenticatedProxy(proxy_url)
            
            # 创建请求
            request = Request(url=url, callback=self.parse)
            
            # 设置代理（根据不同下载器）
            downloader_type = self.crawler.settings.get("DOWNLOADER_TYPE", "aiohttp")
            
            if downloader_type == "aiohttp":
                # AioHttp下载器
                request.proxy = proxy.clean_url
                auth = proxy.get_auth_credentials()
                if auth:
                    request.meta["proxy_auth"] = auth
            elif downloader_type == "httpx":
                # HttpX下载器
                request.proxy = proxy.clean_url
            elif downloader_type == "curl_cffi":
                # CurlCffi下载器
                request.proxy = proxy.proxy_dict
                # 认证信息在URL中或通过headers传递
                auth_header = proxy.get_auth_header()
                if auth_header:
                    request.headers["Proxy-Authorization"] = auth_header
            
            yield request
    
    def parse(self, response):
        # 处理响应
        yield {"url": response.url, "title": response.css('title::text').get()}
    """)


if __name__ == '__main__':
    # 运行演示
    demo_proxy_parsing()
    demo_authenticated_proxy_class()
    demo_in_spider()
    
    print("\n=== 配置说明 ===")
    print("在settings.py中配置代理:")
    print("""
# 启用代理中间件
MIDDLEWARES = [
    # ... 其他中间件 ...
    'crawlo.middleware.proxy.ProxyMiddleware',
]

# 代理配置
PROXY_ENABLED = True
PROXY_API_URL = "https://api.proxyprovider.com/get"  # 代理API地址
PROXY_EXTRACTOR = "proxy"  # 从API响应中提取代理的字段路径
PROXY_REFRESH_INTERVAL = 60  # 代理刷新间隔（秒）
""")