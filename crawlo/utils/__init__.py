#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-02-05 13:57
# @Author  :   oscar
# @Desc    :   工具模块集合

提供用于处理parsel选择器的辅助函数，用于提取文本和属性等操作。
所有方法都采用了简洁直观的命名风格，便于记忆和使用。
"""

from ..tools.date_tools import (
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

from .selector_helper import (
    extract_text,
    extract_texts,
    extract_attr,
    extract_attrs,
    is_xpath
)

from .encoding_helper import (
    html_body_declared_encoding,
    http_content_type_encoding,
    read_bom,
    resolve_encoding,
    html_to_unicode
)

from .response_helper import (
    parse_cookies,
    regex_search,
    regex_findall,
    get_header_value
)

__all__ = [
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
    "extract_text",
    "extract_texts",
    "extract_attr",
    "extract_attrs",
    "is_xpath",
    "html_body_declared_encoding",
    "http_content_type_encoding",
    "read_bom",
    "resolve_encoding",
    "html_to_unicode",
    "parse_cookies",
    "regex_search",
    "regex_findall",
    "get_header_value"
]