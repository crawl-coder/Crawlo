#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
动态加载场景使用示例
==================
展示如何在不同动态加载场景下使用 Crawlo 框架

场景说明:
1. 列表页、详情页都要动态加载
2. 列表页使用协议请求、详情页使用动态加载
3. 列表页使用动态加载，详情页使用协议请求
"""
import asyncio
from crawlo import Spider, Request
from crawlo.tools.scenario_adapter import create_scenario_adapter, create_adapter_for_platform


class DynamicLoadingSpider(Spider):
    """动态加载示例爬虫"""
    name = 'dynamic_loading_spider'
    
    # 自定义配置使用混合下载器
    custom_settings = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
        # 可以根据需要添加更多配置
    }
    
    def __init__(self):
        super().__init__()
        # 创建场景适配器
        self.scenario_adapter = create_adapter_for_platform("电商网站")
        # 或者使用自定义场景
        # self.scenario_adapter = create_scenario_adapter("list_protocol_detail_dynamic")
    
    def start_requests(self):
        """生成起始请求"""
        # 电商网站示例URL
        urls = [
            'https://example-shop.com/products/list',  # 列表页 - 使用协议请求
            'https://example-shop.com/product/12345',  # 详情页 - 使用动态加载
            'https://example-shop.com/product/67890',  # 详情页 - 使用动态加载
        ]
        
        for url in urls:
            request = Request(url=url, callback=self.parse)
            # 使用场景适配器自动配置请求
            self.scenario_adapter.adapt_request(request)
            yield request
    
    def parse(self, response):
        """解析响应"""
        # 根据URL类型处理不同页面
        if '/products/list' in response.url:
            # 处理列表页
            self.parse_list_page(response)
        elif '/product/' in response.url:
            # 处理详情页
            self.parse_detail_page(response)
    
    def parse_list_page(self, response):
        """解析列表页"""
        print(f"Parsing list page: {response.url}")
        
        # 提取产品链接
        product_links = response.css('a.product-link::attr(href)').getall()
        for link in product_links:
            # 构造完整URL
            full_url = response.urljoin(link)
            
            # 创建详情页请求
            request = Request(url=full_url, callback=self.parse)
            
            # 使用场景适配器配置请求（自动使用动态加载器）
            self.scenario_adapter.adapt_request(request)
            
            yield request
    
    def parse_detail_page(self, response):
        """解析详情页"""
        print(f"Parsing detail page: {response.url}")
        
        # 提取产品信息
        product_data = {
            'name': response.css('h1.product-name::text').get(),
            'price': response.css('.price::text').get(),
            'description': response.css('.description::text').get(),
            'images': response.css('img.product-image::attr(src)').getall(),
            'url': response.url
        }
        
        # 输出数据
        yield product_data


# 翻页和多标签页示例
class PaginationSpider(Spider):
    """翻页示例爬虫"""
    name = 'pagination_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': False,  # 为了演示效果，使用非无头模式
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,  # 启用单浏览器多标签页模式
        'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 5,  # 最多5个标签页
    }
    
    def start_requests(self):
        # 社交媒体网站示例URL（需要翻页）
        url = 'https://social-media.com/feed'
        
        # 创建带有翻页操作的请求
        request = Request(
            url=url,
            callback=self.parse_feed
        ).set_dynamic_loader(
            True, 
            {
                # 定义翻页操作
                "pagination_actions": [
                    # 鼠标滑动翻页：滑动3次，每次滑动500像素，间隔1秒
                    {
                        "type": "scroll",
                        "params": {
                            "count": 3,
                            "distance": 500,
                            "delay": 1000
                        }
                    },
                    # 鼠标点击翻页按钮：点击"加载更多"按钮2次，间隔2秒
                    {
                        "type": "click",
                        "params": {
                            "selector": ".load-more-button",
                            "count": 2,
                            "delay": 2000
                        }
                    }
                ]
            }
        )
        
        yield request
    
    def parse_feed(self, response):
        """解析动态加载的feed页面"""
        print(f"Parsing feed page: {response.url}")
        
        # 提取帖子信息
        posts = response.css('.post-item')
        for post in posts:
            post_data = {
                'id': post.css('.post-id::text').get(),
                'content': post.css('.post-content::text').get(),
                'author': post.css('.post-author::text').get(),
                'timestamp': post.css('.post-timestamp::text').get(),
            }
            yield post_data


# 标签页控制示例
class TabControlSpider(Spider):
    """标签页控制示例爬虫"""
    name = 'tab_control_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 3,  # 限制最大页面数为3
    }
    
    def start_requests(self):
        # 请求多个URL来测试标签页控制
        urls = [
            'https://httpbin.org/html',
            'https://httpbin.org/json',
            'https://httpbin.org/xml',
            'https://httpbin.org/robots.txt',
            'https://httpbin.org/headers',
        ]
        
        for url in urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response):
        """解析响应"""
        print(f"成功下载页面: {response.url}")
        yield {'url': response.url, 'status': response.status_code}


# 翻页操作详细示例
class PaginationDetailSpider(Spider):
    """翻页操作详细示例爬虫"""
    name = 'pagination_detail_spider'
    
    custom_settings = {
        'DOWNLOADER_TYPE': 'playwright',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_HEADLESS': True,
        'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 3,
    }
    
    def start_requests(self):
        # 示例1: 鼠标滑动翻页
        scroll_request = Request(
            url='https://example.com/infinite-scroll-page',
            callback=self.parse_scroll
        ).set_dynamic_loader(
            True,
            {
                "pagination_actions": [
                    # 滑动翻页：滑动5次，每次滑动300像素，间隔500毫秒
                    {
                        "type": "scroll",
                        "params": {
                            "count": 5,
                            "distance": 300,
                            "delay": 500
                        }
                    }
                ]
            }
        )
        
        # 示例2: 鼠标点击翻页
        click_request = Request(
            url='https://example.com/click-pagination-page',
            callback=self.parse_click
        ).set_dynamic_loader(
            True,
            {
                "pagination_actions": [
                    # 点击翻页：点击"下一页"按钮3次，每次间隔1秒
                    {
                        "type": "click",
                        "params": {
                            "selector": "a.next-page",
                            "count": 3,
                            "delay": 1000
                        }
                    }
                ]
            }
        )
        
        # 示例3: 组合翻页操作
        combined_request = Request(
            url='https://example.com/combined-pagination-page',
            callback=self.parse_combined
        ).set_dynamic_loader(
            True,
            {
                "pagination_actions": [
                    # 先滑动2次
                    {
                        "type": "scroll",
                        "params": {
                            "count": 2,
                            "distance": 500,
                            "delay": 1000
                        }
                    },
                    # 再点击按钮
                    {
                        "type": "click",
                        "params": {
                            "selector": ".load-more",
                            "count": 1,
                            "delay": 2000
                        }
                    },
                    # 再滑动1次
                    {
                        "type": "scroll",
                        "params": {
                            "count": 1,
                            "distance": 300,
                            "delay": 1000
                        }
                    }
                ]
            }
        )
        
        yield scroll_request
        yield click_request
        yield combined_request
    
    def parse_scroll(self, response):
        """解析滑动翻页结果"""
        print(f"滑动翻页完成: {response.url}")
        # 提取数据
        items = response.css('.item').getall()
        print(f"  滑动后获取到 {len(items)} 个项目")
        yield {'url': response.url, 'type': 'scroll', 'item_count': len(items)}
    
    def parse_click(self, response):
        """解析点击翻页结果"""
        print(f"点击翻页完成: {response.url}")
        # 提取数据
        items = response.css('.item').getall()
        print(f"  点击后获取到 {len(items)} 个项目")
        yield {'url': response.url, 'type': 'click', 'item_count': len(items)}
    
    def parse_combined(self, response):
        """解析组合翻页结果"""
        print(f"组合翻页完成: {response.url}")
        # 提取数据
        items = response.css('.item').getall()
        print(f"  组合操作后获取到 {len(items)} 个项目")
        yield {'url': response.url, 'type': 'combined', 'item_count': len(items)}


# 不同场景的配置示例
def get_scenario_configurations():
    """获取不同场景的配置示例"""
    
    # 场景1: 全动态加载
    all_dynamic_config = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
        **create_scenario_adapter("all_dynamic").get_settings()
    }
    
    # 场景2: 列表页协议，详情页动态
    list_protocol_detail_dynamic_config = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'httpx',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'selenium',
        **create_scenario_adapter("list_protocol_detail_dynamic").get_settings()
    }
    
    # 场景3: 列表页动态，详情页协议
    list_dynamic_detail_protocol_config = {
        'DOWNLOADER_TYPE': 'hybrid',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'playwright',
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'aiohttp',
        **create_scenario_adapter("list_dynamic_detail_protocol").get_settings()
    }
    
    return {
        "all_dynamic": all_dynamic_config,
        "list_protocol_detail_dynamic": list_protocol_detail_dynamic_config,
        "list_dynamic_detail_protocol": list_dynamic_detail_protocol_config
    }


# 使用不同场景的示例爬虫
class AllDynamicSpider(Spider):
    """全动态加载爬虫"""
    name = 'all_dynamic_spider'
    
    custom_settings = get_scenario_configurations()["all_dynamic"]
    
    def start_requests(self):
        urls = [
            'https://social-media.com/feed',      # 动态加载的feed页面
            'https://social-media.com/post/123',  # 动态加载的帖子页面
        ]
        
        adapter = create_scenario_adapter("all_dynamic")
        for url in urls:
            request = Request(url=url, callback=self.parse)
            adapter.adapt_request(request)
            yield request
    
    def parse(self, response):
        print(f"Parsing dynamic page: {response.url}")
        # 解析逻辑...


class ListProtocolDetailDynamicSpider(Spider):
    """列表页协议，详情页动态爬虫"""
    name = 'list_protocol_detail_dynamic_spider'
    
    custom_settings = get_scenario_configurations()["list_protocol_detail_dynamic"]
    
    def start_requests(self):
        urls = [
            'https://news-site.com/articles',        # 协议请求的列表页
            'https://news-site.com/article/123',     # 动态加载的详情页
        ]
        
        adapter = create_scenario_adapter("list_protocol_detail_dynamic")
        for url in urls:
            request = Request(url=url, callback=self.parse)
            adapter.adapt_request(request)
            yield request
    
    def parse(self, response):
        print(f"Parsing page: {response.url}")
        # 解析逻辑...


class ListDynamicDetailProtocolSpider(Spider):
    """列表页动态，详情页协议爬虫"""
    name = 'list_dynamic_detail_protocol_spider'
    
    custom_settings = get_scenario_configurations()["list_dynamic_detail_protocol"]
    
    def start_requests(self):
        urls = [
            'https://blog-platform.com/posts',       # 动态加载的列表页
            'https://blog-platform.com/2023/01/01/article',  # 协议请求的详情页
        ]
        
        adapter = create_scenario_adapter("list_dynamic_detail_protocol")
        for url in urls:
            request = Request(url=url, callback=self.parse)
            adapter.adapt_request(request)
            yield request
    
    def parse(self, response):
        print(f"Parsing page: {response.url}")
        # 解析逻辑...


# 手动指定下载器的示例
def manual_downloader_example():
    """手动指定下载器的示例"""
    # 强制使用动态加载器（带翻页操作）
    dynamic_request = Request(
        url='https://example.com/dynamic-page',
        callback=lambda response: print(f"Dynamic content: {response.text[:100]}")
    ).set_dynamic_loader(
        True, 
        {
            # 定义翻页操作
            "pagination_actions": [
                # 鼠标滑动翻页
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
    
    # 强制使用协议加载器
    protocol_request = Request(
        url='https://example.com/static-page',
        callback=lambda response: print(f"Static content: {response.text[:100]}")
    ).set_protocol_loader()
    
    return [dynamic_request, protocol_request]


# 运行示例
async def run_examples():
    """运行示例"""
    print("=== 动态加载场景示例 ===\n")
    
    # 1. 基本场景适配器使用
    print("1. 基本场景适配器使用:")
    adapter = create_scenario_adapter("list_protocol_detail_dynamic")
    settings = adapter.get_settings()
    print(f"   配置设置: {settings}\n")
    
    # 2. 平台特定适配器使用
    print("2. 平台特定适配器使用:")
    ecommerce_adapter = create_adapter_for_platform("电商网站")
    news_adapter = create_adapter_for_platform("新闻网站")
    print(f"   电商网站配置: {ecommerce_adapter.get_settings()}")
    print(f"   新闻网站配置: {news_adapter.get_settings()}\n")
    
    # 3. 手动指定下载器
    print("3. 手动指定下载器:")
    manual_requests = manual_downloader_example()
    for req in manual_requests:
        print(f"   请求 {req.url} 使用动态加载器: {req.use_dynamic_loader}")
    print()
    
    # 4. 翻页操作示例
    print("4. 翻页操作示例:")
    pagination_request = Request(url="https://example.com/feed")
    pagination_request.set_dynamic_loader(True, {
        "pagination_actions": [
            {
                "type": "scroll",
                "params": {"count": 3, "distance": 500, "delay": 1000}
            },
            {
                "type": "click",
                "params": {"selector": ".load-more", "count": 2, "delay": 2000}
            }
        ]
    })
    print(f"   翻页请求配置: {pagination_request.dynamic_loader_options}")
    
    # 5. 标签页控制示例
    print("5. 标签页控制示例:")
    print("   配置 PLAYWRIGHT_MAX_PAGES_PER_BROWSER = 3")
    print("   请求5个URL，但只会创建3个标签页")
    
    # 6. 翻页操作详细示例
    print("6. 翻页操作详细示例:")
    print("   包含滑动翻页、点击翻页和组合翻页操作")
    print("   滑动翻页：通过鼠标滚轮或页面滚动条向下滚动加载更多内容")
    print("   点击翻页：通过点击'下一页'或'加载更多'按钮加载内容")
    print("   组合翻页：结合滑动和点击操作，处理复杂的翻页场景")
    
    # 7. 翻页操作参数说明
    print("\n7. 翻页操作参数说明:")
    print("   滑动翻页参数:")
    print("     - count: 滑动次数")
    print("     - distance: 每次滑动距离（像素）")
    print("     - delay: 每次滑动后的等待时间（毫秒）")
    print("   点击翻页参数:")
    print("     - selector: 点击元素的选择器")
    print("     - count: 点击次数")
    print("     - delay: 每次点击后的等待时间（毫秒）")


if __name__ == '__main__':
    asyncio.run(run_examples())