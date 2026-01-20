#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行listed_executive_changes爬虫
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.crawler import CrawlerProcess


async def run_spider():
    """运行高管变动信息爬虫"""
    print("开始运行listed_executive_changes爬虫...")
    print("=" * 50)
    
    process = CrawlerProcess()
    
    try:
        await process.crawl('listed_executive_changes')
        print("爬虫运行完成！")
    except Exception as e:
        print(f"爬虫运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Windows兼容性已在框架内部处理，无需在此处设置
    asyncio.run(run_spider())