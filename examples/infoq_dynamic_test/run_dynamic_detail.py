#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
InfoQ 动态详情页测试运行脚本
==============================
测试场景：列表页使用协议下载器，详情页使用动态下载器
"""
import os
import sys
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入 Spider 模块（必须，否则 Spider 不会被注册）
from infoq_dynamic_test.spiders.infoq_dynamic_detail_spider import InfoqDynamicDetailSpider

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    print("=" * 60)
    print("InfoQ 动态详情页测试")
    print("测试场景: 列表页(协议) + 详情页(动态)")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(CrawlerProcess().crawl('infoq_dynamic_detail_spider'))
    except Exception as e:
        print(f"运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
