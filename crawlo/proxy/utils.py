#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-08-24 12:10
# @Author  :   crawl-coder
# @Desc    :   None
"""
from typing import List, Union, Dict, Any


def import_string(dotted_path: str) -> Any:
    """导入模块路径，如 'myapp.module.Klass'"""
    try:
        module_path, obj_name = dotted_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[obj_name])
        return getattr(module, obj_name)
    except Exception as e:
        raise ImportError(f"无法导入 {dotted_path}") from e


def ensure_list(data) -> list:
    """确保是列表"""
    if isinstance(data, str):
        return [data]
    if isinstance(data, (list, tuple)):
        return list(data)
    return []


def filter_valid_urls(items: List[Union[str, Dict]]) -> List[str]:
    """
    支持处理字符串 URL 或 dict 格式代理
    支持格式:
        - "http://ip:port"
        - {"http": "http://...", "https": "http://..."}
    """
    urls = set()
    for item in items:
        if isinstance(item, str):
            url = item.strip()
            if url and (url.startswith(('http://', 'https://', 'socks5://', 'socks4://'))):
                urls.add(url)
        elif isinstance(item, dict):
            # 提取 http 和 https 字段
            for scheme in ['http', 'https']:
                url = item.get(scheme, '').strip()
                if url and (url.startswith(('http://', 'https://', 'socks5://', 'socks4://'))):
                    urls.add(url)
    return list(urls)
