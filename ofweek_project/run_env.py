# -*- coding: UTF-8 -*-
"""通过环境变量切换模式的运行脚本"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# 设置配置模块
os.environ['CRAWLO_SETTINGS_MODULE'] = 'ofweek_project.settings_dynamic'

from crawlo.crawler import CrawlerProcess
from ofweek_project.spiders.OfweekSpider import OfweekSpider

async def main():
    # 从环境变量读取配置
    run_mode = os.getenv('CRAWLO_RUN_MODE', 'standalone')
    
    print(f"使用 {run_mode.capitalize()} 模式运行 OfweekSpider")
    print(f"并发数: {os.getenv('CRAWLO_CONCURRENCY', '8 (standalone) / 16 (distributed)')}")
    print(f"下载延迟: {os.getenv('CRAWLO_DOWNLOAD_DELAY', '1.0 (standalone) / 0.5 (distributed)')} 秒")
    
    # 创建爬虫进程（会自动从环境变量读取配置）
    process = CrawlerProcess()
    
    # 运行爬虫
    await process.crawl(OfweekSpider)

if __name__ == '__main__':
    asyncio.run(main())