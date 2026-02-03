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
            asyncio.run(CrawlerProcess().crawl('a_market_value'))

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
    """
    1、我要彻底重构日志系统；2、我要取消日志轮转工功能；3、我希望把spider_name 加入到文件名里，用户可以在 ​a_market_value.py 21-23​ 里自定义日志文件名，默认是 ​settings.py 56-56​ 3、要解决上述2种场景（多个爬虫同时运行、单个或者多个爬虫在定时模式下，轮次之间）下遇到的问题。
    """