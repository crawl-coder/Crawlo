#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
代理API测试脚本
================
测试指定的代理API接口是否能正常工作
"""

import asyncio
import aiohttp
import sys
import os
from urllib.parse import urlparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.proxy import ProxyMiddleware
from crawlo.network.request import Request
from crawlo.settings.setting_manager import SettingManager


async def test_proxy_api(proxy_api_url):
    """测试代理API接口"""
    print(f"=== 测试代理API接口 ===")
    print(f"API地址: {proxy_api_url}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(proxy_api_url) as response:
                print(f"状态码: {response.status}")
                print(f"响应头: {response.headers.get('content-type', 'Unknown')}")
                
                # 尝试解析JSON响应
                try:
                    data = await response.json()
                    print(f"响应数据: {data}")
                    return data
                except Exception as e:
                    # 如果不是JSON，尝试获取文本
                    try:
                        text = await response.text()
                        print(f"响应文本: {text[:200]}{'...' if len(text) > 200 else ''}")
                        return text
                    except Exception as e2:
                        print(f"无法解析响应内容: {e2}")
                        return None
                        
    except asyncio.TimeoutError:
        print("请求超时")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None


def extract_proxy_url(proxy_data):
    """从API响应中提取代理URL"""
    proxy_url = None
    
    if isinstance(proxy_data, dict):
        # 检查是否有status字段且为成功状态
        if proxy_data.get('status') == 0:
            # 获取proxy字段
            proxy_info = proxy_data.get('proxy', {})
            if isinstance(proxy_info, dict):
                # 优先使用https代理，否则使用http代理
                proxy_url = proxy_info.get('https') or proxy_info.get('http')
            elif isinstance(proxy_info, str):
                proxy_url = proxy_info
        else:
            # 直接尝试常见的字段名
            for key in ['proxy', 'data', 'url', 'http', 'https']:
                if key in proxy_data:
                    value = proxy_data[key]
                    if isinstance(value, str):
                        proxy_url = value
                        break
                    elif isinstance(value, dict):
                        proxy_url = value.get('https') or value.get('http')
                        break
        
        # 如果还是没有找到，尝试更深层的嵌套
        if not proxy_url:
            for key, value in proxy_data.items():
                if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    proxy_url = value
                    break
                elif isinstance(value, dict):
                    # 递归查找
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str) and (sub_value.startswith('http://') or sub_value.startswith('https://')):
                            proxy_url = sub_value
                            break
                    if proxy_url:
                        break
    
    elif isinstance(proxy_data, str):
        # 如果响应是字符串，直接使用
        if proxy_data.startswith('http://') or proxy_data.startswith('https://'):
            proxy_url = proxy_data
    
    return proxy_url


async def test_target_url_without_proxy(target_url):
    """不使用代理直接测试访问目标URL"""
    print(f"\n=== 直接访问目标URL（不使用代理） ===")
    print(f"目标URL: {target_url}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 添加用户代理头，避免被反爬虫机制拦截
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            async with session.get(target_url, headers=headers) as response:
                print(f"状态码: {response.status}")
                print(f"响应头: {response.headers.get('content-type', 'Unknown')}")
                
                # 只读取响应状态，不尝试解码内容
                return response.status == 200
                
    except asyncio.TimeoutError:
        print("请求超时")
        return False
    except Exception as e:
        print(f"请求失败: {e}")
        return False


async def test_target_url_with_proxy(proxy_url, target_url, max_retries=3):
    """使用代理测试访问目标URL"""
    print(f"\n=== 使用代理测试访问目标URL ===")
    print(f"代理地址: {proxy_url}")
    print(f"目标URL: {target_url}")
    
    # 添加用户代理头，避免被反爬虫机制拦截
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        if attempt > 0:
            print(f"\n第 {attempt + 1} 次重试...")
        
        try:
            # 创建aiohttp客户端会话
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # 处理代理URL，支持带认证的代理
                if isinstance(proxy_url, str) and "@" in proxy_url and "://" in proxy_url:
                    parsed = urlparse(proxy_url)
                    if parsed.username and parsed.password:
                        # 提取认证信息
                        auth = aiohttp.BasicAuth(parsed.username, parsed.password)
                        # 清理代理URL，移除认证信息
                        clean_proxy = f"{parsed.scheme}://{parsed.hostname}"
                        if parsed.port:
                            clean_proxy += f":{parsed.port}"
                        
                        print(f"使用带认证的代理: {clean_proxy}")
                        async with session.get(target_url, proxy=clean_proxy, proxy_auth=auth) as response:
                            print(f"状态码: {response.status}")
                            print(f"响应头: {response.headers.get('content-type', 'Unknown')}")
                            return response.status == 200
                    else:
                        # 没有认证信息的代理
                        print(f"使用普通代理: {proxy_url}")
                        async with session.get(target_url, proxy=proxy_url) as response:
                            print(f"状态码: {response.status}")
                            print(f"响应头: {response.headers.get('content-type', 'Unknown')}")
                            return response.status == 200
                else:
                    # 直接使用代理URL
                    print(f"使用代理: {proxy_url}")
                    async with session.get(target_url, proxy=proxy_url) as response:
                        print(f"状态码: {response.status}")
                        print(f"响应头: {response.headers.get('content-type', 'Unknown')}")
                        return response.status == 200
                        
        except asyncio.TimeoutError:
            print("请求超时")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
        except aiohttp.ClientConnectorError as e:
            print(f"连接错误: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
        except aiohttp.ClientHttpProxyError as e:
            print(f"代理HTTP错误: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
        except aiohttp.ServerDisconnectedError as e:
            print(f"服务器断开连接: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
        except Exception as e:
            print(f"请求失败: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
    
    return False


async def main():
    """主测试函数"""
    # 指定的代理API和测试链接
    proxy_api = 'http://test.proxy.api:8080/proxy/getitem/'
    target_url = 'https://stock.10jqka.com.cn/20240315/c655957791.shtml'
    
    print("开始测试代理接口和目标链接访问...\n")
    
    # 1. 测试代理API接口
    proxy_data = await test_proxy_api(proxy_api)
    
    if not proxy_data:
        print("代理API测试失败，无法获取代理信息")
        return
    
    # 2. 从API响应中提取代理URL
    proxy_url = extract_proxy_url(proxy_data)
    
    if not proxy_url:
        print("无法从API响应中提取代理URL")
        print(f"API响应内容: {proxy_data}")
        return
    
    print(f"\n提取到的代理URL: {proxy_url}")
    
    # 3. 首先尝试直接访问，确认目标URL是否可访问
    print("\n=== 测试直接访问目标URL ===")
    direct_success = await test_target_url_without_proxy(target_url)
    
    if direct_success:
        print("直接访问目标URL成功")
    else:
        print("直接访问目标URL失败")
    
    # 4. 使用代理访问目标URL
    print("\n=== 测试使用代理访问目标URL ===")
    proxy_success = await test_target_url_with_proxy(proxy_url, target_url)
    
    if proxy_success:
        print(f"代理测试成功！代理 {proxy_url} 可以正常访问目标链接")
    else:
        print(f"代理测试失败！代理 {proxy_url} 无法访问目标链接")
        
    # 5. 总结
    print(f"\n=== 测试总结 ===")
    print(f"代理API访问: {'成功' if proxy_data else '失败'}")
    print(f"代理提取: {'成功' if proxy_url else '失败'}")
    print(f"直接访问: {'成功' if direct_success else '失败'}")
    print(f"代理访问: {'成功' if proxy_success else '失败'}")


if __name__ == "__main__":
    asyncio.run(main())