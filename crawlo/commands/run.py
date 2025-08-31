"""
命令行入口：crawlo run <spider_name>
用于运行指定名称的爬虫。
"""

import asyncio
from pathlib import Path
import configparser

from crawlo.crawler import CrawlerProcess
from crawlo.utils.project import get_settings
from crawlo.utils.log import get_logger

logger = get_logger(__name__)


def main(args):
    """
    运行指定爬虫的主函数
    用法:
        crawlo run <spider_name>
        crawlo run all
    """
    if len(args) < 1:
        print("Usage: crawlo run <spider_name>|all")
        print("Examples:")
        print("  crawlo run baidu")
        print("  crawlo run all")
        return 1

    spider_arg = args[0]

    try:
        # 1. 获取项目根目录
        project_root = get_settings().get('PROJECT_ROOT')
        if not project_root:
            print("❌ Error: Cannot determine project root.")
            return 1

        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

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

        # 3. 创建 CrawlerProcess 并自动发现爬虫模块
        spider_modules = [f"{project_package}.spiders"]
        settings = get_settings()
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)

        # === 新增：支持 'all' ===
        if spider_arg.lower() == "all":
            spider_names = process.get_spider_names()
            if not spider_names:
                print("❌ No spiders found. Make sure spiders are defined and imported.")
                return 1

            print(f"🚀 Starting ALL {len(spider_names)} spiders:")
            for name in sorted(spider_names):
                cls = process.get_spider_class(name)
                print(f"   🕷️  {name} ({cls.__name__})")
            print("-" * 50)

            # 启动所有爬虫
            asyncio.run(process.crawl(spider_names))
            return 0

        # === 原有：启动单个爬虫 ===
        spider_name = spider_arg
        if not process.is_spider_registered(spider_name):
            print(f"❌ Error: Spider with name '{spider_name}' not found.")
            available_names = process.get_spider_names()
            if available_names:
                print("💡 Available spiders:")
                for name in sorted(available_names):
                    cls = process.get_spider_class(name)
                    print(f"   - {name} (class: {cls.__name__})")
            else:
                print("💡 No spiders found. Make sure your spider classes are defined and imported.")
            return 1

        spider_class = process.get_spider_class(spider_name)

        # 打印启动信息
        print(f"🚀 Starting spider: {spider_name}")
        print(f"📁 Project: {project_package}")
        print(f"🕷️  Class: {spider_class.__name__}")
        print("-" * 50)

        # 启动爬虫
        asyncio.run(process.crawl(spider_name))

        print("-" * 50)
        print("✅ Spider completed successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Spider interrupted by user.")
        return 1
    except Exception as e:
        print(f"❌ Error running spider: {e}")
        import traceback
        traceback.print_exc()
        return 1


def list_available_spiders(project_package: str):
    """
    列出指定项目包中所有可用的爬虫（用于调试或命令行扩展）
    """
    try:
        # 临时创建一个 CrawlerProcess 来发现爬虫
        process = CrawlerProcess(spider_modules=[f"{project_package}.spiders"])
        available_names = process.get_spider_names()

        if not available_names:
            print("   No spiders found. Make sure:")
            print("   - spiders/ 目录存在")
            print("   - 爬虫类继承 Spider 且定义了 name")
            print("   - 模块被导入（可通过 __init__.py 触发）")
            return

        print(f"Found {len(available_names)} spider(s):")
        for name in sorted(available_names):
            cls = process.get_spider_class(name)
            module = cls.__module__.replace(project_package + ".", "")
            print(f"   - {name} ({cls.__name__} @ {module})")
    except Exception as e:
        print(f"❌ Failed to list spiders: {e}")
        import traceback
        traceback.print_exc()


def run_spider_by_name(spider_name: str, project_package: str = None):
    """
    在代码中直接运行某个爬虫（需提供 project_package）
    """
    if project_package is None:
        # 尝试从配置读取
        cfg_file = Path('crawlo.cfg')
        if cfg_file.exists():
            config = configparser.ConfigParser()
            config.read(cfg_file, encoding='utf-8')
            if config.has_option('settings', 'default'):
                project_package = config.get('settings', 'default').split('.')[0]

    if not project_package:
        print("❌ Error: project_package is required.")
        return 1

    # 添加项目路径
    project_root = get_settings().get('PROJECT_ROOT')
    if project_root and str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 复用 main 函数逻辑
    args = [spider_name]
    return main(args)


if __name__ == '__main__':
    """
    允许直接运行：
        python -m crawlo.commands.run <spider_name>
    """
    import sys

    sys.exit(main(sys.argv[1:]))
