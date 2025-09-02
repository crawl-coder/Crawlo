#!/usr/bin/python
# -*- coding: UTF-8 -*-
from pathlib import Path
import asyncio


# --- 正常导入 ---
from crawlo.crawler import CrawlerProcess
from spiders.miit import TelecomDeviceLicensesSpider  # ✅ 简洁导入

async def main():
    process = CrawlerProcess()
    await process.crawl([TelecomDeviceLicensesSpider])

if __name__ == '__main__':
    asyncio.run(main())