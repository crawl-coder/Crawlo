#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 框架通用辅助工具包（已迁移至 crawlo.utils）

此模块为向后兼容层，所有代码已迁移至 crawlo.utils 子包：
- time_utils → crawlo.utils.time_utils
- text_cleaner → crawlo.utils.text.cleaner
- file_downloader → crawlo.utils.file_downloader
- mysql_exists_checker → crawlo.utils.db.mysql_exists_checker
- adaptive_selector → crawlo.utils.adaptive_selector
"""

import sys
import warnings
import importlib

# 注册旧子模块路径到新位置，使 from crawlo.helpers.xxx import Yyy 仍可用
_MODULE_MAP = {
    'crawlo.helpers.time_utils': 'crawlo.utils.time_utils',
    'crawlo.helpers.text_cleaner': 'crawlo.utils.text.cleaner',
    'crawlo.helpers.file_downloader': 'crawlo.utils.file_downloader',
    'crawlo.helpers.mysql_exists_checker': 'crawlo.utils.db.mysql_exists_checker',
    'crawlo.helpers.adaptive_selector': 'crawlo.utils.adaptive_selector',
    'crawlo.helpers.adaptive_selector.element_fingerprint': 'crawlo.utils.adaptive_selector.element_fingerprint',
    'crawlo.helpers.adaptive_selector.similarity_matcher': 'crawlo.utils.adaptive_selector.similarity_matcher',
    'crawlo.helpers.adaptive_selector.storage': 'crawlo.utils.adaptive_selector.storage',
}
for _old, _new in _MODULE_MAP.items():
    if _old not in sys.modules:
        sys.modules[_old] = importlib.import_module(_new)

# 日期工具 — 无 logging 依赖，可立即导入
from crawlo.utils.time_utils import (
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
from crawlo.utils.text.cleaner import (
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

warnings.warn(
    "crawlo.helpers is deprecated, use crawlo.utils instead",
    DeprecationWarning,
    stacklevel=2,
)


def __getattr__(name):
    """延迟导入 file_downloader 和 adaptive_selector，避免循环导入。"""
    if name in ('MySQLExistsChecker', 'check_exists'):
        from crawlo.utils.db.mysql_exists_checker import MySQLExistsChecker, check_exists
        return globals().get(name) or (MySQLExistsChecker if name == 'MySQLExistsChecker' else check_exists)
    elif name == 'FileDownloader':
        from crawlo.utils.file_downloader import FileDownloader
        return FileDownloader
    elif name in ('ElementFingerprint', 'SimilarityMatcher',
                  'FingerprintStorage', 'SqliteStorage', 'RedisStorage'):
        # 注册 adaptive_selector 子模块路径
        import importlib
        for sub in ('__init__', 'element_fingerprint', 'similarity_matcher', 'storage'):
            old_path = f'crawlo.helpers.adaptive_selector.{sub}' if sub != '__init__' else 'crawlo.helpers.adaptive_selector'
            new_path = f'crawlo.utils.adaptive_selector.{sub}' if sub != '__init__' else 'crawlo.utils.adaptive_selector'
            if old_path not in sys.modules:
                sys.modules[old_path] = importlib.import_module(new_path)
        from crawlo.utils.adaptive_selector import (
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
