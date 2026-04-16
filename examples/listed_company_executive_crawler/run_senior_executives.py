#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
运行高级管理人员信息爬虫
"""

import os
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """运行高级管理人员信息爬虫"""
    try:
        print("=" * 60)
        print("上市公司高级管理人员信息爬虫")
        print("=" * 60)
        
        # 运行爬虫
        asyncio.run(CrawlerProcess().crawl('senior_executives'))
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
