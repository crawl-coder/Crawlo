#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : Crawlo 框架通用工具包（供用户使用）

注意：此模块包含预制的通用工具，供用户在编写爬虫时使用。
框架本身并不使用这些工具，它们完全独立于框架核心逻辑。
"""

# 日期工具
from .time_utils import (
    TimeUtils,
    parse_time,
    format_time,
    time_diff,
    to_timestamp,
    to_datetime,
    now,
    to_timezone,
    to_utc,
    to_local,
    from_timestamp_with_tz
)

# 数据清洗工具
from .text_utils import (
    TextCleaner,
    remove_html_tags,
    decode_html_entities,
    remove_extra_whitespace,
    remove_special_chars,
    normalize_unicode,
    clean_text,
    extract_numbers,
    extract_emails,
    extract_urls
)

# 预加载 utils.request 以避免循环导入
from crawlo.utils.request import fingerprint

# 文件下载工具
from .file_downloader import (
    FileDownloader,
)

# 自适应元素选择器
from .adaptive_selector import (
    ElementFingerprint,
    SimilarityMatcher,
    FingerprintStorage,
    SqliteStorage,
    RedisStorage,
)

__all__ = [
    # 日期工具
    "TimeUtils",
    "parse_time",
    "format_time",
    "time_diff",
    "to_timestamp",
    "to_datetime",
    "now",
    "to_timezone",
    "to_utc",
    "to_local",
    "from_timestamp_with_tz",
    
    # 数据清洗工具
    "TextCleaner",
    "remove_html_tags",
    "decode_html_entities",
    "remove_extra_whitespace",
    "remove_special_chars",
    "normalize_unicode",
    "clean_text",
    "extract_numbers",
    "extract_emails",
    "extract_urls",
    
    # 文件下载工具
    "FileDownloader",
    
    # 自适应元素选择器
    "ElementFingerprint",
    "SimilarityMatcher",
    "FingerprintStorage",
    "SqliteStorage",
    "RedisStorage",
]
