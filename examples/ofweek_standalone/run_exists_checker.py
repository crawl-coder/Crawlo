#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""运行 MySQLExistsChecker 测试爬虫"""

import asyncio
from crawlo.crawler import CrawlerProcess


async def main():
    """运行 exists_checker 爬虫"""
    print("=" * 60)
    print("启动 of_week_with_exists_checker 爬虫")
    print("=" * 60)
    
    process = CrawlerProcess()
    await process.crawl('of_week_with_exists_checker')


if __name__ == '__main__':
    asyncio.run(main())
