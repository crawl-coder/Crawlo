# crawlo/commands/run.py
import asyncio
import importlib
from pathlib import Path

from crawlo.crawler import CrawlerProcess
from crawlo.utils.project import get_settings


def main(args):
    if len(args) < 1:
        print("Usage: crawlo run <spider_name>")
        return 1

    spider_name = args[0]

    # 1. 自动发现项目并加载 settings
    try:
        project_root = get_settings()  # get_settings() 返回项目根目录
        # 从 crawlo.cfg 获取 settings 模块名，推断项目包名
        import configparser
        cfg_file = Path(project_root) / 'crawlo.cfg'
        config = configparser.ConfigParser()
        config.read(cfg_file, encoding='utf-8')
        settings_module = config.get('settings', 'default')
        project_package = settings_module.split('.')[0]
    except Exception as e:
        print(f"Error loading project settings: {e}")
        return 1

    # 2. 动态导入 Spider 类
    try:
        # 假设 Spider 在 spiders 包下，模块名为 spider_name
        spider_module_path = f"{project_package}.spiders.{spider_name}"
        module = importlib.import_module(spider_module_path)

        # 查找 Spider 类（假设类名是 SpiderNameSpider）
        spider_class_name = f"{spider_name.capitalize()}Spider"
        if hasattr(module, spider_class_name):
            spider_class = getattr(module, spider_class_name)
        else:
            # 尝试查找类名是 spider_name 的类
            if hasattr(module, spider_name):
                spider_class = getattr(module, spider_name)
            else:
                print(f"Error: Spider class '{spider_class_name}' or '{spider_name}' not found in {spider_module_path}")
                return 1
    except ImportError as e:
        print(f"Error importing spider '{spider_name}': {e}")
        return 1

    # 3. 创建 CrawlerProcess 并运行
    try:
        settings = get_settings()

        process = CrawlerProcess(settings)
        print(f"Starting crawl with spider: {spider_class.name}")
        asyncio.run(process.crawl(spider_class))
        return 0
    except Exception as e:
        print(f"Error running crawler: {e}")
        return 1