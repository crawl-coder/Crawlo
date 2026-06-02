#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : Crawlo 框架通用辅助工具包（供用户使用）

注意：此模块包含预制的通用工具，供用户在编写爬虫时使用。
框架本身并不使用这些工具，它们完全独立于框架核心逻辑。
"""

# 日期工具 — 无 logging 依赖，可立即导入
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

# 数据清洗工具 — 无 logging 依赖
from .text_cleaner import (
    TextCleaner,
    remove_html_tags,
    decode_html_entities,
    remove_extra_whitespace,
    remove_special_chars,
    normalize_unicode,
    clean_text,
    extract_numbers,
    extract_emails,
    extract_urls,
    extract_phones,
    strip_control_chars,
    truncate,
)


def __getattr__(name):
    """延迟导入 file_downloader 和 adaptive_selector，避免循环导入。
    
    这两个模块依赖 crawlo.logging，但 helpers 包被 __init__.py 较早导入，
    此时 logging 模块可能尚未完成初始化，导致循环 ImportError。
    """
    if name in ('MySQLExistsChecker', 'check_exists'):
        from .mysql_exists_checker import MySQLExistsChecker, check_exists
        return globals().get(name) or (MySQLExistsChecker if name == 'MySQLExistsChecker' else check_exists)
    elif name == 'FileDownloader':
        from .file_downloader import FileDownloader
        return FileDownloader
    elif name in ('ElementFingerprint', 'SimilarityMatcher',
                  'FingerprintStorage', 'SqliteStorage', 'RedisStorage'):
        from .adaptive_selector import (
            ElementFingerprint, SimilarityMatcher,
            FingerprintStorage, SqliteStorage, RedisStorage,
        )
        return globals().get(name)
    raise AttributeError(f"module 'crawlo.helpers' has no attribute '{name}'")


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
    "extract_phones",
    "strip_control_chars",
    "truncate",
    
    # 文件下载工具
    "FileDownloader",
    
    # 自适应元素选择器
    "ElementFingerprint",
    "SimilarityMatcher",
    "FingerprintStorage",
    "SqliteStorage",
    "RedisStorage",
    
    # MySQL 数据存在性检查工具
    "MySQLExistsChecker",
    "check_exists",
]
