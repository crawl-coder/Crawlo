#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
ofweek_spider 项目运行脚本
============================
基于 Crawlo 框架的简化爬虫启动器。

框架会自动处理爬虫模块的导入和注册，用户无需手动导入。
框架会自动从settings.py中读取SPIDER_MODULES配置。
"""
import os
import sys
import asyncio

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler_process import CrawlerProcess


def main():
    """主函数：运行爬虫"""
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            from crawlo.scheduling import start_scheduler
            start_scheduler(project_root)
        else:
            # TODO: 请将 'spider_name' 替换为实际要运行的爬虫名称
            asyncio.run(CrawlerProcess().crawl('spider_name'))

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()