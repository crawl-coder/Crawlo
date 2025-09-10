#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
实际测试动态下载器（Playwright）通过代理访问网站
"""

import asyncio
from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.tools import AuthenticatedProxy


class ProxyTestSpider(Spider):
    """代理测试爬虫"""
    name = "proxy_test_spider"  # 添加name属性
    
    # 自定义配置
    custom_settings = {
        "DOWNLOADER_TYPE": "playwright",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_HEADLESS": True,
        # 配置带认证的代理
        "PLAYWRIGHT_PROXY": {
            "server": "http://182.201.243.186:58111",
            "username": "dwe20241014",
            "password": "Dwe0101014"
        }
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("代理测试爬虫初始化完成")
        print(f"代理配置: {self.custom_settings.get('PLAYWRIGHT_PROXY')}")

    def start_requests(self):
        """开始请求"""
        urls = [
            "https://httpbin.org/ip",  # 查看IP地址
            "https://httpbin.org/headers",  # 查看请求头
        ]
        
        for url in urls:
            request = Request(url, callback=self.parse)
            yield request

    def parse(self, response):
        """解析响应"""
        print(f"\n=== 响应信息 ===")
        print(f"URL: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")
        
        # 保存响应内容
        filename = response.url.split("/")[-1].replace("?", "_").replace("&", "_")
        with open(f"proxy_test_{filename}.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"响应已保存到 proxy_test_{filename}.html")
        
        # 返回一个简单的item
        yield {"url": response.url, "status": response.status_code}


# 异步运行函数
async def run_spider():
    """运行爬虫"""
    print("开始测试动态下载器通过代理访问网站...")
    
    # 创建爬虫实例
    spider = ProxyTestSpider()
    
    # 创建一个简单的crawler模拟器
    class MockCrawler:
        def __init__(self):
            from crawlo.settings.setting_manager import SettingManager
            self.settings = SettingManager()
            # 应用爬虫的自定义设置
            if hasattr(spider, 'custom_settings'):
                for key, value in spider.custom_settings.items():
                    self.settings.set(key, value)
    
    crawler = MockCrawler()
    
    # 创建爬虫实例并绑定crawler
    spider_instance = spider.create_instance(crawler)
    
    # 执行初始请求
    requests = list(spider_instance.start_requests())
    print(f"生成了 {len(requests)} 个请求")
    
    # 使用Playwright下载器处理请求
    try:
        from crawlo.downloader import PlaywrightDownloader
        downloader = PlaywrightDownloader(crawler)
        await downloader.download(requests[0])  # 测试第一个请求
        print("Playwright下载器测试成功!")
    except Exception as e:
        print(f"Playwright下载器测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n测试完成!")


async def main():
    """主函数"""
    await run_spider()


if __name__ == "__main__":
    asyncio.run(main())