#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 数据格式化工具
"""
import re
from typing import Any, Optional, Union
from decimal import Decimal, InvalidOperation


class DataFormatter:
    """
    数据格式化工具类，提供各种数据格式化功能。
    特别适用于爬虫中处理各种数据类型的格式化需求。
    """

    @staticmethod
    def format_number(value: Any, 
                      precision: int = 2, 
                      thousand_separator: bool = False) -> Optional[str]:
        """
        格式化数字
        
        :param value: 数字值
        :param precision: 小数点精度
        :param thousand_separator: 是否使用千位分隔符
        :return: 格式化后的数字字符串
        """
        if value is None:
            return None
            
        try:
            # 转换为Decimal以避免浮点数精度问题
            decimal_value = Decimal(str(value))
            
            if thousand_separator:
                # 使用千位分隔符
                formatted = f"{decimal_value:,.{precision}f}"
            else:
                # 不使用千位分隔符
                formatted = f"{decimal_value:.{precision}f}"
                
            return formatted
        except (ValueError, InvalidOperation):
            return None

    @staticmethod
    def format_currency(value: Any, 
                        currency_symbol: str = "¥", 
                        precision: int = 2) -> Optional[str]:
        """
        格式化货币
        
        :param value: 货币值
        :param currency_symbol: 货币符号
        :param precision: 小数点精度
        :return: 格式化后的货币字符串
        """
        formatted_number = DataFormatter.format_number(value, precision, thousand_separator=True)
        if formatted_number is None:
            return None
            
        return f"{currency_symbol}{formatted_number}"

    @staticmethod
    def format_percentage(value: Any, 
                          precision: int = 2, 
                          multiply_100: bool = True) -> Optional[str]:
        """
        格式化百分比
        
        :param value: 百分比值
        :param precision: 小数点精度
        :param multiply_100: 是否乘以100（如果原始值是小数）
        :return: 格式化后的百分比字符串
        """
        if value is None:
            return None
            
        try:
            decimal_value = Decimal(str(value))
            
            if multiply_100:
                decimal_value *= 100
                
            formatted = f"{decimal_value:.{precision}f}%"
            return formatted
        except (ValueError, InvalidOperation):
            return None

    @staticmethod
    def format_phone_number(phone: str, 
                            country_code: str = "+86", 
                            format_type: str = "international") -> Optional[str]:
        """
        格式化电话号码
        
        :param phone: 电话号码
        :param country_code: 国家代码
        :param format_type: 格式类型 ('international', 'domestic', 'plain')
        :return: 格式化后的电话号码
        """
        if not isinstance(phone, str):
            phone = str(phone)
            
        # 移除所有非数字字符
        digits = re.sub(r'\D', '', phone)
        
        if not digits:
            return None
            
        # 如果是11位中国手机号
        if len(digits) == 11 and digits.startswith('1'):
            if format_type == "international":
                return f"{country_code} {digits[:3]} {digits[3:7]} {digits[7:]}"
            elif format_type == "domestic":
                return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
            else:  # plain
                return digits
        else:
            # 其他情况简单处理
            if format_type == "international" and country_code:
                return f"{country_code} {digits}"
            else:
                return digits

    @staticmethod
    def format_chinese_id_card(id_card: str) -> Optional[str]:
        """
        格式化中国身份证号码（隐藏中间部分）
        
        :param id_card: 身份证号码
        :return: 格式化后的身份证号码
        """
        if not isinstance(id_card, str):
            id_card = str(id_card)
            
        # 移除空格
        id_card = id_card.replace(" ", "")
        
        if len(id_card) == 18:
            # 18位身份证号
            return f"{id_card[:6]}********{id_card[-4:]}"
        elif len(id_card) == 15:
            # 15位身份证号
            return f"{id_card[:6]}******{id_card[-3:]}"
        else:
            return None

    @staticmethod
    def capitalize_words(text: str, 
                         delimiter: str = " ", 
                         preserve_articles: bool = True) -> str:
        """
        单词首字母大写
        
        :param text: 文本
        :param delimiter: 单词分隔符
        :param preserve_articles: 是否保留冠词小写
        :return: 首字母大写后的文本
        """
        if not isinstance(text, str):
            return str(text)
            
        # 常见的冠词和介词
        articles = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        words = text.split(delimiter)
        capitalized_words = []
        
        for i, word in enumerate(words):
            if not word:
                capitalized_words.append(word)
                continue
                
            # 第一个单词和最后一个单词总是大写
            if i == 0 or i == len(words) - 1 or not preserve_articles or word.lower() not in articles:
                capitalized_words.append(word.capitalize())
            else:
                capitalized_words.append(word.lower())
                
        return delimiter.join(capitalized_words)


# =======================对外接口=======================

def format_number(value: Any, 
                  precision: int = 2, 
                  thousand_separator: bool = False) -> Optional[str]:
    """格式化数字"""
    return DataFormatter.format_number(value, precision, thousand_separator)


def format_currency(value: Any, 
                    currency_symbol: str = "¥", 
                    precision: int = 2) -> Optional[str]:
    """格式化货币"""
    return DataFormatter.format_currency(value, currency_symbol, precision)


def format_percentage(value: Any, 
                      precision: int = 2, 
                      multiply_100: bool = True) -> Optional[str]:
    """格式化百分比"""
    return DataFormatter.format_percentage(value, precision, multiply_100)


def format_phone_number(phone: str, 
                        country_code: str = "+86", 
                        format_type: str = "international") -> Optional[str]:
    """格式化电话号码"""
    return DataFormatter.format_phone_number(phone, country_code, format_type)


def format_chinese_id_card(id_card: str) -> Optional[str]:
    """格式化中国身份证号码"""
    return DataFormatter.format_chinese_id_card(id_card)


def capitalize_words(text: str, 
                     delimiter: str = " ", 
                     preserve_articles: bool = True) -> str:
    """单词首字母大写"""
    return DataFormatter.capitalize_words(text, delimiter, preserve_articles)