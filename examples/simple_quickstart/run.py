#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""simple_quickstart 启动入口。"""

import asyncio
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.crawler import CrawlerProcess


def main():
    process = CrawlerProcess()
    try:
        asyncio.run(process.crawl("simple_ofweek"))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"运行失败: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
