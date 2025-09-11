# -*- coding: UTF-8 -*-
"""使用 standalone 模式运行 OfweekSpider 的脚本"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess
from ofweek_project.spiders.OfweekSpider import OfweekSpider

async def main():
    # 使用 standalone 模式配置
    # 这种模式适用于单机运行，使用内存队列和去重过滤器
    config = CrawloConfig.standalone(
        concurrency=8,           # 并发请求数
        download_delay=1.0,      # 下载延迟（秒）
        project_name='ofweek_project'
    )
    
    # 打印配置信息
    print("使用 Standalone 模式运行 OfweekSpider")
    print(f"并发数: {config.to_dict().get('CONCURRENCY', 8)}")
    print(f"下载延迟: {config.to_dict().get('DOWNLOAD_DELAY', 1.0)} 秒")
    print(f"过滤器: {config.to_dict().get('FILTER_CLASS', 'MemoryFilter')}")
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config.to_dict())
    
    # 运行爬虫
    await process.crawl(OfweekSpider)

if __name__ == '__main__':
    asyncio.run(main())