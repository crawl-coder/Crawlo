#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:35
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo check，检查所有爬虫定义是否合规。
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
    从当前目录向上查找 crawlo.cfg，确定项目根目录
    """
    current = Path.cwd()

    for _ in range(10):
        cfg = current / "crawlo.cfg"
        if cfg.exists():
            return current

        if current == current.parent:
            break
        current = current.parent

    return None


def main(args):
    """
    主函数：检查所有爬虫定义的合规性
    用法: crawlo check
    """
    if args:
        print("❌ Usage: crawlo check")
        return 1

    try:
        # 1. 查找项目根目录
        project_root = get_project_root()
        if not project_root:
            print("❌ Error: Cannot find 'crawlo.cfg'. Are you in a crawlo project?")
            print("💡 Tip: Run this command inside your project directory.")
            return 1

        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        # 2. 读取 crawlo.cfg
        cfg_file = project_root / "crawlo.cfg"
        if not cfg_file.exists():
            print(f"❌ Error: Expected config file not found: {cfg_file}")
            return 1

        config = configparser.ConfigParser()
        config.read(cfg_file, encoding="utf-8")

        if not config.has_section("settings") or not config.has_option("settings", "default"):
            print("❌ Error: Missing [settings] section or 'default' option in crawlo.cfg")
            return 1

        settings_module = config.get("settings", "default")
        project_package = settings_module.split(".")[0]

        # 3. 确保项目包可导入
        try:
            import_module(project_package)
        except ImportError as e:
            print(f"❌ Failed to import project package '{project_package}': {e}")
            return 1

        # 4. 加载爬虫
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(spider_modules=spider_modules)
        spider_names = process.get_spider_names()

        if not spider_names:
            print("📭 No spiders found.")
            print("💡 Make sure:")
            print("   • Spiders are defined in the 'spiders' module")
            print("   • They have a `name` attribute")
            print("   • Modules are properly imported")
            return 1

        print(f"🔍 Checking {len(spider_names)} spider(s)...")
        print("-" * 60)

        issues_found = False

        for name in sorted(spider_names):
            cls = process.get_spider_class(name)
            issues = []

            # 检查 name 属性
            if not getattr(cls, "name", None):
                issues.append("missing or empty 'name' attribute")
            elif not isinstance(cls.name, str):
                issues.append("'name' is not a string")

            # 检查 start_requests 是否可调用
            if not callable(getattr(cls, "start_requests", None)):
                issues.append("missing or non-callable 'start_requests' method")

            # 检查 start_urls 类型（不应是字符串）
            if hasattr(cls, "start_urls") and isinstance(cls.start_urls, str):
                issues.append("'start_urls' is a string; should be list or tuple")

            # 实例化并检查 parse 方法（非强制但推荐）
            try:
                spider = cls.create_instance(None)
                if not callable(getattr(spider, "parse", None)):
                    issues.append("no 'parse' method defined (recommended)")
            except Exception as e:
                issues.append(f"failed to instantiate spider: {e}")

            # 输出结果
            if issues:
                print(f"❌ {name:<20} {cls.__name__}")
                for issue in issues:
                    print(f"     • {issue}")
                issues_found = True
            else:
                print(f"✅ {name:<20} {cls.__name__} (OK)")

        print("-" * 60)

        if issues_found:
            print("⚠️  Some spiders have issues. Please fix them.")
            return 1
        else:
            print("🎉 All spiders are compliant and well-defined!")
            return 0

    except Exception as e:
        print(f"❌ Unexpected error during check: {e}")
        logger.exception("Exception in 'crawlo check'")
        return 1


if __name__ == "__main__":
    """
    支持直接运行：
        python -m crawlo.commands.check
    """
    sys.exit(main(sys.argv[1:]))