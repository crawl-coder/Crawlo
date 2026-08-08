#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试代理中间件与Crawlo框架中三个主要下载器的兼容性
- aiohttp_downloader
- httpx_downloader
- curl_cffi_downloader
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.downloader.aiohttp_downloader import AioHttpDownloader
from crawlo.downloader.httpx_downloader import HttpXDownloader
from crawlo.downloader.cffi_downloader import CurlCffiDownloader
from crawlo.middleware.proxy import ProxyMiddleware
from crawlo.network.request import Request
from crawlo.settings.setting_manager import SettingManager


class MockSpider:
    """模拟爬虫类"""
    def __init__(self, crawler):
        self.crawler = crawler


class MockCrawler:
    """模拟爬虫实例"""
    def __init__(self, settings):
        self.settings = settings
        self.spider = MockSpider(self)  # 添加spider属性


def create_test_settings(proxy_url=None, proxy_list=None):
    """创建测试设置"""
    settings = SettingManager()
    settings.set("LOG_LEVEL", "DEBUG")
    settings.set("DOWNLOAD_TIMEOUT", 30)
    settings.set("CONNECTION_POOL_LIMIT", 100)
    settings.set("CONNECTION_POOL_LIMIT_PER_HOST", 20)
    settings.set("DOWNLOAD_MAXSIZE", 10 * 1024 * 1024)
    settings.set("VERIFY_SSL", True)
    
    # 代理相关设置
    if proxy_url:
        # 高级代理配置（适用于ProxyMiddleware）
        # 只要配置了代理API URL，中间件就会自动启用
        settings.set("PROXY_API_URL", proxy_url)
    elif proxy_list:
        # 代理配置（适用于ProxyMiddleware）
        # 只要配置了代理列表，中间件就会自动启用
        settings.set("PROXY_LIST", proxy_list)
        
    return settings


async def test_aiohttp_with_proxy(proxy_url, target_url):
    """测试aiohttp下载器与代理的适配性"""
    print(f"\n=== 测试 aiohttp 下载器与代理 ===")
    print(f"代理URL: {proxy_url}")
    print(f"目标URL: {target_url}")
    
    try:
        # 创建设置
        settings = create_test_settings(proxy_url=proxy_url)
        crawler = MockCrawler(settings)
        
        # 创建下载器
        downloader = AioHttpDownloader(crawler)
        downloader.open()
        
        # 创建代理中间件
        from crawlo.middleware.proxy import ProxyMiddleware
        proxy_middleware = ProxyMiddleware(settings, "DEBUG")
        
        # 创建请求
        request = Request(url=target_url)
        
        # 创建模拟爬虫
        spider = MockSpider(crawler)
        
        # 通过代理中间件处理请求
        await proxy_middleware.process_request(request, spider)
        
        if request.proxy:
            print(f"✓ 代理已成功设置: {request.proxy}")
        else:
            print("代理未设置")
            
        # 尝试下载
        try:
            response = await downloader.download(request)
            if response and response.status_code:
                print(f"✓ 下载成功，状态码: {response.status_code}")
                # 只检查状态码，避免编码问题
                return True
            else:
                print("✗ 下载失败，响应为空")
                return False
        except Exception as e:
            print(f"✗ 下载过程中出错: {e}")
            return False
            
    except Exception as e:
        print(f"✗ 测试aiohttp时出错: {e}")
        return False
    finally:
        # 清理资源
        try:
            await downloader.close()
            await proxy_middleware.close()
        except:
            pass


async def test_httpx_with_proxy_async(proxy_list, target_url):
    """测试httpx下载器与代理的适配性"""
    print(f"\n=== 测试 httpx 下载器与代理 ===")
    print(f"代理列表: {proxy_list}")
    print(f"目标URL: {target_url}")
    
    try:
        # 创建设置
        settings = create_test_settings(proxy_list=proxy_list)
        crawler = MockCrawler(settings)
        
        # 创建下载器
        downloader = HttpXDownloader(crawler)
        downloader.open()
        
        # 创建代理中间件
        from crawlo.middleware.simple_proxy import SimpleProxyMiddleware
        proxy_middleware = SimpleProxyMiddleware(settings, "DEBUG")
        
        # 创建请求
        request = Request(url=target_url)
        
        # 创建模拟爬虫
        spider = MockSpider(crawler)
        
        # 通过代理中间件处理请求
        await proxy_middleware.process_request(request, spider)
        
        if request.proxy:
            print(f"✓ 代理已成功设置: {request.proxy}")
        else:
            print("代理未设置")
            
        # 尝试下载
        try:
            response = await downloader.download(request)
            if response and response.status_code:
                print(f"✓ 下载成功，状态码: {response.status_code}")
                # 只检查状态码，避免编码问题
                return True
            else:
                print("✗ 下载失败，响应为空")
                return False
        except Exception as e:
            print(f"✗ 下载过程中出错: {e}")
            return False
            
    except Exception as e:
        print(f"✗ 测试httpx时出错: {e}")
        return False
    finally:
        # 清理资源
        try:
            await downloader.close()
        except:
            pass


