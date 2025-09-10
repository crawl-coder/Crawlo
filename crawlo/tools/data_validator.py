#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 数据验证工具
"""

import re
from typing import Any, Union, Dict, List
from datetime import datetime
from urllib.parse import urlparse


class DataValidator:
    """数据验证工具类"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        验证邮箱地址格式
        
        Args:
            email (str): 邮箱地址
            
        Returns:
            bool: 验证结果
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone(phone: str, country_code: str = "CN") -> bool:
        """
        验证电话号码格式
        
        Args:
            phone (str): 电话号码
            country_code (str): 国家代码，默认为"CN"
            
        Returns:
            bool: 验证结果
        """
        if country_code == "CN":
            # 中国手机号码格式
            pattern = r'^1[3-9]\d{9}$'
            return bool(re.match(pattern, phone))
        else:
            # 通用格式，只检查是否全为数字且长度在7-15之间
            pattern = r'^\d{7,15}$'
            return bool(re.match(pattern, phone))

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url (str): URL地址
            
        Returns:
            bool: 验证结果
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def validate_chinese_id_card(id_card: str) -> bool:
        """
        验证中国身份证号码格式
        
        Args:
            id_card (str): 身份证号码
            
        Returns:
            bool: 验证结果
        """
        # 18位身份证号码格式
        pattern = r'^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$'
        return bool(re.match(pattern, id_card))

    @staticmethod
    def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
        """
        验证日期格式
        
        Args:
            date_str (str): 日期字符串
            date_format (str): 日期格式，默认为"%Y-%m-%d"
            
        Returns:
            bool: 验证结果
        """
        try:
            datetime.strptime(date_str, date_format)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_number_range(value: Union[int, float], min_val: Union[int, float], 
                             max_val: Union[int, float]) -> bool:
        """
        验证数值是否在指定范围内
        
        Args:
            value (Union[int, float]): 要验证的数值
            min_val (Union[int, float]): 最小值
            max_val (Union[int, float]): 最大值
            
        Returns:
            bool: 验证结果
        """
        return min_val <= value <= max_val

    @staticmethod
    def check_data_integrity(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        检查数据完整性，确保关键字段不为空
        
        Args:
            data (Dict[str, Any]): 要检查的数据
            required_fields (List[str]): 必需字段列表
            
        Returns:
            Dict[str, Any]: 检查结果，包含缺失字段和空值字段
        """
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
            elif data[field] is None or data[field] == "":
                empty_fields.append(field)
                
        return {
            "is_valid": len(missing_fields) == 0 and len(empty_fields) == 0,
            "missing_fields": missing_fields,
            "empty_fields": empty_fields
        }


# 便捷函数
def validate_email(email: str) -> bool:
    """验证邮箱地址格式"""
    return DataValidator.validate_email(email)


def validate_phone(phone: str, country_code: str = "CN") -> bool:
    """验证电话号码格式"""
    return DataValidator.validate_phone(phone, country_code)


def validate_url(url: str) -> bool:
    """验证URL格式"""
    return DataValidator.validate_url(url)


def validate_chinese_id_card(id_card: str) -> bool:
    """验证中国身份证号码格式"""
    return DataValidator.validate_chinese_id_card(id_card)


def validate_date(date_str: str, date_format: str = "%Y-%m-%d") -> bool:
    """验证日期格式"""
    return DataValidator.validate_date(date_str, date_format)


def validate_number_range(value: Union[int, float], min_val: Union[int, float], 
                         max_val: Union[int, float]) -> bool:
    """验证数值是否在指定范围内"""
    return DataValidator.validate_number_range(value, min_val, max_val)


def check_data_integrity(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """检查数据完整性"""
    return DataValidator.check_data_integrity(data, required_fields)