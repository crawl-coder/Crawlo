#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 数据清洗工具包
"""

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
    extract_urls
)

from .data_formatter import (
    DataFormatter,
    format_number,
    format_currency,
    format_percentage,
    format_phone_number,
    format_chinese_id_card,
    capitalize_words
)

from .encoding_converter import (
    EncodingConverter,
    detect_encoding,
    to_utf8,
    convert_encoding
)

__all__ = [
    "TextCleaner",
    "DataFormatter",
    "EncodingConverter",
    "remove_html_tags",
    "decode_html_entities",
    "remove_extra_whitespace",
    "remove_special_chars",
    "normalize_unicode",
    "clean_text",
    "extract_numbers",
    "extract_emails",
    "extract_urls",
    "format_number",
    "format_currency",
    "format_percentage",
    "format_phone_number",
    "format_chinese_id_card",
    "capitalize_words",
    "detect_encoding",
    "to_utf8",
    "convert_encoding"
]