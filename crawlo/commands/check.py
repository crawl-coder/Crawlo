#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-31 22:35
# @Author  :   crawl-coder
# @Desc    :   命令行入口：crawlo check， 检查所有爬虫定义是否合规。
"""
import sys
import configparser

from crawlo.crawler import CrawlerProcess
from crawlo.utils.project import get_settings
from crawlo.utils.log import get_logger


logger = get_logger(__name__)


def main(args):
    if args:
        print("Usage: crawlo check")
        return 1

    try:
        project_root = get_settings().get('PROJECT_ROOT')
        if not project_root:
            print("❌ Error: Cannot determine project root.")
            return 1

        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

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

        # 创建 CrawlerProcess 并发现爬虫
        process = CrawlerProcess(spider_modules=[f"{project_package}.spiders"])
        spider_names = process.get_spider_names()

        if not spider_names:
            print("📭 No spiders found.")
            return 1

        print(f"🔍 Checking {len(spider_names)} spider(s)...")
        print("-" * 60)

        issues_found = False
        for name in sorted(spider_names):
            cls = process.get_spider_class(name)
            issues = []

            if not hasattr(cls, 'name') or not cls.name:
                issues.append("missing or empty 'name' attribute")
            elif not isinstance(cls.name, str):
                issues.append("'name' is not a string")

            if not callable(getattr(cls, 'start_requests', None)):
                issues.append("missing or non-callable 'start_requests' method")

            if hasattr(cls, 'start_urls') and isinstance(cls.start_urls, str):
                issues.append("'start_urls' is a string, should be list/tuple")

            # 实例化检查（轻量）
            try:
                spider = cls.create_instance(None)
                if not callable(getattr(spider, 'parse', None)):
                    issues.append("no 'parse' method defined (optional but recommended)")
            except Exception as e:
                issues.append(f"failed to create instance: {e}")

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
            print("🎉 All spiders are compliant!")
            return 0

    except Exception as e:
        print(f"❌ Error during check: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))