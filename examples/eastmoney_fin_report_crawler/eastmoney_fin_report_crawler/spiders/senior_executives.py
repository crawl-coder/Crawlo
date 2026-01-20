# -*- coding: UTF-8 -*-
"""
financial_reports_spider.spiders.senior_e0xecutives
=======================================
由 `crawlo genspider` 命令生成的爬虫。
基于 Crawlo 框架，支持异步并发、分布式爬取等功能。

使用示例：
    crawlo crawl senior_e0xecutives
"""

from crawlo.spider import Spider
from crawlo import Request

from utils.tools import get_v_params, generate_pmid, parse_tenure_dates
from ..items import SeniorExecutivesItem
from ..settings import HEADERS, STOCKS


class SeniorExecutivesSpider(Spider):
    """
    爬虫：senior_e0xecutives
    
    功能说明：
    - 支持并发爬取
    - 自动去重过滤
    - 错误重试机制
    - 数据管道处理
    """
    name = 'senior_executives'
    allowed_domains = ['datacenter.eastmoney.com', 'datapc.eastmoney.com']
    # start_urls = ['300080.SZ']
    
    # 高级配置（可选）
    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENCY': 8,
        'MYSQL_TABLE': 'listed_senior_executives'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_stocks = set()

    def start_requests(self):
        """
        生成初始请求。
        
        支持自定义请求头、代理、优先级等。
        """
        url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
        for stock_code in STOCKS:
            params = {
                "reportName": "RPT_F10_ORGINFO_MANAINTRO",
                "columns": "ALL",
                "quoteColumns": "",
                "filter": f"(SECUCODE=\"{stock_code}\")",
                "pageNumber": "1",
                "pageSize": "",
                "sortTypes": "",
                "sortColumns": "",
                "source": "HSF10",
                "client": "PC",
                "v": "04693675080409824"
            }
            v_value = get_v_params(params)
            params['v'] = v_value
            yield Request(
                url=url,
                callback=self.parse,
                headers=HEADERS,
                params=params,
                meta={'stock_code': stock_code}
            )

    def parse(self, response):
        """
        解析响应的主方法。
        
        Args:
            response: 响应对象，包含页面内容和元数据
            
        Yields:
            Request: 新的请求对象（用于深度爬取）
            Item: 数据项对象（用于数据存储）
        """
        try:
            json_data = response.json()
            msg = json_data.get('message')
            stock_code = response.meta.get('stock_code')

            # 关键修改：如果消息不是'ok'，直接返回None，不产生任何item
            if msg != 'ok':
                self.logger.error(f"API返回错误消息: {msg}, URL: {response.url}")
                self.failed_stocks.add(stock_code)
                return None  # 直接返回None，不产生任何数据

            rows = json_data.get('result', {}).get('data', [])
            for row in rows:
                person_name = row.get('PERSON_NAME')
                incumbent_time = row.get('INCUMBENT_TIME')
                date_info = parse_tenure_dates(incumbent_time)
                item = SeniorExecutivesItem()
                item['stock_code'] = stock_code
                item['stock_name'] = row.get('SECURITY_NAME_ABBR')
                item['name'] = row.get('PERSON_NAME')
                item['gender'] = row.get('SEX')
                item['age'] = row.get('AGE')
                item['education'] = row.get('HIGH_DEGREE')
                item['shareholding_num'] = row.get('HOLD_NUM')
                item['salary'] = row.get('SALARY')
                item['position'] = row.get('POSITION')
                item['tenure_start_date'] = date_info.get('tenure_start_date')
                item['tenure_end_date'] = date_info.get('tenure_end_date')
                # item['incumbent_time'] = row.get('INCUMBENT_TIME')
                item['introduction'] = row.get('RESUME')
                item['pmid'] = generate_pmid(stock_code=stock_code, report_date=person_name)

                yield item

        except Exception as e:
            pass



