#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统一指纹生成工具
================
提供一致的指纹生成方法，确保在框架各组件中生成的指纹保持一致。

特点:
- 算法优化: 请求指纹使用 MD5（高性能），数据指纹使用 SHA256（高准确）
- 格式一致: 相同数据在不同场景下生成相同指纹
- 高性能: 针对不同场景选择最优算法
- 易扩展: 支持不同类型数据的指纹生成
"""

import hashlib
from typing import Any, Dict, Iterable
from w3lib.url import canonicalize_url


def generate_data_fingerprint(data: Any) -> str:
    """
    生成数据指纹

    基于数据内容生成唯一指纹，用于去重判断。
    使用 SHA256 算法确保数据准确性。

    :param data: 要生成指纹的数据（支持 dict, Item, namedtuple, str 等类型）
    :return: 数据指纹（hex string，64字符）
    """
    # 将数据转换为可序列化的字典
    if hasattr(data, 'to_dict'):
        # 支持 Item 等实现了 to_dict 方法的对象
        data_dict = data.to_dict()
    elif hasattr(data, '_asdict'):
        # 支持 namedtuple 对象
        data_dict = data._asdict()
    elif isinstance(data, dict):
        data_dict = data
    else:
        # 其他类型转换为字符串处理
        data_dict = {'__data__': str(data)}

    # 对字典进行排序以确保一致性
    sorted_items = sorted(data_dict.items())

    # 生成指纹字符串
    fingerprint_string = '|'.join([f"{k}={v}" for k, v in sorted_items if v is not None])

    # 使用 SHA256 生成固定长度的指纹（数据去重需要高准确性）
    return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()


def generate_request_fingerprint(
        method: str,
        url: str,
        body: bytes = b'',
        headers: Dict[str, str] = None,
        meta: Dict[str, Any] = None,
        include_headers: Iterable[str] = None,
) -> str:
    """
    生成请求指纹

    默认基于 method、规范化 URL 与 body 生成唯一指纹
    （与 Scrapy 默认行为一致：headers/meta 不参与，避免随机 UA、
    按请求变化的 Cookie 等导致同一 URL 去重失效）。
    使用 MD5 算法确保高性能（请求去重频率极高，不需要密码学安全）。

    :param method: HTTP方法
    :param url: 请求URL
    :param body: 请求体
    :param headers: 请求头（仅在 ``include_headers`` 显式指定时参与指纹）
    :param meta: 元数据（由调用方预先筛选，如 ``DUPEFILTER_INCLUDE_META``）
    :param include_headers: 纳入指纹的 header 名称列表（大小写不敏感）；
        为空/None 时所有 headers 均不参与指纹
    :return: 请求指纹（hex string，32字符）
    """
    hash_func = hashlib.md5()  # nosec B324

    hash_func.update(method.encode('utf-8'))
    hash_func.update(canonicalize_url(url).encode('utf-8'))
    hash_func.update(body or b'')

    # headers：默认不参与；显式指定 include_headers 时才纳入指定项
    if include_headers and headers:
        header_map = {str(k).lower(): v for k, v in headers.items()}
        for name in sorted({str(h).lower() for h in include_headers}):
            value = header_map.get(name)
            if value is None:
                continue
            hash_func.update(f"{name}:{value}".encode('utf-8'))

    # meta：调用方预先筛选后传入（如 DUPEFILTER_INCLUDE_META），全部参与
    if meta:
        for key in sorted(meta.keys(), key=str):
            hash_func.update(f"meta_{key}:{str(meta[key])}".encode('utf-8'))

    return hash_func.hexdigest()


class FingerprintGenerator:
    """指纹生成器类"""

    @staticmethod
    def item_fingerprint(item) -> str:
        """
        生成数据项指纹

        :param item: 数据项
        :return: 指纹字符串
        """
        return generate_data_fingerprint(item)

    @staticmethod
    def request_fingerprint(method: str, url: str, body: bytes = b'', headers: Dict[str, str] = None, meta: Dict[str, Any] = None) -> str:
        """
        生成请求指纹

        :param method: HTTP方法
        :param url: 请求URL
        :param body: 请求体
        :param headers: 请求头（默认不参与指纹，与 Scrapy 一致）
        :param meta: 元数据（调用方预先筛选后传入）
        :return: 请求指纹（hex string，32字符）
        """
        return generate_request_fingerprint(method, url, body, headers, meta)

    @staticmethod
    def data_fingerprint(data: Any) -> str:
        """
        生成通用数据指纹

        :param data: 任意数据
        :return: 指纹字符串
        """
        return generate_data_fingerprint(data)
