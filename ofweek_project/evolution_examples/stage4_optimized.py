# -*- coding: UTF-8 -*-
"""
阶段4：分布式模式优化示例
- 配置 Redis 连接池
- 优化去重性能
- 增加监控和故障恢复机制
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
    print("=== 阶段4：分布式模式优化 ===")
    print("特点：")
    print("- 配置 Redis 连接池")
    print("- 优化去重性能")
    print("- 增加监控和故障恢复机制")
    print()
    
    # 创建基础的分布式配置
    config = CrawloConfig.distributed(
        redis_host='127.0.0.1',
        redis_port=6379,
        redis_password='',
        redis_db=2,
        project_name='ofweek_project',
        concurrency=16,           # 更高的并发数
        download_delay=0.5        # 更短的延迟
    )
    
    # 获取配置字典并添加优化配置
    config_dict = config.to_dict()
    
    # 添加 Redis 连接池配置
    config_dict.update({
        'REDIS_CONNECTION_POOL': {
            'min_connections': 5,
            'max_connections': 20,
            'retry_on_timeout': True,
            'health_check_interval': 30
        },
        # 可以添加更多优化配置
        'REQUEST_TIMEOUT': 30,
        'RETRY_TIMES': 3,
        'RETRY_DELAY': 2.0
    })
    
    # 打印详细配置信息
    print("优化配置详情：")
    print(f"- Redis 地址: {config_dict.get('REDIS_HOST', '127.0.0.1')}:{config_dict.get('REDIS_PORT', 6379)}")
    print(f"- 并发数: {config_dict.get('CONCURRENCY', 16)}")
    print(f"- 下载延迟: {config_dict.get('DOWNLOAD_DELAY', 0.5)} 秒")
    print(f"- 过滤器: {config_dict.get('FILTER_CLASS', 'AioRedisFilter')}")
    
    # 打印连接池配置
    pool_config = config_dict.get('REDIS_CONNECTION_POOL', {})
    print("- Redis 连接池配置:")
    print(f"  - 最小连接数: {pool_config.get('min_connections', 5)}")
    print(f"  - 最大连接数: {pool_config.get('max_connections', 20)}")
    print(f"  - 超时重试: {pool_config.get('retry_on_timeout', True)}")
    print(f"  - 健康检查间隔: {pool_config.get('health_check_interval', 30)} 秒")
    print()
    
    # 检查 Redis 连接和连接池
    print("检查 Redis 连接和连接池配置...")
    try:
        import aioredis
        redis_url = config_dict.get('REDIS_URL', 'redis://127.0.0.1:6379/2')
        # 使用连接池配置创建 Redis 连接
        pool_config = config_dict.get('REDIS_CONNECTION_POOL', {})
        redis = aioredis.from_url(
            redis_url,
            minsize=pool_config.get('min_connections', 5),
            maxsize=pool_config.get('max_connections', 20),
            retry_on_timeout=pool_config.get('retry_on_timeout', True)
        )
        await redis.ping()
        print("✓ Redis 连接和连接池配置成功")
        await redis.close()
    except Exception as e:
        print(f"✗ Redis 连接或连接池配置失败: {e}")
        print("请确保 Redis 服务正在运行")
        return
    
    print()
    
    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=config_dict)
    
    # 运行爬虫
    print("开始运行优化的分布式爬虫...")
    await process.crawl(OfweekSpider)
    
    print("优化的分布式爬虫运行完成")

if __name__ == '__main__':
    asyncio.run(main())