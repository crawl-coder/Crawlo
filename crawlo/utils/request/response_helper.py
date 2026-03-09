#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
响应处理工具模块
==================
提供用于处理HTTP响应的辅助函数，包括Cookie处理和正则表达式操作。

该模块包含以下主要函数：
- parse_cookies: 从响应头中解析Cookies
- regex_search: 在文本上执行正则表达式搜索
- regex_findall: 在文本上执行正则表达式查找
- get_header_value: 从响应头中获取值，处理大小写不敏感的情况
"""

import re
from typing import Dict, List, Any, Optional, Union
from http.cookies import SimpleCookie


def parse_cookies(cookie_header: str) -> Dict[str, str]:
    """
    从响应头中解析并返回Cookies
    
    :param cookie_header: Set-Cookie头部的值
    :return: 解析后的Cookies字典
    """
    if isinstance(cookie_header, list):
        cookie_header = ", ".join(cookie_header)
    
    if not cookie_header:
        return {}
        
    cookies = SimpleCookie()
    try:
        cookies.load(cookie_header)
        return {key: morsel.value for key, morsel in cookies.items()}
    except Exception:
        # 如果解析失败，返回空字典
        return {}


def regex_search(pattern: str, text: str, flags: int = re.DOTALL) -> Optional[re.Match]:
    """
    在文本上执行正则表达式搜索
    
    :param pattern: 正则表达式模式
    :param text: 要搜索的文本
    :param flags: 正则表达式标志
    :return: 匹配对象或None
    """
    if not isinstance(pattern, str):
        raise TypeError("Pattern must be a string")
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    return re.search(pattern, text, flags=flags)


def regex_findall(pattern: str, text: str, flags: int = re.DOTALL) -> List[Any]:
    """
    在文本上执行正则表达式查找
    
    :param pattern: 正则表达式模式
    :param text: 要搜索的文本
    :param flags: 正则表达式标志
    :return: 匹配结果列表
    """
    if not isinstance(pattern, str):
        raise TypeError("Pattern must be a string")
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    return re.findall(pattern, text, flags=flags)


def get_header_value(headers: Dict[str, Any], header_name: str, default: Any = None) -> Any:
    """
    从响应头中获取值，处理大小写不敏感的情况
    
    :param headers: 响应头字典
    :param header_name: 头部名称
    :param default: 默认值
    :return: 头部值或默认值
    """
    if not headers or not header_name:
        return default
        
    # 首先尝试直接匹配
    if header_name in headers:
        return headers[header_name]
        
    # 尝试小写匹配
    lower_header = header_name.lower()
    if lower_header in headers:
        return headers[lower_header]
        
    # 尝试首字母大写匹配
    capitalized_header = header_name.capitalize()
    if capitalized_header in headers:
        return headers[capitalized_header]
        
    # 尝试标题格式匹配
    title_header = header_name.title()
    if title_header in headers:
        return headers[title_header]
        
    return default


__all__ = [
    "parse_cookies",
    "regex_search",
    "regex_findall",
    "get_header_value"
]