# -*- coding: UTF-8 -*-
"""
阶段3：分布式模式示例
- 使用 Redis 队列和去重过滤器
- 支持多节点协同工作
- 需要 Redis 环境支持
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
    print("=== 阶段3：分布式模式 ===")
    print("特点：")
    print("- 使用 Redis 队列和去重过滤器")
    print("- 支持多节点协同工作")
    print("- 需要 Redis 环境支持")
    print()
    
    # 使用 distributed 模式配置
    config = CrawloConfig.distributed(
        redis_host='127.0.0.1',   # Redis 服务器地址
        redis_port=6379,          # Redis 端口
        redis_password='',        # Redis 密码（如果有的话）
        redis_db=2,               # Redis 数据库编号
        project_name='ofweek_project',
        concurrency=8,            # 分布式环境下适中的并发数
        download_delay=1.0        # 分布式环境下适中的延迟
    )
    
    # 打印配置信息
    config_dict = config.to_dict()
    print("配置详情：")
    print(f"- Redis 地址: {config_dict.get('REDIS_HOST', '127.0.0.1')}:{config_dict.get('REDIS_PORT', 6379)}")
    print(f"- Redis 数据库: {config_dict.get('REDIS_DB', 2)}")
    print(f"- 并发数: {config_dict.get('CONCURRENCY', 8)}")
    print(f"- 下载延迟: {config_dict.get('DOWNLOAD_DELAY', 1.0)} 秒")
    print(f"- 过滤器: {config_dict.get('FILTER_CLASS', 'AioRedisFilter')}")
    print(f"- 调度器: {config_dict.get('SCHEDULER', 'Scheduler')}")
    print()
    
    # 检查 Redis 连接
    print("检查 Redis 连接...")
    try:
        import aioredis
        redis_url = config_dict.get('REDIS_URL', 'redis://127.0.0.1:6379/2')
        redis = aioredis.from_url(redis_url)
        await redis.ping()
        print("✓ Redis 连接成功")
        await redis.close()
    except Exception as e:
        print(f"✗ Redis 连接失败: {e}")
        print("请确保 Redis 服务正在运行")
        return
    
    print()
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config_dict)
    
    # 运行爬虫
    print("开始运行分布式爬虫...")
    await process.crawl(OfweekSpider)
    
    print("分布式爬虫运行完成")

if __name__ == '__main__':
    asyncio.run(main())