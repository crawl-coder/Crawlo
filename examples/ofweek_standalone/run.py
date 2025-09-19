#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
单机模式运行脚本
适用于开发测试和小规模数据采集
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


async def main():
    """主函数：使用单机模式配置运行爬虫"""
    # print("🚀 开始启动 OfweekSpider (单机模式)")
    
    # 获取配置
    # settings = get_settings()
    # print("配置信息:")
    # print(f"  - 项目名称: {settings.get('PROJECT_NAME', 'Unknown')}")
    # print(f"  - 运行模式: {settings.get('RUN_MODE', 'Unknown')}")
    # print(f"  - 并发数: {settings.get('CONCURRENCY', 1)}")
    # print(f"  - 下载延迟: {settings.get('DOWNLOAD_DELAY', 0)}秒")
    # print(f"  - 过滤器: {settings.get('FILTER_CLASS', 'Unknown')}")
    # print(f"  - 队列类型: {settings.get('QUEUE_TYPE', 'Unknown')}")
    # print(f"  - 默认去重管道: {settings.get('DEFAULT_DEDUP_PIPELINE', 'Unknown')}")
    # print(f"  - Redis URL: {settings.get('REDIS_URL', 'Unknown')}")
    # print("-" * 50)

    # 创建爬虫进程并应用配置
    try:
        # 确保 spider 模块被正确导入
        spider_modules = ['ofweek_standalone.spiders']
        process = CrawlerProcess(spider_modules=spider_modules)

        await process.crawl('of_week_standalone')

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # 设置超时时间
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()