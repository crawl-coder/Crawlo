# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-02-05 13:57
# @Author  :   oscar
# @Desc    :   Crawlo 框架核心工具模块

此模块包含框架内部使用的核心工具，不推荐用户直接使用。
用户应该使用 crawlo.tools 中的通用工具。
"""

from .request.response_helper import (
    parse_cookies,
    regex_search,
    regex_findall,
    get_header_value
)

from .request.fingerprint import FingerprintGenerator

from .request.request_serializer import RequestSerializer

# 编码检测
from .encoding_detector import (
    EncodingDetector,
    detect_encoding,
    decode_body,
)

# 批量处理
from .batch import (
    BatchProcessor,
    RedisBatchProcessor,
    batch_process,
    process_in_batches
)

# 中间件优先级常量
from .priority import (
    MiddlewarePriority,
    MiddlewarePriorityGroup,
    BUILTIN_MIDDLEWARE_PRIORITIES,
    get_default_middleware_priority,
)

__all__ = [
    # response_helper
    "parse_cookies",
    "regex_search",
    "regex_findall",
    "get_header_value",
    # fingerprint
    "FingerprintGenerator",
    # request_serializer
    "RequestSerializer",
    # encoding_detector
    "EncodingDetector",
    "detect_encoding",
    "decode_body",
    # batch
    "BatchProcessor",
    "RedisBatchProcessor",
    "batch_process",
    "process_in_batches",
    # priority
    "MiddlewarePriority",
    "MiddlewarePriorityGroup",
    "BUILTIN_MIDDLEWARE_PRIORITIES",
    "get_default_middleware_priority",
]