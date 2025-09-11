# -*- coding: UTF-8 -*-
"""使用 distributed 模式运行 OfweekSpider 的脚本"""

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
    # 使用 distributed 模式配置
    # 这种模式适用于分布式运行，使用 Redis 队列和去重过滤器
    config = CrawloConfig.distributed(
        redis_host='127.0.0.1',   # Redis 服务器地址
        redis_port=6379,          # Redis 端口
        redis_password='',        # Redis 密码（如果有的话）
        redis_db=2,               # Redis 数据库编号
        project_name='ofweek_project',
        concurrency=16,           # 分布式环境下可以设置更高的并发数
        download_delay=0.5        # 分布式环境下可以设置更短的延迟
    )
    
    # 打印配置信息
    print("使用 Distributed 模式运行 OfweekSpider")
    print(f"Redis 地址: {config.to_dict().get('REDIS_HOST', '127.0.0.1')}:{config.to_dict().get('REDIS_PORT', 6379)}")
    print(f"并发数: {config.to_dict().get('CONCURRENCY', 16)}")
    print(f"下载延迟: {config.to_dict().get('DOWNLOAD_DELAY', 0.5)} 秒")
    print(f"过滤器: {config.to_dict().get('FILTER_CLASS', 'AioRedisFilter')}")
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config.to_dict())
    
    # 运行爬虫
    await process.crawl(OfweekSpider)

if __name__ == '__main__':
    asyncio.run(main())