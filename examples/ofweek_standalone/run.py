#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
ofweek_standalone 项目运行脚本
============================
基于 Crawlo 框架的简化爬虫启动器。

框架会自动处理爬虫模块的导入和注册，用户无需手动导入。
框架会自动从settings.py中读取SPIDER_MODULES配置。
"""
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


def main():
    """主函数：运行爬虫"""
    try:
        # CrawlerProcess会自动从settings.py中读取SPIDER_MODULES配置
        process = CrawlerProcess()

        # 运行指定的爬虫
        asyncio.run(process.crawl('of_week_standalone'))

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()


    """
    1、html 标签以<!DOCTYPE html开头，共31,320条，已软删。
    2、content 内容存在datalist 共6条，已软删。
    """