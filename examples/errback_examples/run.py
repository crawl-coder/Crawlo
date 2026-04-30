#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
errback Examples 运行入口
=========================
演示 Crawlo 框架 errback 错误回调的各种使用模式。

运行方式:
    cd examples/errback_examples
    python run.py basic_errback     # 基础 errback 用法
    python run.py smart_retry         # 智能重试 + Failure.request
"""
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    if len(sys.argv) < 2:
        print("用法: python run.py <spider_name>")
        print("可选: basic_errback | smart_retry")
        sys.exit(1)

    spider_name = sys.argv[1]
    try:
        asyncio.run(CrawlerProcess().crawl(spider_name))
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
