#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
单机模式运行脚本
适用于开发测试和小规模数据采集
"""

import asyncio
import sys

from crawlo.crawler import CrawlerProcess


def main():
    """主函数：使用单机模式配置运行爬虫"""
    # 创建爬虫进程（自动加载默认配置）
    try:
        # 确保 spider 模块被正确导入
        spider_modules = ['ofweek_standalone.spiders']
        process = CrawlerProcess(spider_modules=spider_modules)
        
        # 添加调试信息
        print("MIDDLEWARES配置详情:")
        print("默认MIDDLEWARES:", process.settings.attributes.get('MIDDLEWARES', []))
        print("实际启用的MIDDLEWARES:", process.settings.get_list('MIDDLEWARES'))
        print()
        
        # 运行固定的爬虫
        asyncio.run(process.crawl('of_week_standalone'))
        
        print("✅ 爬虫运行完成")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()