#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用重构后框架的爬虫示例
"""

from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.items import Item


class OfweekSpider(Spider):
    """示例爬虫 - 使用新的框架特性"""
    
    name = 'ofweek_refactored'
    
    def start_requests(self):
        """生成初始请求"""
        yield Request(
            url='https://ee.ofweek.com/',
            callback=self.parse_list
        )
    
    def parse_list(self, response):
        """解析列表页"""
        # 提取文章链接
        article_links = response.css('a[href*="/ART-"]::attr(href)').getall()
        
        for link in article_links[:5]:  # 限制数量用于演示
            full_url = response.urljoin(link)
            yield Request(
                url=full_url,
                callback=self.parse_article
            )
    
    def parse_article(self, response):
        """解析文章页"""
        yield Item({
            'title': response.css('h1::text').get('').strip(),
            'url': response.url,
            'content': ' '.join(response.css('.content p::text').getall()),
            'publish_time': response.css('.time::text').get('').strip()
        })