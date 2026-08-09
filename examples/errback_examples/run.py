#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
errback Examples 运行入口
=========================
演示 Crawlo 框架 errback 错误回调的各种使用模式。

运行方式:
    cd examples/errback_examples
    python run.py basic_errback      # 基础 errback 用法
    python run.py smart_retry        # 智能重试 + Failure.request
    python run.py async_start        # async start_requests 用法
    python run.py --schedule         # 定时任务模式
"""
import os
import sys
import asyncio

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler import CrawlerProcess


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
        from crawlo.commands.scheduler import start_scheduler
        start_scheduler(project_root)
        return

    if len(sys.argv) < 2:
        print("用法: python run.py <spider_name>")
        print("可选: basic_errback | smart_retry | async_start")
        print("      python run.py --schedule  # 定时任务模式")
        sys.exit(1)

    spider_name = sys.argv[1]
    try:
        asyncio.run(CrawlerProcess().crawl(spider_name))
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
