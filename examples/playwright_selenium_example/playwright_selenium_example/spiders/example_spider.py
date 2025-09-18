# -*- coding: UTF-8 -*-
"""
示例爬虫 - 演示 Playwright 和 Selenium 下载器的使用
"""
from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.items.items import Item
from crawlo.items.fields import Field


class ExampleItem(Item):
    url = Field()
    title = Field()
    content_length = Field()


class ExampleSpider(Spider):
    name = 'example_spider'
    
    def start_requests(self):
        """开始请求"""
        # 测试静态内容网站
        yield Request(
            url='https://httpbin.org/html',
            callback=self.parse_static
        )
        
        # 测试需要 JavaScript 渲染的网站
        yield Request(
            url='https://httpbin.org/delay/2',
            callback=self.parse_dynamic,
            meta={
                # Playwright 自定义操作示例
                'playwright_actions': [
                    {
                        'type': 'wait',
                        'params': {
                            'timeout': 3000
                        }
                    }
                ],
                # Selenium 自定义脚本示例
                'selenium_scripts': [
                    {
                        'type': 'wait',
                        'content': 3
                    }
                ]
            }
        )
        
        # 测试需要滚动加载的页面
        yield Request(
            url='https://httpbin.org/html',
            callback=self.parse_scroll,
            meta={
                # Playwright 翻页操作示例
                'pagination_actions': [
                    {
                        'type': 'scroll',
                        'params': {
                            'count': 2,
                            'distance': 300,
                            'delay': 500
                        }
                    }
                ],
                # Selenium 翻页操作示例
                'selenium_scripts': [
                    {
                        'type': 'js',
                        'content': 'window.scrollTo(0, document.body.scrollHeight);'
                    }
                ]
            }
        )

    def parse_static(self, response):
        """解析静态内容"""
        self.logger.info(f"解析静态内容: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")
        self.logger.info(f"响应内容长度: {len(response.body)}")
        yield ExampleItem(
            url=response.url,
            title='Static Content',
            content_length=len(response.body)
        )

    def parse_dynamic(self, response):
        """解析动态内容"""
        self.logger.info(f"解析动态内容: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")
        self.logger.info(f"响应内容长度: {len(response.body)}")
        yield ExampleItem(
            url=response.url,
            title='Dynamic Content',
            content_length=len(response.body)
        )

    def parse_scroll(self, response):
        """解析滚动加载内容"""
        self.logger.info(f"解析滚动加载内容: {response.url}")
        self.logger.info(f"响应状态码: {response.status_code}")
        self.logger.info(f"响应内容长度: {len(response.body)}")
        yield ExampleItem(
            url=response.url,
            title='Scroll Content',
            content_length=len(response.body)
        )