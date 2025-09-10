#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 编码转换工具
"""
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False
from typing import Optional, Union


class EncodingConverter:
    """
    编码转换工具类，提供各种编码转换功能。
    特别适用于爬虫中处理不同编码的网页内容。
    """

    @staticmethod
    def detect_encoding(data: Union[str, bytes]) -> Optional[str]:
        """
        检测数据编码
        
        :param data: 数据（字符串或字节）
        :return: 检测到的编码
        """
        if isinstance(data, str):
            # 如果是字符串，直接返回
            return 'utf-8'
        
        if not isinstance(data, bytes):
            return None
            
        if HAS_CHARDET:
            try:
                # 使用chardet检测编码
                result = chardet.detect(data)
                return result['encoding']
            except Exception:
                return None
        else:
            # 如果没有chardet，返回None
            return None

    @staticmethod
    def to_utf8(data: Union[str, bytes], source_encoding: Optional[str] = None) -> Optional[str]:
        """
        转换为UTF-8编码的字符串
        
        :param data: 数据（字符串或字节）
        :param source_encoding: 源编码（如果为None则自动检测）
        :return: UTF-8编码的字符串
        """
        if isinstance(data, str):
            # 如果已经是字符串，假设它已经是UTF-8
            return data
            
        if not isinstance(data, bytes):
            return None
            
        try:
            if source_encoding is None:
                # 自动检测编码
                source_encoding = EncodingConverter.detect_encoding(data)
                if source_encoding is None:
                    # 如果检测失败，尝试常见编码
                    for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                        try:
                            decoded = data.decode(encoding)
                            return decoded
                        except UnicodeDecodeError:
                            continue
                    return None
            else:
                # 使用指定编码
                return data.decode(source_encoding)
                
            # 使用检测到的编码解码
            return data.decode(source_encoding)
        except Exception:
            return None

    @staticmethod
    def convert_encoding(data: Union[str, bytes], 
                        source_encoding: Optional[str] = None, 
                        target_encoding: str = 'utf-8') -> Optional[bytes]:
        """
        编码转换
        
        :param data: 数据（字符串或字节）
        :param source_encoding: 源编码（如果为None则自动检测）
        :param target_encoding: 目标编码
        :return: 转换后的字节数据
        """
        # 先转换为UTF-8字符串
        utf8_str = EncodingConverter.to_utf8(data, source_encoding)
        if utf8_str is None:
            return None
            
        try:
            # 再转换为目标编码
            return utf8_str.encode(target_encoding)
        except Exception:
            return None


# =======================对外接口=======================

def detect_encoding(data: Union[str, bytes]) -> Optional[str]:
    """检测数据编码"""
    return EncodingConverter.detect_encoding(data)


def to_utf8(data: Union[str, bytes], source_encoding: Optional[str] = None) -> Optional[str]:
    """转换为UTF-8编码的字符串"""
    return EncodingConverter.to_utf8(data, source_encoding)


def convert_encoding(data: Union[str, bytes], 
                    source_encoding: Optional[str] = None, 
                    target_encoding: str = 'utf-8') -> Optional[bytes]:
    """编码转换"""
    return EncodingConverter.convert_encoding(data, source_encoding, target_encoding)