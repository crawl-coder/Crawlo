#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-31 22:36
# @Author  :   crawl-coder
# @Desc    :   命令行入口：crawlo stats，查看最近运行的爬虫统计信息。
"""
import sys
from crawlo.utils.log import get_logger


logger = get_logger(__name__)

# 保存最近运行的爬虫的统计（示例）
_LAST_RUN_STATS = {}


def record_stats(crawler):
    """在爬虫关闭后记录统计（需在 close 中调用）"""
    if crawler.stats and crawler.spider:
        _LAST_RUN_STATS[crawler.spider.name] = crawler.stats.get_stats()


def main(args):
    if len(args) == 0:
        # 显示所有历史统计
        if not _LAST_RUN_STATS:
            print("📊 No stats available. Run a spider first.")
            return 0

        print("📊 Recent Spider Statistics:")
        print("-" * 60)
        for spider_name, stats in _LAST_RUN_STATS.items():
            print(f"🕷️  {spider_name}")
            for k, v in stats.items():
                print(f"    {k:<30} {v}")
            print()
        return 0

    elif len(args) == 1:
        spider_name = args[0]
        if spider_name not in _LAST_RUN_STATS:
            print(f"📊 No stats found for spider '{spider_name}'")
            return 1

        stats = _LAST_RUN_STATS[spider_name]
        print(f"📊 Stats for '{spider_name}':")
        print("-" * 60)
        for k, v in stats.items():
            print(f"    {k:<30} {v}")
        return 0

    else:
        print("Usage: crawlo stats [spider_name]")
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))