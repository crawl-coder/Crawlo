#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
test_project 项目运行脚本
============================
基于 Crawlo 框架的简化爬虫启动器。
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换到项目根目录
os.chdir(project_root)

from crawlo.crawler import CrawlerProcess


def main():
    """主函数：运行固定的爬虫"""
    print("🚀 启动 test_project 爬虫")
    
    # 创建爬虫进程（自动加载默认配置）
    try:
        # 确保 spider 模块被正确导入
        spider_modules = ['test_project.spiders']
        process = CrawlerProcess(spider_modules=spider_modules)
        print("✅ 爬虫进程初始化成功")
        
        # 运行OfweekSpider爬虫
        asyncio.run(process.crawl('of_week'))
        
        print("✅ 爬虫运行完成")
        
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()