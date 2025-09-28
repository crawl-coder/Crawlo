#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-20 10:00
# @Author  : crawl-coder
# @Desc    : 请求处理工具
"""
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from copy import deepcopy


def build_url(base_url: str, path: str = "", query_params: Optional[Dict[str, Any]] = None) -> str:
    """
    构建完整的URL
    
    :param base_url: 基础URL
    :param path: 路径
    :param query_params: 查询参数字典
    :return: 完整的URL
    """
    # 解析基础URL
    parsed = urlparse(base_url)
    
    # 合并路径
    if path:
        # 确保路径以/开头
        if not path.startswith('/'):
            path = '/' + path
        # 合并路径
        new_path = parsed.path.rstrip('/') + path
    else:
        new_path = parsed.path
    
    # 处理查询参数
    if query_params:
        # 解析现有查询参数
        existing_params = parse_qs(parsed.query)
        # 合并新参数
        for key, value in query_params.items():
            existing_params[key] = [str(value)]
        # 编码查询参数
        new_query = urlencode(existing_params, doseq=True)
    else:
        new_query = parsed.query
    
    # 构建新的URL
    new_parsed = parsed._replace(path=new_path, query=new_query)
    return urlunparse(new_parsed)


def add_query_params(url: str, params: Dict[str, Any]) -> str:
    """
    向URL添加查询参数
    
    :param url: 原始URL
    :param params: 要添加的参数字典
    :return: 添加参数后的URL
    """
    parsed = urlparse(url)
    # 解析现有查询参数
    existing_params = parse_qs(parsed.query)
    # 添加新参数
    for key, value in params.items():
        existing_params[key] = [str(value)]
    # 编码查询参数
    new_query = urlencode(existing_params, doseq=True)
    # 构建新的URL
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def merge_headers(base_headers: Dict[str, str], additional_headers: Dict[str, str]) -> Dict[str, str]:
    """
    合并请求头
    
    :param base_headers: 基础请求头
    :param additional_headers: 要添加的请求头
    :return: 合并后的请求头
    """
    merged = deepcopy(base_headers)
    merged.update(additional_headers)
    return merged