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
from crawlo.settings.setting_manager import SettingManager
from ofweek_project.spiders.OfweekSpider import OfweekSpider


async def main():
    # 使用 distributed 模式配置
    # 这种模式适用于分布式运行，使用 Redis 队列和去重过滤器
    config = CrawloConfig.distributed(
        redis_host='127.0.0.1',  # Redis 服务器地址
        redis_port=6379,  # Redis 端口
        redis_password='',  # Redis 密码（如果有的话）
        redis_db=2,  # Redis 数据库编号
        project_name='ofweek_project',
        concurrency=16,  # 分布式环境下可以设置更高的并发数
        download_delay=0.5  # 分布式环境下可以设置更短的延迟
    )

    # 打印配置信息
    print("使用 Distributed 模式运行 OfweekSpider")
    config_dict = config.to_dict()
    print(f"Redis 地址: {config_dict.get('REDIS_HOST', '127.0.0.1')}:{config_dict.get('REDIS_PORT', 6379)}")
    print(f"并发数: {config_dict.get('CONCURRENCY', 16)}")
    print(f"下载延迟: {config_dict.get('DOWNLOAD_DELAY', 0.5)} 秒")
    print(f"过滤器: {config_dict.get('FILTER_CLASS', 'AioRedisFilter')}")
    print(f"项目名称: {config_dict.get('PROJECT_NAME', 'default')}")

    # 创建 SettingManager 实例并应用配置
    settings = SettingManager()
    settings.update_attributes(config_dict)
    
    # 验证项目名称是否正确设置
    print(f"SettingManager 中的项目名称: {settings.get('PROJECT_NAME', 'default')}")

    # 创建爬虫进程并应用配置
    process = CrawlerProcess(settings=settings)

    # 运行爬虫
    await process.crawl(OfweekSpider)


if __name__ == '__main__':
    asyncio.run(main())

    """
crawlo:ofweek_project:filter:fingerprint (请求去重)
crawlo:ofweek_project:item:fingerprint (数据项去重)
crawlo:ofweek_project:queue:requests (请求队列)
crawlo:ofweek_project:queue:processing (处理中队列)
crawlo:ofweek_project:queue:failed (失败队列)
    """