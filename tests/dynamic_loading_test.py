#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
动态加载功能测试示例
==================
测试新添加的动态加载功能是否符合预期
"""
import asyncio
from crawlo import Spider, Request


class TabControlTestSpider(Spider):
    """标签页控制测试爬虫"""
    name = 'tab_control_test_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 3,  # 限制最大页面数为3
    }
    
    def start_requests(self):
        # 测试多个URL，验证标签页控制功能
        urls = [
            'https://httpbin.org/html',  # 简单HTML页面
            'https://httpbin.org/json',  # JSON页面
            'https://httpbin.org/xml',   # XML页面
            'https://httpbin.org/robots.txt',  # 文本页面
            'https://httpbin.org/headers',  # 请求头页面
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        print(f"成功下载页面: {response.url}")
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容长度: {len(response.text)}")
        yield {'url': response.url, 'status': response.status_code}


class PaginationTestSpider(Spider):
    """翻页功能测试爬虫"""
    name = 'pagination_test_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,
    }
    
    def start_requests(self):
        # 测试带有翻页操作的请求
        request = Request(
            url='https://httpbin.org/html',
            callback=self.parse_with_pagination
        ).set_dynamic_loader(
            True,
            {
                "pagination_actions": [
                    # 模拟鼠标滑动
                    {
                        "type": "scroll",
                        "params": {
                            "count": 2,
                            "distance": 300,
                            "delay": 500
                        }
                    }
                ]
            }
        )
        yield request
    
    def parse_with_pagination(self, response):
        """解析带翻页操作的响应"""
        print(f"成功下载页面: {response.url}")
        yield {'url': response.url, 'status': response.status_code}


# 运行测试
async def run_tests():
    """运行测试"""
    print("=== 动态加载功能测试 ===\n")
    
    # 测试1: 标签页控制功能
    print("1. 测试标签页控制功能:")
    print("   配置最大页面数为3，请求5个URL")
    print("   预期结果: 正常下载所有页面，但只创建3个标签页\n")
    
    # 测试2: 翻页功能
    print("2. 测试翻页功能:")
    print("   配置鼠标滑动翻页操作")
    print("   预期结果: 页面加载完成后执行滑动操作\n")
    
    print("请运行以下命令来执行测试:")
    print("crawlo crawl tab_control_test_spider")
    print("crawlo crawl pagination_test_spider")


if __name__ == '__main__':
    asyncio.run(run_tests())