#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
高管变动数据爬虫工具函数
"""
import hashlib
import time
from datetime import datetime
from urllib.parse import urlencode


def generate_pmid_executive(stock_code, person_name):
    """
    生成高管信息 PMID（业务主键）
    
    Args:
        stock_code: 股票代码（必须带后缀，如 600285.SH, 300758.SZ）
        person_name: 高管姓名
    
    Returns:
        str: 32位 MD5 哈希值
    
    Note:
        PMID 格式：股票代码（带后缀）+ 姓名，无分隔符
        例如：'300758.SZ徐惠祥' -> MD5 -> 'd97687b835510f3f94343a9fea638752'
    """
    # 确保股票代码带后缀
    if '.' not in stock_code:
        raise ValueError(f"股票代码必须包含交易所后缀（如 .SH, .SZ），当前值: {stock_code}")
    
    pmid_str = f"{stock_code}{person_name}"
    return hashlib.md5(pmid_str.encode()).hexdigest()


def generate_pmid_changes(person_name, change_date, dse_person_name, change_shares, shares_after_change):
    """
    生成 PMID（业务主键）- 高管变动数据
    
    Args:
        person_name: 变动人姓名
        change_date: 变动日期
        dse_person_name: 董监高人员姓名
        change_shares: 变动股数
        shares_after_change: 变动后持股数
    
    Returns:
        str: 32位 MD5 哈希值
    """
    pmid_str = f"{person_name}|{change_date}|{dse_person_name}|{change_shares}|{shares_after_change}"
    return hashlib.md5(pmid_str.encode()).hexdigest()


def parse_stock_code(stock_with_suffix):
    """
    从带后缀的股票代码中提取纯数字代码
    
    Args:
        stock_with_suffix: 带后缀的股票代码，如 '600285.SH'
    
    Returns:
        str: 纯数字代码，如 '600285'
    """
    return stock_with_suffix.split('.')[0]


def build_api_params(stock_code, page=1, page_size=20):
    """
    构建 API 请求参数 - 高管变动
    
    Args:
        stock_code: 纯数字股票代码
        page: 页码，默认1
        page_size: 每页数量，默认20
    
    Returns:
        dict: API 请求参数
    """
    return {
        "st": "CHANGE_DATE,SECURITY_CODE,PERSON_NAME",
        "sr": "-1,1,1",
        "code": stock_code,
        "name": "",
        "p": str(page),
        "ps": str(page_size)
    }


def build_base_params(stock_code, page_size=20):
    """
    构建基础参数（用于翻页时复制）- 高管变动
    
    Args:
        stock_code: 纯数字股票代码
        page_size: 每页数量，默认20
    
    Returns:
        dict: 基础参数（不包含页码）
    """
    return {
        "st": "CHANGE_DATE,SECURITY_CODE,PERSON_NAME",
        "sr": "-1,1,1",
        "code": stock_code,
        "name": "",
        "ps": str(page_size)
    }


def get_v_params(params):
    """
    生成东方财富 API 的 v 参数（签名）
    
    Args:
        params: 请求参数字典
    
    Returns:
        str: v 参数值
    """
    # 简单的时间戳 + 随机数实现
    timestamp = str(int(time.time() * 1000))
    return timestamp


def parse_tenure_dates(incumbent_time):
    """
    解析任职时间字符串，提取开始和结束日期
    
    Args:
        incumbent_time: 任职时间字符串，如 "2020-01-01 ~ 2023-12-31" 或 "2020-01-01 至今"
    
    Returns:
        dict: {'tenure_start_date': str, 'tenure_end_date': str or None}
    """
    result = {
        'tenure_start_date': None,
        'tenure_end_date': None
    }
    
    if not incumbent_time:
        return result
    
    try:
        # 清理空格
        incumbent_time = incumbent_time.strip()
        
        # 处理 "至今" 的情况
        if '至今' in incumbent_time:
            parts = incumbent_time.replace('至今', '').strip()
            if '~' in parts:
                start_date = parts.split('~')[0].strip()
            else:
                start_date = parts
            
            result['tenure_start_date'] = start_date if start_date else None
            result['tenure_end_date'] = None  # 至今表示仍在任职
            return result
        
        # 处理有结束日期的情况
        if '~' in incumbent_time:
            parts = incumbent_time.split('~')
            start_date = parts[0].strip() if len(parts) > 0 else None
            end_date = parts[1].strip() if len(parts) > 1 else None
            
            result['tenure_start_date'] = start_date
            result['tenure_end_date'] = end_date
            return result
        
        # 单个日期
        result['tenure_start_date'] = incumbent_time
        return result
        
    except Exception as e:
        # 解析失败，返回原始值
        result['tenure_start_date'] = incumbent_time
        return result
