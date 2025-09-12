#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
分布式模式运行脚本
适用于大规模数据采集，需要 Redis 环境支持
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
from crawlo.settings.setting_manager import SettingManager
from ofweek_distributed.settings import *

def main():
    """主函数：使用分布式模式配置运行爬虫"""
    print("🌐 启动 OfweekSpider (分布式模式)")
    print(f"  - 项目名称: {PROJECT_NAME}")
    print(f"  - 并发数: {CONCURRENCY}")
    print(f"  - 下载延迟: {DOWNLOAD_DELAY}秒")
    print(f"  - 过滤器: {FILTER_CLASS}")
    print(f"  - 队列类型: {QUEUE_TYPE}")
    print(f"  - Redis URL: {REDIS_URL}")
    print(f"  - 队列名称: {SCHEDULER_QUEUE_NAME}")
    print("-" * 50)
    
    # 检查 Redis 连接
    try:
        import redis
        r = redis.Redis.from_url(REDIS_URL)
        r.ping()
        print("✅ Redis 连接成功")
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        print("💡 请确保 Redis 服务已启动并可访问")
        sys.exit(1)
    
    # 创建爬虫进程并应用配置
    try:
        # 创建 SettingManager 实例并应用配置
        settings = SettingManager()
        # 将分布式配置导入到 SettingManager 中
        settings.update_attributes(locals())
        
        # 确保 spider 模块被正确导入
        spider_modules = ['ofweek_distributed.spiders']
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)
        print("✅ 爬虫进程初始化成功")
        
        # 运行指定的爬虫
        asyncio.run(process.crawl('of_week'))
        print("✅ 爬虫运行完成")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()