#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Spider Loader 示例运行脚本
演示如何使用SPIDER_MODULES配置来自动发现和加载爬虫
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 确保当前目录也在路径中
sys.path.insert(0, os.getcwd())

# 导入必要的模块
from crawlo import CrawlerProcess
from crawlo.settings.setting_manager import SettingManager


def load_settings():
    """加载settings.py配置"""
    # 尝试导入settings模块
    try:
        import settings
        # 创建SettingManager实例
        setting_manager = SettingManager()
        # 获取settings模块中的所有大写属性
        for attr in dir(settings):
            if attr.isupper():
                setting_manager.set(attr, getattr(settings, attr))
        return setting_manager
    except ImportError:
        print("警告: 无法导入settings.py，使用默认配置")
        return None


async def main():
    """主函数"""
    # 加载设置
    settings = load_settings()
    
    # 创建CrawlerProcess实例，它会自动从settings.py中读取SPIDER_MODULES配置
    process = CrawlerProcess(settings=settings)
    
    # 获取所有可用的爬虫名称
    spider_names = process.get_spider_names()
    print(f"发现的爬虫: {spider_names}")
    
    # 运行指定的爬虫
    if spider_names:
        spider_name = spider_names[0]  # 运行第一个爬虫
        print(f"运行爬虫: {spider_name}")
        await process.crawl(spider_name)
    else:
        print("未发现任何爬虫")


if __name__ == '__main__':
    asyncio.run(main())