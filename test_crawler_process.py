#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换到项目根目录
os.chdir(project_root)

from crawlo.crawler import CrawlerProcess
from crawlo.project import get_settings

def main():
    """测试 CrawlerProcess 是否存在问题"""
    try:
        print("测试 CrawlerProcess 初始化...")
        
        # 获取配置
        settings = get_settings()
        print(f"项目名称: {settings.get('PROJECT_NAME', 'Unknown')}")
        print(f"运行模式: {settings.get('RUN_MODE', 'Unknown')}")
        
        # 创建爬虫进程
        spider_modules = ['ofweek_distributed.spiders']  # 修正模块路径
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)
        print("✅ CrawlerProcess 初始化成功")
        print(f"已注册的爬虫: {process.get_spider_names()}")
        
        # 测试获取爬虫类
        if process.get_spider_names():
            spider_name = process.get_spider_names()[0]
            spider_cls = process.get_spider_class(spider_name)
            print(f"爬虫类: {spider_cls}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()