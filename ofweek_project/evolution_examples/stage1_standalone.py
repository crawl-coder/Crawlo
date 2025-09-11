# -*- coding: UTF-8 -*-
"""
阶段1：基础单机模式示例
- 使用内存队列和内存去重过滤器
- 适合开发测试和小规模数据采集
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess
from ofweek_project.spiders.OfweekSpider import OfweekSpider

async def main():
    print("=== 阶段1：基础单机模式 ===")
    print("特点：")
    print("- 使用内存队列和内存去重过滤器")
    print("- 适合开发测试和小规模数据采集")
    print("- 配置简单，无需额外依赖")
    print()
    
    # 使用 standalone 模式配置（最简单的配置方式）
    config = CrawloConfig.standalone(
        concurrency=4,           # 较低的并发数，避免对目标网站造成压力
        download_delay=2.0,      # 较长的下载延迟，适合测试
        project_name='ofweek_project'
    )
    
    # 打印配置信息
    config_dict = config.to_dict()
    print("配置详情：")
    print(f"- 并发数: {config_dict.get('CONCURRENCY', 4)}")
    print(f"- 下载延迟: {config_dict.get('DOWNLOAD_DELAY', 2.0)} 秒")
    print(f"- 过滤器: {config_dict.get('FILTER_CLASS', 'MemoryFilter')}")
    print(f"- 调度器: {config_dict.get('SCHEDULER', 'Scheduler')}")
    print()
    
    # 为了演示，我们限制爬取的页面数量
    # 在实际应用中，可以移除这个限制
    print("注意：为了演示目的，这里会限制爬取的页面数量")
    print()
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config_dict)
    
    # 运行爬虫
    print("开始运行爬虫...")
    await process.crawl(OfweekSpider)
    
    print("爬虫运行完成")

if __name__ == '__main__':
    asyncio.run(main())