#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
此扁平模块已迁移至 `crawlo.crawler` 子包。

保持 `import crawlo.crawler` / `from crawlo.crawler import CrawlerProcess` 的用户代码完全兼容，
仅在直接 import 本文件时打印一条 DeprecationWarning（调用方无感即可）。

未来版本（如 v1.0）会移除该扁平文件，届时仅 `crawlo.crawler.<module>` 子包路径可用。
"""
from __future__ import annotations

import warnings

from crawlo.crawler import (  # noqa: F401 (re-export all public APIs)
    CrawlerState,
    CrawlerMetrics,
    Crawler,
    CrawlerProcess,
    CrawloFramework,
    get_framework,
    reset_framework,
    run_spider,
    run_spiders,
    create_crawler,
    configure_framework,
    initialize_framework,
    is_framework_ready,
    get_logger,
)

warnings.warn(
    "`crawlo.crawler` 扁平模块已迁至 `crawlo.crawler` 子包；"
    "现通过兼容层 re-export，行为不变。后续版本将移除该扁平文件，建议直接使用 "
    "`from crawlo import CrawlerProcess / CrawloFramework` 或 `from crawlo.crawler import ...`。",
    DeprecationWarning,
    stacklevel=2,
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
