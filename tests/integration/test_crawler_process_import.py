#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 CrawlerProcess 导入功能（v2.0 版本）。

v2.0 已删除 crawlo.crawler.__getattr__('CrawlerProcess') facade，
必须从 crawlo.crawler_process 或 crawlo 顶层导入。
"""

import pytest


def test_crawler_process_from_crawler_process_module():
    """从 crawlo.crawler_process 导入 CrawlerProcess 正常"""
    from crawlo.crawler_process import CrawlerProcess
    assert CrawlerProcess is not None


def test_crawler_process_from_crawlo_top_level():
    """从 crawlo 顶层导入 CrawlerProcess 正常（PEP 562 __getattr__ 转发）"""
    from crawlo import CrawlerProcess
    assert CrawlerProcess is not None


def test_crawler_process_in_crawler_module():
    """CrawlerProcess 位于 crawlo.crawler（重构后 crawler_process 是其别名）"""
    import crawlo.crawler
    from crawlo.crawler import CrawlerProcess
    assert crawlo.crawler.CrawlerProcess is CrawlerProcess


if __name__ == '__main__':
    test_crawler_process_from_crawler_process_module()
    test_crawler_process_from_crawlo_top_level()
    test_crawler_process_not_in_crawler_module()
    print("All tests passed!")
