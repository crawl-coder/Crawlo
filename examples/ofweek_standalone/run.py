#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio

# 确保可以导入 crawlo 模块
# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)
# 爬虫示例目录
project_root = os.path.dirname(script_path)
# Crawlo 项目根目录（向上两级）
crawlo_project_root = os.path.dirname(os.path.dirname(project_root))

# 使用绝对路径确保可以找到 crawlo 模块
if crawlo_project_root not in sys.path:
    sys.path.insert(0, crawlo_project_root)

from crawlo.crawler import CrawlerProcess


def main():
    """运行爬虫"""
    try:
        # 检查是否启动定时任务模式
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            # 启动定时任务模式
            from crawlo.scheduling import start_scheduler
            # 获取当前脚本所在目录作为项目根目录
            project_root = os.path.dirname(os.path.abspath(__file__))
            start_scheduler(project_root)
        else:
            # 正常爬虫运行模式
            spider_name = sys.argv[1] if len(sys.argv) > 1 else 'of_week'
            
            # 加载爬虫配置
            from crawlo.settings.setting_manager import SettingManager
            settings = SettingManager()
            
            # 设置 SPIDER_MODULES
            settings.set('SPIDER_MODULES', ['ofweek_standalone.spiders'])
            
            asyncio.run(CrawlerProcess(settings).crawl(spider_name))
    except Exception as e:
        print(f"运行失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
    """
    python -m build
    twine upload dist/*
    pip install -i https://pypi.org/simple/ crawlo
    """
