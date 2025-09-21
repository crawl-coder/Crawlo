#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
混合模式运行脚本
支持单机和分布式模式切换
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换到项目根目录
os.chdir(project_root)

from crawlo.crawler import CrawlerProcess
from crawlo.project import get_settings


def main():
    """主函数：根据环境变量运行爬虫"""
    # 获取配置
    settings = get_settings()

    run_mode = settings.get('RUN_MODE', 'standalone')

    print(f"启动 OfweekSpider ({run_mode}模式)")
    print(f"  - 项目名称: {settings.get('PROJECT_NAME', 'Unknown')}")
    print(f"  - 并发数: {settings.get('CONCURRENCY', 1)}")
    print(f"  - 下载延迟: {settings.get('DOWNLOAD_DELAY', 0)}秒")
    print(f"  - 过滤器: {settings.get('FILTER_CLASS', 'Unknown')}")
    print(f"  - 队列类型: {settings.get('QUEUE_TYPE', 'Unknown')}")

    if run_mode == 'distributed':
        print(f"  - Redis URL: {settings.get('REDIS_URL', 'Unknown')}")
        print(f"  - 队列名称: {settings.get('SCHEDULER_QUEUE_NAME', 'Unknown')}")

        # 检查 Redis 连接
        try:
            import redis
            redis_url = settings.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
            r = redis.Redis.from_url(redis_url)
            r.ping()
            print("Redis 连接成功")
        except Exception as e:
            print(f"Redis 连接失败: {e}")
            print("请确保 Redis 服务已启动并可访问")
            sys.exit(1)

    print("-" * 50)

    # 创建爬虫进程并应用配置
    try:
        # 确保 spider 模块被正确导入
        spider_modules = ['ofweek_spider.spiders']
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)
        print("爬虫进程初始化成功")

        # 运行指定的爬虫
        asyncio.run(process.crawl('of_week'))
        print("爬虫运行完成")

    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
