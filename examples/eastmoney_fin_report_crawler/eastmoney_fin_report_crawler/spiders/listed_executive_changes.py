# -*- coding: UTF-8 -*-
"""
financial_reports_spider.spiders.listed_executive_changes
=======================================
由 `crawlo genspider` 命令生成的爬虫。
基于 Crawlo 框架，支持异步并发、分布式爬取等功能。

使用示例：
    crawlo crawl listed_executive_changes
"""
import hashlib

from crawlo.spider import Spider
from crawlo import Request

from utils.tools import round_if_numeric
from ..items import ListedExecutiveChangesItem
from ..settings import HEADERS, STOCKS, REPORT_DATE_FILTER


class ListedExecutiveChangesSpider(Spider):
    """
    爬虫：listed_executive_changes
    
    功能说明：
    - 支持并发爬取
    - 自动去重过滤
    - 错误重试机制
    - 数据管道处理
    """
    name = 'listed_executive_changes'
    allowed_domains = ['datacenter.eastmoney.com', 'datapc.eastmoney.com']
    # start_urls = ['300080']
    
    # 高级配置（可选）
    custom_settings = {
        'DOWNLOAD_DELAY': 3.0,
        'CONCURRENCY': 4,
        'MYSQL_TABLE': 'listed_executive_changes'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_stocks = set()

    def start_requests(self):
        url = "https://datapc.eastmoney.com/emdatacenter/ggcg/detaillist"  # 去掉多余空格
        for stock_with_suffix in STOCKS:
            stock_with_suffix = stock_with_suffix.strip()
            if not stock_with_suffix:
                continue

            # 分离出纯数字代码用于请求
            code_for_api = stock_with_suffix.split('.')[0]

            params = {
                "st": "CHANGE_DATE,SECURITY_CODE,PERSON_NAME",
                "sr": "-1,1,1",
                "code": code_for_api,
                "name": "",
                "p": "1",
                "ps": "20"
            }

            yield Request(
                url=url,
                callback=self.parse,
                headers=HEADERS,
                params=params,
                meta={
                    'stock_with_suffix': stock_with_suffix,  # 保存原始带后缀代码，用于 item
                    'code_for_api': code_for_api,  # 可选，用于日志或翻页
                    'current_page': 1,
                    'base_params': {
                        "st": "CHANGE_DATE,SECURITY_CODE,PERSON_NAME",
                        "sr": "-1,1,1",
                        "code": code_for_api,
                        "name": "",
                        "ps": "20"
                    }
                }
            )

    def parse(self, response):
        """
        解析响应并实现翻页。
        """
        try:
            json_data = response.json()
            msg = json_data.get('message')
            stock_with_suffix = response.meta.get('stock_with_suffix')
            current_page = response.meta.get('current_page', 1)
            base_params = response.meta.get('base_params', {})

            if msg != 'ok':
                self.logger.error(f"API返回错误消息: {msg}, URL: {response.url}, Page: {current_page}")
                self.failed_stocks.add(stock_with_suffix)
                return

            result = json_data.get('result', {})
            rows = result.get('data', [])
            total_pages = result.get('pages', 0)  # 注意：有些接口可能在顶层，但你示例中是 result.pages

            # 解析当前页数据
            for row in rows:
                item = ListedExecutiveChangesItem()
                person_name = row.get('PERSON_NAME')
                change_date = row.get('CHANGE_DATE')
                dse_person_name = row.get('DSE_PERSON_NAME')
                change_shares = row.get('CHANGE_SHARES')
                shares_after_change = row.get('CHANGE_AFTER_HOLDNUM')
                item['pmid'] = hashlib.md5(f"{person_name}|{change_date}|{dse_person_name}|{change_shares}|{shares_after_change}".encode()).hexdigest()
                item['stock_code'] = stock_with_suffix
                item['stock_name'] = row.get('SECURITY_NAME')
                item['change_date'] = row.get('CHANGE_DATE')
                item['changer'] = person_name
                item['change_reason'] = row.get('CHANGE_REASON')
                item['change_shares'] = row.get('CHANGE_SHARES')
                item['average_trading_price'] = round_if_numeric(row.get('AVERAGE_PRICE'))
                item['change_amount'] = round_if_numeric(row.get('CHANGE_AMOUNT'))
                item['change_ratio'] = row.get('CHANGE_RATIO')
                item['shares_after_change'] = shares_after_change
                item['share_type'] = row.get('HOLD_TYPE')
                item['supervisor_name'] = dse_person_name
                item['position'] = row.get('POSITION_NAME')
                item['relationship_with_supervisor'] = row.get('PERSON_DSE_RELATION')

                yield item

            # 翻页逻辑：如果还有下一页，继续请求
            if current_page < total_pages:
                next_page = current_page + 1
                self.logger.info(f'{stock_with_suffix} next_page: {next_page}')
                next_params = base_params.copy()
                next_params['p'] = str(next_page)

                yield Request(
                    url=response.url.split('?')[0],  # 去掉原始参数，避免重复
                    callback=self.parse,
                    headers=HEADERS,
                    params=next_params,
                    meta={
                        'stock_with_suffix': stock_with_suffix,
                        'current_page': next_page,
                        'base_params': base_params
                    }
                )

        except Exception as e:
            self.logger.exception(f"解析出错: {e}, URL: {response.url}")



