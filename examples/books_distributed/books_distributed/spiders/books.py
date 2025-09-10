# -*- coding: utf-8 -*-
"""
Books Spider (Distributed version)
==============================

Features:
- Distributed mode operation
- Books data scraping from books.toscrape.com
- Redis distributed queue and deduplication

Run with:
    crawlo run books
"""

import uuid
from crawlo.spider import Spider
from crawlo import Request
from crawlo.utils.log import get_logger
from ..items import BookItem

logger = get_logger(__name__)


class BooksSpider(Spider):
    """Distributed Books Spider"""
    
    name = 'books'
    allowed_domains = ['books.toscrape.com']
    
    # Distributed spider configuration
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,           # Can reduce delay in distributed environment
        'CONCURRENCY': 16,               # Higher concurrency in distributed mode
        'MAX_RETRY_TIMES': 5,            # Increase retry count in distributed environment
        'FILTER_CLASS': 'crawlo.filters.aioredis_filter.AioRedisFilter',  # Redis deduplication
        'SCHEDULER': 'crawlo.core.scheduler.Scheduler',  # Redis scheduler
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_id = str(uuid.uuid4())[:8]  # Generate short unique ID
        logger.info(f"Instance unique ID: {self.instance_id}")
    
    def start_requests(self):
        """Generate initial requests"""
        logger.info("BooksSpider started")
        
        # Use more start URLs to get more data
        start_urls = []
        for i in range(1, 51):  # Pages 1-10
            start_urls.append(f'http://books.toscrape.com/catalogue/page-{i}.html')
        
        logger.info(f"Using {len(start_urls)} start URLs")
        for url in start_urls:
            logger.info(f"Adding start URL: {url}")
            yield Request(url)
    
    def parse(self, response):
        """Parse book listing pages and follow pagination links"""
        logger.info(f"Parsing page: {response.url}")
        
        item = BookItem()
        product_main = response.css('div.product_main')
        table = response.css('table.table.table-striped')

        item['title'] = product_main.css('h1::text').get()
        item['price'] = product_main.css('p.price_color::text').get()
        item['rating'] = product_main.css('p.star-rating::attr(class)').re_first(r'Star Rating (\w+)')
        availability_text = product_main.css('p.availability::text').re_first(r'\S+')
        item['availability'] = availability_text.strip() if availability_text else 'Unknown'

        item['upc'] = table.xpath('.//tr[th/text()="UPC"]/td/text()').get()
        item['tax'] = table.xpath('.//tr[th/text()="Tax"]/td/text()').get()
        stock_text = table.xpath('.//tr[th/text()="Availability"]/td/text()').re_first(r'\((\d+) available\)')
        item['stock'] = stock_text

        item['category'] = response.css('ul.breadcrumb li:nth-child(3) a::text').get()
        item['url'] = response.url

        logger.debug(f"📊 提取到的数据: {dict(item)}")

        yield item