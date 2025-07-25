#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-07-08 08:55
# @Author  :   crawl-coder
# @Desc    :   None
"""
import json
import hashlib
from typing import Any, Optional, Iterable, Union
from w3lib.url import canonicalize_url

from crawlo import Request


def to_bytes(data: Any, encoding='utf-8') -> bytes:
    """
    将各种类型统一转换为 bytes。
    支持 str, bytes, dict, None 及其他可转为字符串的类型。
    """
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode(encoding)
    if isinstance(data, dict):
        return json.dumps(data, sort_keys=True, ensure_ascii=False).encode(encoding)
    if data is None:
        return b''
    return str(data).encode(encoding)


def request_fingerprint(
        request: Request,
        include_headers: Optional[Iterable[Union[bytes, str]]] = None
) -> str:
    """
    生成请求指纹，基于方法、标准化 URL、body 和可选的 headers。
    使用 SHA256 哈希算法以提高安全性。

    :param request: Request 对象（需包含 method, url, body, headers）
    :param include_headers: 指定要参与指纹计算的 header 名称列表（str 或 bytes）
    :return: 请求指纹（hex string）
    """
    hash_func = hashlib.sha256()

    # 基本字段
    hash_func.update(to_bytes(request.method))
    hash_func.update(to_bytes(canonicalize_url(request.url)))
    hash_func.update(request.body or b'')

    # 处理 headers
    if include_headers:
        headers = request.headers  # 假设 headers 是类似字典或 MultiDict 的结构
        for header_name in include_headers:
            name_bytes = to_bytes(header_name).lower()  # 统一转为小写进行匹配
            value = b''

            # 兼容 headers 的访问方式（如 MultiDict 或 dict）
            if hasattr(headers, 'get_all'):
                # 如 scrapy.http.Headers 的 get_all 方法
                values = headers.get_all(name_bytes)
                value = b';'.join(values) if values else b''
            elif hasattr(headers, '__getitem__'):
                # 如普通 dict
                try:
                    raw_value = headers[name_bytes]
                    if isinstance(raw_value, list):
                        value = b';'.join(to_bytes(v) for v in raw_value)
                    else:
                        value = to_bytes(raw_value)
                except (KeyError, TypeError):
                    value = b''
            else:
                value = b''

            hash_func.update(name_bytes + b':' + value)

    return hash_func.hexdigest()


def set_request(request: Request, priority: int) -> None:
    request.meta['depth'] = request.meta.setdefault('depth', 0) + 1
    if priority:
        request.priority -= request.meta['depth'] * priority

