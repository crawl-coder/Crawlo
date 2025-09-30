#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
统一指纹生成工具
================
提供一致的指纹生成方法，确保在框架各组件中生成的指纹保持一致。

特点:
- 算法统一: 所有指纹生成使用相同的算法(SHA256)
- 格式一致: 相同数据在不同场景下生成相同指纹
- 高性能: 优化的实现确保高效生成
- 易扩展: 支持不同类型数据的指纹生成
"""

import hashlib
from typing import Any, Dict
from w3lib.url import canonicalize_url


def generate_data_fingerprint(data: Any) -> str:
    """
    生成数据指纹
    
    基于数据内容生成唯一指纹，用于去重判断。
    使用 SHA256 算法确保安全性。
    
    :param data: 要生成指纹的数据（支持 dict, Item, namedtuple, str 等类型）
    :return: 数据指纹（hex string）
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
    
    # 使用 SHA256 生成固定长度的指纹
    return hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()


def generate_request_fingerprint(
        method: str,
        url: str,
        body: bytes = b'',
        headers: Dict[str, str] = None
) -> str:
    """
    生成请求指纹
    
    基于请求的方法、URL、body 和可选的 headers 生成唯一指纹。
    使用 SHA256 算法确保安全性。
    
    :param method: HTTP方法
    :param url: 请求URL
    :param body: 请求体
    :param headers: 请求头
    :return: 请求指纹（hex string）
    """
    hash_func = hashlib.sha256()
    
    # 基本字段
    hash_func.update(method.encode('utf-8'))
    hash_func.update(canonicalize_url(url).encode('utf-8'))
    hash_func.update(body or b'')
    
    # 可选的 headers
    if headers:
        # 对 headers 进行排序以确保一致性
        sorted_headers = sorted(headers.items())
        for name, value in sorted_headers:
            hash_func.update(f"{name}:{value}".encode('utf-8'))
    
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
    def request_fingerprint(method: str, url: str, body: bytes = b'', headers: Dict[str, str] = None) -> str:
        """
        生成请求指纹
        
        :param method: HTTP方法
        :param url: 请求URL
        :param body: 请求体
        :param headers: 请求头
        :return: 指纹字符串
        """
        return generate_request_fingerprint(method, url, body, headers)
    
    @staticmethod
    def data_fingerprint(data: Any) -> str:
        """
        生成通用数据指纹
        
        :param data: 任意数据
        :return: 指纹字符串
        """
        return generate_data_fingerprint(data)