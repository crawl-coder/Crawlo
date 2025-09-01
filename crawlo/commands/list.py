#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:33
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo list，用于列出所有已注册的爬虫
"""

import sys
import configparser
from pathlib import Path
from importlib import import_module

from crawlo.crawler import CrawlerProcess
from crawlo.utils.log import get_logger


logger = get_logger(__name__)


def get_project_root():
    """
    自动检测项目根目录：从当前目录向上查找 crawlo.cfg
    找到后返回该目录路径（字符串），最多向上查找10层。
    """
    current = Path.cwd()

    for _ in range(10):
        cfg = current / "crawlo.cfg"
        if cfg.exists():
            return str(current)

        # 到达文件系统根目录
        if current == current.parent:
            break
        current = current.parent

    return None  # 未找到


def main(args):
    """
    主函数：列出所有可用爬虫
    用法: crawlo list
    """
    if args:
        print("❌ Usage: crawlo list")
        return 1

    try:
        # 1. 查找项目根目录
        project_root = get_project_root()
        if not project_root:
            print("❌ Error: Cannot find 'crawlo.cfg'. Are you in a crawlo project?")
            print("💡 Tip: Run this command inside your project directory, or create a project with 'crawlo startproject'.")
            return 1

        project_root_path = Path(project_root)
        project_root_str = str(project_root_path)

        # 2. 将项目根加入 Python 路径，以便导入项目模块
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        # 3. 读取 crawlo.cfg 获取 settings 模块
        cfg_file = project_root_path / "crawlo.cfg"
        config = configparser.ConfigParser()
        config.read(cfg_file, encoding="utf-8")

        if not config.has_section("settings") or not config.has_option("settings", "default"):
            print("❌ Error: Invalid crawlo.cfg — missing [settings] or 'default' option.")
            return 1

        settings_module = config.get("settings", "default")
        project_package = settings_module.split(".")[0]

        # 4. 确保项目包可导入（可选：尝试导入以触发异常）
        try:
            import_module(project_package)
        except ImportError as e:
            print(f"❌ Failed to import project package '{project_package}': {e}")
            return 1

        # 5. 初始化 CrawlerProcess 并加载爬虫模块
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(spider_modules=spider_modules)

        # 6. 获取所有爬虫名称
        spider_names = process.get_spider_names()
        if not spider_names:
            print("📭 No spiders found in 'spiders/' directory.")
            print("💡 Make sure:")
            print("   • Spider classes inherit from `crawlo.spider.Spider`")
            print("   • Each spider has a `name` attribute")
            print("   • Spiders are imported in `spiders/__init__.py` (if using package)")
            return 1

        # 7. 输出爬虫列表
        print(f"📋 Found {len(spider_names)} spider(s):")
        print("-" * 60)
        for name in sorted(spider_names):
            spider_cls = process.get_spider_class(name)
            module_name = spider_cls.__module__.replace(f"{project_package}.", "")
            print(f"🕷️  {name:<20} {spider_cls.__name__:<25} ({module_name})")
        print("-" * 60)
        return 0

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.exception("Exception during 'crawlo list'")
        return 1


if __name__ == "__main__":
    """
    支持直接运行：
        python -m crawlo.commands.list
    """
    sys.exit(main(sys.argv[1:]))