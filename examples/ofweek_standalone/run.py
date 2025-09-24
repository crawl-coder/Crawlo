#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
单机模式运行脚本
适用于开发测试和小规模数据采集
使用手动初始化确保稳定性
"""
import asyncio
import sys

async def main():
    """主函数：框架完全自动初始化版本"""
    try:
        print("🚀 正在启动 ofweek_standalone 爬虫...")
        
        # 框架完全自动初始化，用户无需任何手动操作
        from crawlo.crawler import CrawlerProcess
        
        print("✅ 正在创建 CrawlerProcess...")
        process = CrawlerProcess()
        print("爬虫进程初始化成功")
        
        print("✅ 正在运行爬虫...")
        
        # 直接使用爬虫类
        from ofweek_standalone.spiders.OfweekSpider import OfweekSpider
        
        # 运行爬虫
        await process.crawl(OfweekSpider)
        
        print("✅ 爬虫运行完成")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())