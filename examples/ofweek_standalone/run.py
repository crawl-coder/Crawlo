#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import asyncio

from crawlo.crawler import CrawlerProcess


async def _run() -> None:
    cp = CrawlerProcess()
    await cp.crawl('of_week')


def main() -> None:
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--schedule':
            from crawlo.commands.scheduler import start_scheduler
            project_root = os.path.dirname(os.path.abspath(__file__))
            start_scheduler(project_root)
        else:
            asyncio.run(_run())
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
