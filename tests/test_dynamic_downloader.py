#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
动态下载器测试脚本
==================
测试 DynamicRenderMiddleware 和 PlaywrightDownloader 的使用

测试目标：https://www.infoq.cn/zones/harmonyos/latest

测试场景：
1. 默认不使用动态下载器（协议下载器）
2. 通过域名配置启用动态下载器
3. 通过请求标记启用动态下载器
4. PlaywrightDownloader 的增强功能测试
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo import Spider, Request
from crawlo.crawler import CrawlerProcess


# ========================================
# 测试场景 1：默认使用协议下载器（不启用动态）
# ========================================
class ProtocolDownloaderSpider(Spider):
    """默认使用协议下载器的测试"""
    name = 'protocol_test'
    
    custom_settings = {
        'DOWNLOADER': 'crawlo.downloader.HybridDownloader',
        'LOG_LEVEL': 'DEBUG',
        'CONCURRENCY': 1,
        'DOWNLOAD_DELAY': 1,
        # DynamicRenderMiddleware 配置
        'MIDDLEWARES': {
            'crawlo.middleware.DynamicRenderMiddleware': 350,
        },
        # 默认不使用动态下载器
        'DYNAMIC_RENDER_DEFAULT_DYNAMIC': False,
    }
    
    def start_requests(self):
        yield Request(url='https://www.infoq.cn/zones/harmonyos/latest', callback=self.parse)
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"[场景1] 协议下载器测试")
        print(f"URL: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"内容长度: {len(response.text)} 字符")
        print(f"使用动态下载器: {response.request.meta.get('use_dynamic_loader', False)}")
        
        # 提取标题
        title = response.xpath('//title/text()').get()
        print(f"页面标题: {title}")
        
        # 提取文章列表
        articles = response.css('a[href*="/article/"]::attr(href)').getall()
        print(f"找到文章链接数: {len(articles)}")
        print(f"{'='*60}\n")
        
        yield {'test': 'protocol', 'url': response.url, 'articles_count': len(articles)}


# ========================================
# 测试场景 2：通过域名配置启用动态下载器
# ========================================
class DynamicDownloaderSpider(Spider):
    """通过域名配置启用动态下载器"""
    name = 'dynamic_test'
    
    custom_settings = {
        'DOWNLOADER': 'crawlo.downloader.HybridDownloader',
        'LOG_LEVEL': 'DEBUG',
        'CONCURRENCY': 1,
        'DOWNLOAD_DELAY': 2,
        # DynamicRenderMiddleware 配置
        'MIDDLEWARES': {
            'crawlo.middleware.DynamicRenderMiddleware': 350,
        },
        # 配置 infoq.cn 域名使用动态下载器
        'DYNAMIC_RENDER_DOMAINS': ['www.infoq.cn'],
        # Playwright 配置
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,
        'PLAYWRIGHT_TIMEOUT': 30000,
        # 智能等待配置
        'PLAYWRIGHT_WAIT_STRATEGY': 'auto',
        'PLAYWRIGHT_WAIT_TIMEOUT': 10000,
        # 资源屏蔽（提升性能）
        'PLAYWRIGHT_BLOCK_RESOURCES': ['image', 'font', 'media'],
        'PLAYWRIGHT_BLOCK_ADS': True,
        # 反检测
        'PLAYWRIGHT_STEALTH_MODE': True,
    }
    
    def start_requests(self):
        yield Request(url='https://www.infoq.cn/zones/harmonyos/latest', callback=self.parse)
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"[场景2] 动态下载器测试（域名配置）")
        print(f"URL: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"内容长度: {len(response.text)} 字符")
        print(f"使用动态下载器: {response.request.meta.get('use_dynamic_loader', False)}")
        
        # 提取标题
        title = response.xpath('//title/text()').get()
        print(f"页面标题: {title}")
        
        # 提取文章列表
        articles = response.css('a[href*="/article/"]::attr(href)').getall()
        print(f"找到文章链接数: {len(articles)}")
        
        # 提取更多内容（动态加载后）
        content_blocks = response.css('.article-item, .content-item, [class*="article"]').getall()
        print(f"内容块数量: {len(content_blocks)}")
        print(f"{'='*60}\n")
        
        yield {'test': 'dynamic_domain', 'url': response.url, 'articles_count': len(articles)}


# ========================================
# 测试场景 3：通过请求标记启用动态下载器
# ========================================
class RequestMetaSpider(Spider):
    """通过请求标记启用动态下载器"""
    name = 'request_meta_test'
    
    custom_settings = {
        'DOWNLOADER': 'crawlo.downloader.HybridDownloader',
        'LOG_LEVEL': 'DEBUG',
        'CONCURRENCY': 1,
        'DOWNLOAD_DELAY': 2,
        # DynamicRenderMiddleware 配置
        'MIDDLEWARES': {
            'crawlo.middleware.DynamicRenderMiddleware': 350,
        },
        # 默认不使用动态下载器
        'DYNAMIC_RENDER_DEFAULT_DYNAMIC': False,
        # Playwright 配置
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,
        'PLAYWRIGHT_TIMEOUT': 30000,
        'PLAYWRIGHT_WAIT_STRATEGY': 'auto',
        'PLAYWRIGHT_BLOCK_RESOURCES': ['image', 'font', 'media'],
        'PLAYWRIGHT_STEALTH_MODE': True,
        # 自动滚动测试
        'PLAYWRIGHT_AUTO_SCROLL': True,
        'PLAYWRIGHT_SCROLL_COUNT': 2,
        'PLAYWRIGHT_SCROLL_DELAY': 500,
    }
    
    def start_requests(self):
        # 通过请求标记显式指定使用动态下载器
        yield Request(
            url='https://www.infoq.cn/zones/harmonyos/latest',
            callback=self.parse,
            meta={'use_dynamic_loader': True}  # 显式指定使用动态下载器
        )
    
    def parse(self, response):
        print(f"\n{'='*60}")
        print(f"[场景3] 动态下载器测试（请求标记）")
        print(f"URL: {response.url}")
        print(f"状态码: {response.status_code}")
        print(f"内容长度: {len(response.text)} 字符")
        print(f"使用动态下载器: {response.request.meta.get('use_dynamic_loader', False)}")
        
        # 提取标题
        title = response.xpath('//title/text()').get()
        print(f"页面标题: {title}")
        
        # 提取文章链接
        articles = response.css('a[href*="/article/"]::attr(href)').getall()
        print(f"找到文章链接数: {len(articles)}")
        
        # 打印前5篇文章链接
        for i, article in enumerate(articles[:5]):
            print(f"  文章{i+1}: {article}")
        print(f"{'='*60}\n")
        
        yield {'test': 'request_meta', 'url': response.url, 'articles_count': len(articles)}


def run_test_scenario(spider_class, description):
    """运行单个测试场景"""
    print(f"\n{'#'*70}")
    print(f"# 测试场景: {description}")
    print(f"{'#'*70}")
    
    process = CrawlerProcess()
    process.crawl(spider_class)
    process.start()


def main():
    """主测试入口"""
    print("\n" + "="*70)
    print("动态下载器测试脚本")
    print("测试目标: https://www.infoq.cn/zones/harmonyos/latest")
    print("="*70)
    
    print("\n请选择测试场景:")
    print("1. 协议下载器测试（默认不使用动态）")
    print("2. 动态下载器测试（域名配置）")
    print("3. 动态下载器测试（请求标记）")
    print("4. 运行所有测试")
    print("0. 退出")
    
    choice = input("\n请输入选项 [0-4]: ").strip()
    
    if choice == '1':
        run_test_scenario(ProtocolDownloaderSpider, "协议下载器测试")
    elif choice == '2':
        run_test_scenario(DynamicDownloaderSpider, "动态下载器（域名配置）")
    elif choice == '3':
        run_test_scenario(RequestMetaSpider, "动态下载器（请求标记）")
    elif choice == '4':
        print("\n运行所有测试场景...")
        run_test_scenario(ProtocolDownloaderSpider, "协议下载器测试")
        print("\n等待 3 秒后继续下一个测试...")
        import time
        time.sleep(3)
        run_test_scenario(DynamicDownloaderSpider, "动态下载器（域名配置）")
        print("\n等待 3 秒后继续下一个测试...")
        time.sleep(3)
        run_test_scenario(RequestMetaSpider, "动态下载器（请求标记）")
    elif choice == '0':
        print("退出测试")
        return
    else:
        print("无效选项")
        return
    
    print("\n测试完成!")


if __name__ == '__main__':
    main()
