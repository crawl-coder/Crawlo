#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 文本清洗工具
"""
import html
import re
import unicodedata
from typing import List


class TextCleaner:
    """
    文本清洗工具类，提供各种文本清洗功能。
    特别适用于爬虫中处理网页内容的清洗需求。
    """

    @staticmethod
    def remove_html_tags(text: str) -> str:
        """
        移除HTML标签（含 script/style 块及注释）
        
        :param text: 包含HTML标签的文本
        :return: 移除HTML标签后的文本
        """
        if not isinstance(text, str):
            return str(text)
        
        # 移除 script/style 块及 HTML 注释
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        # 移除剩余标签
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    @staticmethod
    def decode_html_entities(text: str) -> str:
        """
        解码HTML实体字符
        
        :param text: 包含HTML实体字符的文本
        :return: 解码后的文本
        """
        if not isinstance(text, str):
            return str(text)
        
        return html.unescape(text)

    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """
        移除多余的空白字符（包括空格、制表符、换行符等）
        
        :param text: 文本
        :return: 清理后的文本
        """
        if not isinstance(text, str):
            return str(text)
        
        # 将多个连续的空白字符替换为单个空格
        clean_text = re.sub(r'\s+', ' ', text)
        return clean_text.strip()

    @staticmethod
    def remove_special_chars(text: str, chars: str = '') -> str:
        """
        移除特殊字符
        
        :param text: 文本
        :param chars: 要移除的特殊字符
        :return: 清理后的文本
        """
        if not isinstance(text, str):
            return str(text)
        
        # 移除常见的特殊字符（chars 参数经 re.escape 转义防注入）
        special_chars = r'[^\w\s\u4e00-\u9fff' + re.escape(chars) + r']'
        clean_text = re.sub(special_chars, '', text)
        return clean_text

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """
        标准化Unicode字符
        
        :param text: 文本
        :return: 标准化后的文本
        """
        if not isinstance(text, str):
            return str(text)
        
        return unicodedata.normalize('NFKC', text)

    @staticmethod
    def clean_text(text: str, 
                   remove_html: bool = True,
                   decode_entities: bool = True,
                   remove_whitespace: bool = True,
                   remove_special: bool = False,
                   normalize: bool = True) -> str:
        """
        综合文本清洗方法
        
        :param text: 原始文本
        :param remove_html: 是否移除HTML标签
        :param decode_entities: 是否解码HTML实体
        :param remove_whitespace: 是否移除多余空白字符
        :param remove_special: 是否移除特殊字符
        :param normalize: 是否标准化Unicode字符
        :return: 清洗后的文本
        """
        if not isinstance(text, str):
            text = str(text)
        
        if not text:
            return text
            
        # 按顺序进行清洗
        if remove_html:
            text = TextCleaner.remove_html_tags(text)
        
        if decode_entities:
            text = TextCleaner.decode_html_entities(text)
        
        if normalize:
            text = TextCleaner.normalize_unicode(text)
        
        if remove_whitespace:
            text = TextCleaner.remove_extra_whitespace(text)
        
        if remove_special:
            text = TextCleaner.remove_special_chars(text)
        
        return text

    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """
        从文本中提取数字
        
        :param text: 文本
        :return: 数字列表
        """
        if not isinstance(text, str):
            return []
        
        # 匹配整数和小数
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return numbers

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """
        从文本中提取邮箱地址
        
        :param text: 文本
        :return: 邮箱地址列表
        """
        if not isinstance(text, str):
            return []
        
        # 匹配邮箱地址
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        return emails

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """
        从文本中提取URL
        
        :param text: 文本
        :return: URL列表
        """
        if not isinstance(text, str):
            return []
        
        # 匹配URL
        urls = re.findall(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            text
        )
        return urls


    @staticmethod
    def extract_phones(text: str) -> List[str]:
        """
        从文本中提取手机号/座机号（中国）

        :param text: 文本
        :return: 号码列表
        """
        if not isinstance(text, str):
            return []
        patterns = [
            r'\b1[3-9]\d{9}\b',                 # 手机号
            r'\b0\d{2,3}[-\s]?\d{7,8}\b',       # 座机号(带区号)
            r'\b400[-\s]?\d{3}[-\s]?\d{4}\b',   # 400热线
        ]
        phones = []
        for p in patterns:
            phones.extend(re.findall(p, text))
        return phones

    @staticmethod
    def strip_control_chars(text: str, keep: str = '\t\n\r') -> str:
        """
        移除不可见控制字符（\x00-\x1f），保留指定的换行/制表符

        :param text: 文本
        :param keep: 保留的控制字符
        :return: 清理后的文本
        """
        if not isinstance(text, str):
            return str(text)
        return re.sub(rf'[^\x20-\x7e\u4e00-\u9fff{re.escape(keep)}]', '', text)

    @staticmethod
    def truncate(text: str, max_len: int = 255, ellipsis: str = '...') -> str:
        """
        截断文本到指定长度

        :param text: 文本
        :param max_len: 最大长度
        :param ellipsis: 截断标记
        :return: 截断后的文本
        """
        if not isinstance(text, str):
            text = str(text)
        if len(text) <= max_len:
            return text
        return text[:max_len - len(ellipsis)] + ellipsis

# =======================对外接口=======================

def remove_html_tags(text: str) -> str:
    """移除HTML标签"""
    return TextCleaner.remove_html_tags(text)


def decode_html_entities(text: str) -> str:
    """解码HTML实体字符"""
    return TextCleaner.decode_html_entities(text)


def remove_extra_whitespace(text: str) -> str:
    """移除多余的空白字符"""
    return TextCleaner.remove_extra_whitespace(text)


def remove_special_chars(text: str, chars: str = '') -> str:
    """移除特殊字符"""
    return TextCleaner.remove_special_chars(text, chars)


def normalize_unicode(text: str) -> str:
    """标准化Unicode字符"""
    return TextCleaner.normalize_unicode(text)


def clean_text(text: str, 
               remove_html: bool = True,
               decode_entities: bool = True,
               remove_whitespace: bool = True,
               remove_special: bool = False,
               normalize: bool = True) -> str:
    """综合文本清洗"""
    return TextCleaner.clean_text(text, remove_html, decode_entities, remove_whitespace, remove_special, normalize)


def extract_numbers(text: str) -> List[str]:
    """提取数字"""
    return TextCleaner.extract_numbers(text)


def extract_emails(text: str) -> List[str]:
    """提取邮箱地址"""
    return TextCleaner.extract_emails(text)


def extract_urls(text: str) -> List[str]:
    """提取URL"""
    return TextCleaner.extract_urls(text)


def extract_phones(text: str) -> List[str]:
    """提取手机号/座机号"""
    return TextCleaner.extract_phones(text)


def strip_control_chars(text: str, keep: str = '\t\n\r') -> str:
    """移除不可见控制字符"""
    return TextCleaner.strip_control_chars(text, keep)


def truncate(text: str, max_len: int = 255, ellipsis: str = '...') -> str:
    """截断文本到指定长度"""
    return TextCleaner.truncate(text, max_len, ellipsis)
