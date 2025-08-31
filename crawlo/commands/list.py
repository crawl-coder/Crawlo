#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-31 22:33
# @Author  :   crawl-coder
# @Desc    :   命令行入口：crawlo list，用于列出所有已注册的爬虫
"""
import sys
import configparser

from crawlo.crawler import CrawlerProcess
from crawlo.utils.project import get_settings
from crawlo.utils.log import get_logger


logger = get_logger(__name__)


def main(args):
    """
    列出所有可用爬虫
    用法: crawlo list
    """
    if args:
        print("Usage: crawlo list")
        return 1

    try:
        # 1. 获取项目根目录
        project_root = get_settings().get('PROJECT_ROOT')
        if not project_root:
            print("❌ Error: Cannot determine project root.")
            return 1

        # 将项目根目录加入 sys.path
        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        # 2. 读取 crawlo.cfg 获取项目包名
        cfg_file = project_root / 'crawlo.cfg'
        if not cfg_file.exists():
            print(f"❌ Error: crawlo.cfg not found in {project_root}")
            return 1

        config = configparser.ConfigParser()
        config.read(cfg_file, encoding='utf-8')

        if not config.has_section('settings') or not config.has_option('settings', 'default'):
            print("❌ Error: Missing [settings] section or 'default' option in crawlo.cfg")
            return 1

        settings_module = config.get('settings', 'default')
        project_package = settings_module.split('.')[0]

        # 3. 创建 CrawlerProcess 并自动发现爬虫
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(spider_modules=spider_modules)

        # 4. 获取所有爬虫信息
        spider_names = process.get_spider_names()
        if not spider_names:
            print("📭 No spiders found.")
            print("💡 Make sure:")
            print("   - Your spider classes inherit from `Spider`")
            print("   - They define a `name` attribute")
            print("   - The modules are imported (e.g. via __init__.py)")
            return 1

        # 5. 输出爬虫列表
        print(f"📋 Found {len(spider_names)} spider(s):")
        print("-" * 50)
        for name in sorted(spider_names):
            cls = process.get_spider_class(name)
            module = cls.__module__.replace(project_package + ".", "")  # 简化模块名
            print(f"🕷️  {name:<20} {cls.__name__:<25} ({module})")
        print("-" * 50)
        return 0

    except Exception as e:
        print(f"❌ Error listing spiders: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    """
    允许直接运行：
        python -m crawlo.commands.list
    """
    sys.exit(main(sys.argv[1:]))