#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawler 子包对外门面。

从 _crawler / _process / _framework 三个内部模块 re-export 所有公开 API，
保持 `from crawlo.crawler import CrawlerProcess` 与拆分前完全兼容。
"""
from ._crawler import (
    CrawlerState, CrawlerMetrics, Crawler,
    initialize_framework, is_framework_ready, get_logger,
)
from ._process import CrawlerProcess
from ._framework import (
    CrawloFramework,
    get_framework,
    reset_framework,
    run_spider,
    run_spiders,
    create_crawler,
    configure_framework,
)

__all__ = [
    'CrawlerState',
    'CrawlerMetrics',
    'Crawler',
    'CrawlerProcess',
    'CrawloFramework',
    'get_framework',
    'reset_framework',
    'run_spider',
    'run_spiders',
    'create_crawler',
    'configure_framework',
    'initialize_framework',
    'is_framework_ready',
    'get_logger',
]
