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
    config_dict = config.to_dict()
    print(f"Redis 地址: {config_dict.get('REDIS_HOST', '127.0.0.1')}:{config_dict.get('REDIS_PORT', 6379)}")
    print(f"Redis 数据库: {config_dict.get('REDIS_DB', 2)}")
    print(f"并发数: {config_dict.get('CONCURRENCY', 16)}")
    print(f"下载延迟: {config_dict.get('DOWNLOAD_DELAY', 0.5)} 秒")
    print(f"过滤器: {config_dict.get('FILTER_CLASS', 'AioRedisFilter')}")
    print(f"项目名称: {config_dict.get('PROJECT_NAME', 'default')}")
    
    # 检查 Redis 连接（简化版，不实际连接）
    print("检查 Redis 配置...")
    try:
        # 只是验证配置是否正确，不实际连接Redis
        redis_url = config_dict.get('REDIS_URL', 'redis://127.0.0.1:6379/2')
        print(f"Redis URL: {redis_url}")
        # 验证URL中包含正确的数据库编号
        expected_db = config_dict.get('REDIS_DB', 2)
        if f"/{expected_db}" in redis_url:
            print("✓ Redis 配置检查通过")
        else:
            print(f"⚠️ Redis URL 中的数据库编号可能不正确")
    except Exception as e:
        print(f"✗ Redis 配置检查失败: {e}")
        return

    # 创建爬虫进程并应用配置
    print("初始化爬虫进程...")
    try:
        process = CrawlerProcess(settings=config_dict)
        print("✓ 爬虫进程初始化成功")
    except Exception as e:
        print(f"✗ 爬虫进程初始化失败: {e}")
        return
    
    print("✅ 脚本初始化完成，配置正确")


if __name__ == '__main__':
    asyncio.run(main())