#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
编码工具模块
==================
提供用于处理HTTP响应编码检测的辅助函数，作为w3lib库的替代实现。

该模块包含以下主要函数：
- html_body_declared_encoding: 从HTML meta标签中检测编码声明
- http_content_type_encoding: 从HTTP Content-Type头部检测编码
- read_bom: 检测字节顺序标记(BOM)
- resolve_encoding: 解析编码名称
- html_to_unicode: 将HTML内容转换为Unicode字符串
"""

import re
from typing import Optional, Tuple, Callable


def html_body_declared_encoding(html_body_str: bytes) -> Optional[str]:
    """
    HTML meta 标签声明编码检测的替代实现
    
    :param html_body_str: HTML内容字节串
    :return: 检测到的编码或None
    """
    if isinstance(html_body_str, str):
        html_body_str = html_body_str.encode('utf-8')
    
    # 只检查前4KB内容
    html_start = html_body_str[:4096]
    
    try:
        # 尝试解码为ASCII（忽略错误）
        html_text = html_start.decode('ascii', errors='ignore')
        
        # 查找 <meta charset="xxx"> 或 <meta http-equiv="Content-Type" content="...charset=xxx">
        # <meta charset="utf-8">
        charset_match = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', html_text, re.I)
        if charset_match:
            return charset_match.group(1).lower()

        # <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        content_match = re.search(r'<meta[^>]+content=["\'][^"\'>]*charset=([\w-]+)', html_text, re.I)
        if content_match:
            return content_match.group(1).lower()
            
    except Exception:
        pass
        
    return None


def http_content_type_encoding(content_type: str) -> Optional[str]:
    """
    HTTP Content-Type 头部编码检测的替代实现
    
    :param content_type: Content-Type头部值
    :return: 检测到的编码或None
    """
    if not content_type:
        return None
        
    charset_match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if charset_match:
        return charset_match.group(1).lower()
        
    return None


def read_bom(data: bytes) -> Tuple[Optional[str], bytes]:
    """
    检测字节顺序标记(BOM)的替代实现
    
    :param data: 字节数据
    :return: (编码, 去除BOM后的数据)
    """
    if data.startswith(b'\xff\xfe'):
        return 'utf-16-le', data[2:]
    elif data.startswith(b'\xfe\xff'):
        return 'utf-16-be', data[2:]
    elif data.startswith(b'\xff\xfe\x00\x00'):
        return 'utf-32-le', data[4:]
    elif data.startswith(b'\x00\x00\xfe\xff'):
        return 'utf-32-be', data[4:]
    elif data.startswith(b'\xef\xbb\xbf'):
        return 'utf-8', data[3:]
    else:
        return None, data


def resolve_encoding(encoding: str) -> Optional[str]:
    """
    解析编码名称的替代实现
    
    :param encoding: 编码名称
    :return: 标准化后的编码名称或None
    """
    if not encoding:
        return None
        
    # 常见编码别名映射
    encoding_aliases = {
        'utf8': 'utf-8',
        'utf-8-sig': 'utf-8',
        'ucs2': 'utf-16',
        'ucs-2': 'utf-16',
        'ucs4': 'utf-32',
        'ucs-4': 'utf-32',
        'iso-8859-1': 'latin1',
        'iso-latin-1': 'latin1',
        'cp936': 'gbk',
        'ms936': 'gbk',
        'gb2312': 'gbk',
        'gb_2312': 'gbk',
        'gb_2312-80': 'gbk',
        'csgb2312': 'gbk',
        'big5-hkscs': 'big5',
        'shift_jis': 'shift-jis',
        'sjis': 'shift-jis',
        'windows-31j': 'shift-jis',
        'cskoi8r': 'koi8-r',
        'koi8_r': 'koi8-r',
    }
    
    encoding = encoding.lower().strip()
    return encoding_aliases.get(encoding, encoding)


def html_to_unicode(content_type_header: str, 
                   html_body_str: bytes,
                   auto_detect_fun: Optional[Callable[[bytes], Optional[str]]] = None,
                   default_encoding: str = 'utf-8') -> Tuple[str, str]:
    """
    将HTML内容转换为Unicode字符串的替代实现
    
    :param content_type_header: Content-Type头部
    :param html_body_str: HTML内容字节串
    :param auto_detect_fun: 自动检测编码的回调函数
    :param default_encoding: 默认编码
    :return: (编码, Unicode字符串)
    """
    # 1. 检测BOM
    bom_enc, html_body_str = read_bom(html_body_str)
    if bom_enc:
        try:
            return bom_enc, html_body_str.decode(bom_enc)
        except (UnicodeDecodeError, LookupError):
            pass
    
    # 2. 从Content-Type头部获取编码
    header_enc = http_content_type_encoding(content_type_header)
    if header_enc:
        try:
            return header_enc, html_body_str.decode(header_enc)
        except (UnicodeDecodeError, LookupError):
            pass
    
    # 3. 从HTML meta标签获取编码
    meta_enc = html_body_declared_encoding(html_body_str)
    if meta_enc:
        try:
            return meta_enc, html_body_str.decode(meta_enc)
        except (UnicodeDecodeError, LookupError):
            pass
    
    # 4. 使用自动检测函数
    if auto_detect_fun:
        auto_enc = auto_detect_fun(html_body_str)
        if auto_enc:
            try:
                return auto_enc, html_body_str.decode(auto_enc)
            except (UnicodeDecodeError, LookupError):
                pass
    
    # 5. 使用默认编码
    try:
        return default_encoding, html_body_str.decode(default_encoding)
    except (UnicodeDecodeError, LookupError):
        # 最后尝试使用错误容忍的方式解码
        return 'utf-8', html_body_str.decode('utf-8', errors='replace')


__all__ = [
    "html_body_declared_encoding",
    "http_content_type_encoding",
    "read_bom",
    "resolve_encoding",
    "html_to_unicode"
]