# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-02-05 13:57
# @Author  :   oscar
# @Desc    :   Crawlo 框架核心工具模块

此模块包含框架内部使用的核心工具，不推荐用户直接使用。
用户应该使用 crawlo.helpers 中的通用工具。
"""

from .request.response_helper import (
    parse_cookies,
    regex_search,
    regex_findall,
    regex_findone,
    get_header_value
)

from .request.fingerprint import FingerprintGenerator

# 编码检测
from .encoding_detector import (
    EncodingDetector,
    detect_encoding,
    decode_body,
)

# 中间件优先级常量
from crawlo.middleware.priority import (
    MiddlewarePriority,
    MiddlewarePriorityGroup,
    BUILTIN_MIDDLEWARE_PRIORITIES,
    get_default_middleware_priority,
)


def __getattr__(name):
    """延迟导入 request_serializer 和 batch，避免循环导入。
    
    这两个模块间接依赖 crawlo.logging（通过 crawlo.network → response），
    而 logging/manager.py 通过 from crawlo.utils.singleton import SingletonMeta
    触发本包的导入，此时 logging 尚未完成初始化，直接导入会形成循环。
    """
    if name == 'RequestSerializer':
        from .request.request_serializer import RequestSerializer
        return RequestSerializer
    elif name in ('BatchProcessor', 'RedisBatchProcessor',
                  'batch_process', 'process_in_batches'):
        from .batch import (
            BatchProcessor, RedisBatchProcessor,
            batch_process, process_in_batches
        )
        return globals().get(name)
    raise AttributeError(f"module 'crawlo.utils' has no attribute '{name}'")


__all__ = [
    # response_helper
    "parse_cookies",
    "regex_search",
    "regex_findall",
    "regex_findone",
    "get_header_value",
    # fingerprint
    "FingerprintGenerator",
    # request_serializer (lazy)
    "RequestSerializer",
    # encoding_detector
    "EncodingDetector",
    "detect_encoding",
    "decode_body",
    # batch (lazy)
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
