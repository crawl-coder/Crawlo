# -*- coding: utf-8 -*-
"""
Created on {DATE}
---------
@summary: 爬虫入口
---------
@author: {USER}
"""

from crawlo import ArgumentParser

from spiders import *



def crawl_xxx():
    """
    Spider爬虫
    """
    spider = xxx.XXXSpider(redis_key="xxx:xxx")
    spider.start()



if __name__ == "__main__":
    parser = ArgumentParser(description="xxx爬虫")

    parser.add_argument(
        "--crawl_xxx", action="store_true", help="xxx爬虫", function=crawl_xxx
    )
    parser.start()

    # main.py作为爬虫启动的统一入口，提供命令行的方式启动多个爬虫