# -*- coding: UTF-8 -*-
"""动态模式切换运行脚本"""

import sys
import os
import asyncio
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.config import CrawloConfig
from crawlo.crawler import CrawlerProcess
from ofweek_project.spiders.OfweekSpider import OfweekSpider

def get_config(mode, **kwargs):
    """根据模式获取配置"""
    if mode == 'distributed':
        return CrawloConfig.distributed(
            redis_host=kwargs.get('redis_host', '127.0.0.1'),
            redis_port=kwargs.get('redis_port', 6379),
            redis_password=kwargs.get('redis_password', ''),
            redis_db=kwargs.get('redis_db', 2),
            project_name=kwargs.get('project_name', 'ofweek_project'),
            concurrency=kwargs.get('concurrency', 16),
            download_delay=kwargs.get('download_delay', 0.5)
        )
    else:  # standalone
        return CrawloConfig.standalone(
            project_name=kwargs.get('project_name', 'ofweek_project'),
            concurrency=kwargs.get('concurrency', 8),
            download_delay=kwargs.get('download_delay', 1.0)
        )

async def main():
    parser = argparse.ArgumentParser(description='运行 OfweekSpider')
    parser.add_argument('--mode', choices=['standalone', 'distributed'], 
                       default='standalone', help='运行模式')
    parser.add_argument('--redis-host', default='127.0.0.1', help='Redis 主机地址')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis 端口')
    parser.add_argument('--redis-password', default='', help='Redis 密码')
    parser.add_argument('--redis-db', type=int, default=2, help='Redis 数据库编号')
    parser.add_argument('--concurrency', type=int, help='并发数')
    parser.add_argument('--delay', type=float, help='下载延迟')
    
    args = parser.parse_args()
    
    # 构建配置参数
    config_kwargs = {
        'project_name': 'ofweek_project',
        'redis_host': args.redis_host,
        'redis_port': args.redis_port,
        'redis_password': args.redis_password,
        'redis_db': args.redis_db
    }
    
    # 根据参数设置并发数和延迟
    if args.concurrency:
        config_kwargs['concurrency'] = args.concurrency
    if args.delay is not None:
        config_kwargs['download_delay'] = args.delay
    
    # 获取配置
    config = get_config(args.mode, **config_kwargs)
    
    # 打印配置信息
    print(f"使用 {args.mode.capitalize()} 模式运行 OfweekSpider")
    print(f"并发数: {config.to_dict().get('CONCURRENCY')}")
    print(f"下载延迟: {config.to_dict().get('DOWNLOAD_DELAY')} 秒")
    if args.mode == 'distributed':
        print(f"Redis 地址: {config.to_dict().get('REDIS_HOST')}:{config.to_dict().get('REDIS_PORT')}")
        print(f"过滤器: {config.to_dict().get('FILTER_CLASS')}")
    else:
        print(f"过滤器: {config.to_dict().get('FILTER_CLASS')}")
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config.to_dict())
    
    # 运行爬虫
    await process.crawl(OfweekSpider)

if __name__ == '__main__':
    asyncio.run(main())