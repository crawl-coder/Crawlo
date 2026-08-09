# -*- coding: UTF-8 -*-
"""
No-limit dynamic browser downloader runner.

Uses CloakBrowser directly, zero download delay, maximum crawl speed.
    python run_no_limit.py
    python run_no_limit.py --max=50
"""
import sys
import os
import asyncio
import importlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
settings_mod = importlib.import_module('infoq_dynamic_test.settings_no_limit')

from crawlo.settings.setting_manager import SettingManager
from crawlo.crawler import CrawlerProcess


async def main():
    max_companies = 100
    for arg in sys.argv[1:]:
        if arg.startswith('--max='):
            max_companies = int(arg.split('=')[1])

    settings = SettingManager()
    settings.set_settings(settings_mod)

    print("=== No-limit Dynamic Browser Crawler ===")
    print(f"  Downloader: {settings.get('DOWNLOADER', 'N/A')}")
    print(f"  Concurrency: {settings.get('CONCURRENCY', 'N/A')}")
    print(f"  Delay: {settings.get('DOWNLOAD_DELAY', 'N/A')}s")
    print(f"  Max companies: {max_companies}")
    print()

    process = CrawlerProcess(settings)
    await process.crawl('baike_company', max_companies=max_companies)


if __name__ == '__main__':
    asyncio.run(main())