async def test_curl_cffi_with_proxy_async(proxy_url, target_url):
    """测试curl-cffi下载器与代理的适配性"""
    print(f"\n=== 测试 curl-cffi 下载器与代理 ===")
    print(f"代理URL: {proxy_url}")
    print(f"目标URL: {target_url}")
    
    try:
        # 创建设置
        settings = create_test_settings(proxy_url=proxy_url)
        crawler = MockCrawler(settings)
        
        # 创建下载器
        downloader = CurlCffiDownloader(crawler)
        downloader.open()
        
        # 创建代理中间件
        proxy_middleware = ProxyMiddleware(settings, "DEBUG")
        
        # 创建请求
        request = Request(url=target_url)
        
        # 创建模拟爬虫
        spider = MockSpider(crawler)
        
        # 通过代理中间件处理请求
        await proxy_middleware.process_request(request, spider)
        
        if request.proxy:
            print(f"✓ 代理已成功设置: {request.proxy}")
        else:
            print("代理未设置")
            
        # 尝试下载
        try:
            response = await downloader.download(request)
            if response and response.status_code:
                print(f"✓ 下载成功，状态码: {response.status_code}")
                # 只检查状态码，避免编码问题
                return True
            else:
                print("✗ 下载失败，响应为空")
                return False
        except Exception as e:
            print(f"✗ 下载过程中出错: {e}")
            return False
            
    except Exception as e:
        print(f"✗ 测试curl-cffi时出错: {e}")
        return False
    finally:
        # 清理资源
        try:
            await downloader.close()
            await proxy_middleware.close()
        except:
            pass


async def main():
    """主测试函数"""
    print("开始测试代理中间件与三个下载器的兼容性...")
    
    # 使用测试代理URL（这里使用一个公开的测试代理）
    # 注意：在实际使用中，您需要替换为有效的代理URL
    test_proxy_url = "http://test.proxy.api:8080/proxy/getitem/"
    test_proxy_list = ["http://proxy1:8080", "http://proxy2:8080"]
    test_target_url = "https://httpbin.org/ip"  # 一个返回IP信息的测试站点
    
    print(f"测试代理API: {test_proxy_url}")
    print(f"测试代理列表: {test_proxy_list}")
    print(f"测试目标URL: {test_target_url}")
    
    # 测试aiohttp下载器（使用高级代理）
    aiohttp_result = await test_aiohttp_with_proxy(test_proxy_url, test_target_url)
    
    # 测试httpx下载器（使用简化代理）
    httpx_result = await test_httpx_with_proxy_async(test_proxy_list, test_target_url)
    
    # 测试curl-cffi下载器（使用高级代理）
    curl_cffi_result = await test_curl_cffi_with_proxy_async(test_proxy_url, test_target_url)
    
    # 汇总结果
    print("\n" + "="*50)
    print("测试结果汇总:")
    print(f"aiohttp 下载器 (高级代理): {'✓ 通过' if aiohttp_result else '✗ 失败'}")
    print(f"httpx 下载器 (简化代理): {'✓ 通过' if httpx_result else '✗ 失败'}")
    print(f"curl-cffi 下载器 (高级代理): {'✓ 通过' if curl_cffi_result else '✗ 失败'}")
    
    overall_result = all([aiohttp_result, httpx_result, curl_cffi_result])
    print(f"\n总体结果: {'✓ 所有下载器都适配代理中间件' if overall_result else '✗ 部分下载器不兼容'}")
    
    return overall_result


if __name__ == "__main__":
    asyncio.run(main())