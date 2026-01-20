#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    try:
        asyncio.run(CrawlerProcess().crawl('senior_executives'))
        # asyncio.run(CrawlerProcess().crawl_multiple(
        #         [
        #         'bs',                       # 资产负债表爬虫
        #         'core_financial_indicators',  # 核心财务指标爬虫
        #         'income_statement',           # 利润表爬虫
        #         'cash_flow_statement',        # 现金流量表爬虫
        #         'senior_executives',          # 高管信息爬虫
        #         'listed_executive_changes'    # 高管变动信息爬虫
        #         ]
        #     )
        # )

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()