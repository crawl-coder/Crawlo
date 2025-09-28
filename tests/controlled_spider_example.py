#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受控爬虫混入类使用示例
演示如何使用 ControlledRequestMixin 和 AsyncControlledRequestMixin 来控制大规模请求生成
"""

import asyncio
from crawlo.spider import Spider
from crawlo.network import Request
from crawlo.utils.controlled_spider_mixin import ControlledRequestMixin, AsyncControlledRequestMixin


class LargeScaleSpider(Spider, ControlledRequestMixin):
    """
    同步版本的受控爬虫示例
    适用于需要生成大量请求但要控制并发的场景
    """
    name = 'large_scale_spider'
    
    def __init__(self):
        Spider.__init__(self)
        ControlledRequestMixin.__init__(self)
        
        # 配置受控生成参数
        self.max_pending_requests = 150     # 最大待处理请求数
        self.batch_size = 75               # 每批生成请求数
        self.generation_interval = 0.02     # 生成间隔（秒）
        self.backpressure_threshold = 300   # 背压阈值
    
    def _original_start_requests(self):
        """
        提供原始的大量请求
        这里模拟爬取一个电商网站的商品页面
        """
        # 模拟爬取 10,000 个商品页面
        base_urls = [
            "https://example-shop.com/products",
            "https://example-shop.com/electronics", 
            "https://example-shop.com/clothing",
            "https://example-shop.com/books",
            "https://example-shop.com/home"
        ]
        
        for category in base_urls:
            # 每个分类爬取 2000 页
            for page in range(1, 2001):
                yield Request(
                    url=f"{category}?page={page}",
                    callback=self.parse_product_list,
                    meta={'category': category.split('/')[-1], 'page': page}
                )
    
    def _process_request_before_yield(self, request):
        """
        在 yield 请求前进行处理
        可以添加去重、优先级设置、请求头设置等逻辑
        """
        # 设置请求头
        request.headers.setdefault('User-Agent', 
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # 根据分类设置优先级
        category = request.meta.get('category', '')
        if category == 'electronics':
            request.priority = 10  # 电子产品优先级最高
        elif category == 'clothing':
            request.priority = 8
        else:
            request.priority = 5
        
        # 可以在这里添加去重逻辑
        # if self.is_duplicate_request(request):
        #     return None  # 跳过重复请求
        
        return request
    
    async def parse_product_list(self, response):
        """解析商品列表页面"""
        # 提取商品链接
        product_links = response.css('a.product-link::attr(href)').getall()
        
        for link in product_links:
            # 生成商品详情页请求
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_product_detail,
                meta={'category': response.meta['category']}
            )
        
        # 提取分页信息
        next_page = response.css('a.next-page::attr(href)').get()
        if next_page:
            yield Request(
                url=response.urljoin(next_page),
                callback=self.parse_product_list,
                meta=response.meta
            )
    
    async def parse_product_detail(self, response):
        """解析商品详情页面"""
        yield {
            'title': response.css('h1.product-title::text').get(),
            'price': response.css('.price::text').re_first(r'\d+\.?\d*'),
            'description': response.css('.product-description::text').get(),
            'category': response.meta['category'],
            'url': response.url,
            'in_stock': 'in-stock' in response.css('.availability::attr(class)').get(''),
            'rating': response.css('.rating::attr(data-rating)').get(),
            'reviews_count': response.css('.reviews-count::text').re_first(r'\d+')
        }


class AsyncLargeScaleSpider(Spider, AsyncControlledRequestMixin):
    """
    异步版本的受控爬虫示例
    使用异步控制来实现更精确的并发管理
    """
    name = 'async_large_scale_spider'
    
    def __init__(self):
        Spider.__init__(self)
        AsyncControlledRequestMixin.__init__(self)
        
        # 配置异步控制参数
        self.max_concurrent_generations = 15    # 最大同时生成数
        self.queue_monitor_interval = 0.5       # 队列监控间隔
    
    def _original_start_requests(self):
        """
        提供原始的大量请求
        这里模拟爬取新闻网站的文章
        """
        # 模拟爬取 50,000 篇新闻文章
        news_sites = [
            "https://news-site-1.com",
            "https://news-site-2.com", 
            "https://news-site-3.com",
            "https://tech-news.com",
            "https://finance-news.com"
        ]
        
        categories = ['tech', 'finance', 'sports', 'politics', 'entertainment']
        
        for site in news_sites:
            for category in categories:
                # 每个分类爬取 2000 页
                for page in range(1, 2001):
                    yield Request(
                        url=f"{site}/{category}?page={page}",
                        callback=self.parse_article_list,
                        meta={'site': site, 'category': category, 'page': page}
                    )
    
    def _process_request_before_yield(self, request):
        """异步版本的请求预处理"""
        # 设置请求头
        request.headers.setdefault('User-Agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # 根据新闻类型设置优先级
        category = request.meta.get('category', '')
        if category in ['tech', 'finance']:
            request.priority = 10  # 科技和财经新闻优先级最高
        elif category in ['sports', 'politics']:
            request.priority = 8
        else:
            request.priority = 5
        
        # 设置延迟（避免对服务器造成过大压力）
        site = request.meta.get('site', '')
        if 'tech-news.com' in site:
            request.meta['download_delay'] = 0.5  # 科技新闻站点较敏感，增加延迟
        
        return request
    
    async def parse_article_list(self, response):
        """解析文章列表页面"""
        # 提取文章链接
        article_links = response.css('a.article-link::attr(href)').getall()
        
        for link in article_links:
            yield Request(
                url=response.urljoin(link),
                callback=self.parse_article_detail,
                meta={
                    'site': response.meta['site'],
                    'category': response.meta['category']
                }
            )
    
    async def parse_article_detail(self, response):
        """解析文章详情页面"""
        yield {
            'title': response.css('h1.article-title::text').get(),
            'content': ' '.join(response.css('.article-content p::text').getall()),
            'author': response.css('.author::text').get(),
            'publish_date': response.css('.publish-date::attr(datetime)').get(),
            'category': response.meta['category'],
            'site': response.meta['site'],
            'url': response.url,
            'tags': response.css('.tags a::text').getall(),
            'views': response.css('.views-count::text').re_first(r'\d+'),
            'comments': response.css('.comments-count::text').re_first(r'\d+')
        }
