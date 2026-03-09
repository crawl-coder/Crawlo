# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-02-05 13:57
# @Author  :   oscar
# @Desc    :   Crawlo 框架核心工具模块

此模块包含框架内部使用的核心工具，不推荐用户直接使用。
用户应该使用 crawlo.tools 中的通用工具。
"""

# 框架内部使用的工具导出
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

from .request.response_helper import (
    parse_cookies,
    regex_search,
    regex_findall,
    get_header_value
)

from .request.fingerprint import FingerprintGenerator

from .request.request_serializer import RequestSerializer

# 批量处理
from .batch import (
    BatchProcessor,
    RedisBatchProcessor,
    batch_process,
    process_in_batches
)

__all__ = [
    # selector_helper
    "extract_text",
    "extract_texts",
    "extract_attr",
    "extract_attrs",
    "is_xpath",
    # encoding_helper
    "html_body_declared_encoding",
    "http_content_type_encoding",
    "read_bom",
    "resolve_encoding",
    "html_to_unicode",
    # response_helper
    "parse_cookies",
    "regex_search",
    "regex_findall",
    "get_header_value",
    # fingerprint
    "FingerprintGenerator",
    # request_serializer
    "RequestSerializer",
    # batch
    "BatchProcessor",
    "RedisBatchProcessor",
    "batch_process",
    "process_in_batches",
]