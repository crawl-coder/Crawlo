# crawlo/commands/run.py
import asyncio
import importlib
import sys
from pathlib import Path
import configparser

from crawlo.crawler import CrawlerProcess
from crawlo.utils.project import get_settings
from crawlo.utils.log import get_logger
from crawlo.utils.spider_loader import SpiderLoader

logger = get_logger(__name__)


def main(args):
    """
    运行指定爬虫的主函数
    用法: crawlo run <spider_name>
    """
    if len(args) < 1:
        print("Usage: crawlo run <spider_name>")
        print("Example: crawlo run baidu")
        return 1

    spider_name = args[0]

    try:
        # 1. 获取项目根目录
        project_root = get_settings()

        # 将项目根目录添加到 Python 路径
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # 2. 读取配置文件获取项目包名
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

        # 3. 查找并加载指定名称的 Spider
        spider_class = find_spider_by_name(project_package, spider_name)
        if spider_class is None:
            return 1

        # 4. 创建 CrawlerProcess 并运行单个爬虫
        settings = get_settings()
        process = CrawlerProcess(settings)

        print(f"🚀 Starting spider: {spider_class.name}")
        print(f"📁 Project: {project_package}")
        print(f"🕷️  Class: {spider_class.__name__}")
        print("-" * 50)

        # 运行单个爬虫
        asyncio.run(process.crawl(spider_class))

        print("-" * 50)
        print("✅ Spider completed successfully!")
        return 0

    except Exception as e:
        print(f"❌ Error running spider: {e}")
        import traceback
        traceback.print_exc()
        return 1


def find_spider_by_name(project_package: str, target_spider_name: str):
    """使用 SpiderLoader 查找爬虫"""
    loader = SpiderLoader(project_package)
    spider_class = loader.load(target_spider_name)

    if spider_class is None:
        print(f"❌ Error: Spider with name '{target_spider_name}' not found")
        print("💡 Available spiders:")
        available_spiders = loader.list()
        for spider_name in available_spiders:
            print(f"   - {spider_name}")
        return None

    return spider_class


def list_available_spiders(project_package: str):
    """
    列出所有可用的爬虫
    """
    spiders_dir = Path.cwd() / project_package / 'spiders'
    if not spiders_dir.exists():
        print("   No spiders directory found")
        return

    spider_count = 0
    for py_file in spiders_dir.glob("*.py"):
        if py_file.name.startswith('_'):
            continue

        module_name = py_file.stem
        spider_module_path = f"{project_package}.spiders.{module_name}"

        try:
            module = importlib.import_module(spider_module_path)
        except ImportError:
            continue

        # 查找模块中所有 Spider 子类
        from crawlo.spider import Spider
        for attr_name in dir(module):
            attr_value = getattr(module, attr_name)
            if (isinstance(attr_value, type) and
                    issubclass(attr_value, Spider) and
                    attr_value != Spider and
                    hasattr(attr_value, 'name')):
                print(f"   - {attr_value.name} (class: {attr_value.__name__}, module: {module_name})")
                spider_count += 1

    if spider_count == 0:
        print("   No spiders found")


def run_spider_by_name(spider_name: str, project_root: Path = None):
    """
    直接在代码中通过 spider name 运行爬虫
    """
    if project_root:
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

    args = [spider_name]
    return main(args)


if __name__ == '__main__':
    # 允许直接运行: python -m crawlo.commands.run <spider_name>
    import sys

    sys.exit(main(sys.argv[1:]))