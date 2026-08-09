#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            from crawlo.commands.scheduler import start_scheduler
            start_scheduler(project_root)
        else:
            # asyncio.run(CrawlerProcess().crawl('listed_executive_changes'))
            asyncio.run(CrawlerProcess().crawl(
                [
                    'bs',  # 资产负债表爬虫
                    'core_financial_indicators',  # 核心财务指标爬虫
                    'income_statement',  # 利润表爬虫
                    'cash_flow_statement',  # 现金流量表爬虫
                    'senior_executives',  # 高管信息爬虫
                    'listed_executive_changes'  # 高管变动信息爬虫
                ]
            ))


    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()