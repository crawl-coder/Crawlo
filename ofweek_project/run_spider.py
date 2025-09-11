# -*- coding: UTF-8 -*-
"""运行 OfweekSpider 的简单脚本"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.crawler import CrawlerProcess
from ofweek_project.spiders.OfweekSpider import OfweekSpider

async def main():
    # 创建爬虫进程
    process = CrawlerProcess()
    
    # 运行爬虫
    await process.crawl(OfweekSpider)

if __name__ == '__main__':
    asyncio.run(main())