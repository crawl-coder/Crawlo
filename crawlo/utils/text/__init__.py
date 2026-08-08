# -*- coding: UTF-8 -*-
"""文本处理工具子包"""

from .cleaner import (
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

__all__ = [
    'TextCleaner',
    'remove_html_tags',
    'decode_html_entities',
    'remove_extra_whitespace',
    'remove_special_chars',
    'normalize_unicode',
    'clean_text',
    'extract_numbers',
    'extract_emails',
    'extract_urls',
    'extract_phones',
    'strip_control_chars',
    'truncate',
]
