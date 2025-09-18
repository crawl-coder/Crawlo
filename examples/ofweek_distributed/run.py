#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
分布式模式运行脚本
适用于大规模数据采集，需要 Redis 环境支持
"""

import sys
import os
import asyncio

from crawlo.project import get_settings

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换到项目根目录
os.chdir(project_root)

from crawlo.crawler import CrawlerProcess


def main():
    """主函数：使用分布式模式配置运行爬虫"""

    # 创建爬虫进程并应用配置
    try:
        # 创建 SettingManager 实例并应用配置
        settings = get_settings()
        # 将分布式配置导入到 SettingManager 中
        # settings.update_attributes(locals())
        print(settings)

        # 确保 spider 模块被正确导入
        spider_modules = ['ofweek_distributed.spiders']
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)
        print("✅ 爬虫进程初始化成功")

        # 运行指定的爬虫，使用正确的爬虫名称
        asyncio.run(process.crawl('of_week_distributed'))
        print("✅ 爬虫运行完成")

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
