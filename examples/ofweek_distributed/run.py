#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from crawlo.crawler import CrawlerProcess


def main():
    """运行分布式爬虫"""
    try:
        # 分布式模式：启动多个 worker（在不同终端运行同一脚本）
        # crawlo.cfg 指定 settings 模块 → settings.py 中 CrawloConfig.distributed() 完成配置
        # 多个 worker 共享同一 Redis 队列协同爬取
        asyncio.run(CrawlerProcess().crawl('of_week_distributed'))
    except Exception as e:
        print(f"Run failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
