#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    try:
        # 检查是否启动定时任务模式
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            # 启动定时任务模式
            from crawlo.scheduling import start_scheduler
            # 获取当前脚本所在目录作为项目根目录
            project_root = os.path.dirname(os.path.abspath(__file__))
            start_scheduler(project_root)
        else:
            # 正常爬虫运行模式
            asyncio.run(CrawlerProcess().crawl('of_week_with_notifications'))
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
    """
    python -m build
    twine upload dist/*
    pip install -i https://pypi.org/simple/ crawlo
    """
