#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
单机模式运行脚本
使用新的框架架构，完全自动化初始化
"""
import asyncio
import sys

from crawlo.crawler import CrawlerProcess


def main():
    """主函数：运行爬虫"""
    # print("🚀 启动 Ofweek 爬虫")

    try:
        # 使用框架自动处理配置
        spider_modules = ['ofweek_standalone.spiders']
        process = CrawlerProcess(spider_modules=spider_modules)

        # 运行指定的爬虫
        asyncio.run(process.crawl('of_week_standalone'))

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()