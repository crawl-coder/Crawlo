#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
股票列表加载工具
从codes.txt文件读取主板股票代码
"""

import os
from pathlib import Path


def load_a_stocks():
    """
    从codes.txt文件读取主板股票代码
    
    Returns:
        list: A股主板股票代码列表，格式如['000001.SZ', '600000.SH']
    """
    try:
        # 获取codes.txt文件路径
        codes_file_path = Path(__file__).parent.parent / "data" / "codes.txt"
        
        if not codes_file_path.exists():
            print(f"❌ 文件不存在: {codes_file_path}")
            return []
        
        # 读取codes.txt文件中的所有股票代码
        with open(codes_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 解析股票代码并添加后缀
        stocks = []
        for line in lines:
            code = line.strip()
            if code and code.isdigit():  # 确保是纯数字代码
                # 根据股票代码的前缀判断交易所并添加后缀
                exchange_suffix = get_exchange_suffix(code)
                
                # 只添加主板股票
                if is_main_board(code):
                    stocks.append(f"{code}.{exchange_suffix}")
        
        print(f"✅ 成功从codes.txt文件加载 {len(stocks)} 只A股主板股票代码")
        return stocks
        
    except Exception as e:
        print(f"❌ 从codes.txt文件加载股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


def get_exchange_suffix(code):
    """
    根据股票代码获取交易所后缀
    
    Args:
        code (str): 股票代码
        
    Returns:
        str: 交易所后缀 ('SZ' 或 'SH')
    """
    if code.startswith(('000', '001', '002', '003', '300')):
        return 'SZ'  # 深圳证券交易所
    elif code.startswith(('600', '601', '603', '605', '688')):
        return 'SH'  # 上海证券交易所
    else:
        # 默认规则：以0、2、3开头的为深圳，以6开头的为上海
        if code.startswith(('0', '2', '3')):
            return 'SZ'
        elif code.startswith('6'):
            return 'SH'
        else:
            # 对于其他未知的代码，可以根据常见规则判断
            return 'SZ'  # 默认深圳


def is_main_board(code):
    """
    判断是否为主板股票
    
    Args:
        code (str): 股票代码
        
    Returns:
        bool: 是否为主板股票
    """
    # 主板股票包括：
    # 深圳主板：000xxx, 001xxx, 002xxx, 003xxx
    # 上海主板：600xxx, 601xxx, 603xxx, 605xxx
    # 注意：300xxx 是创业板，688xxx 是科创板，不属于主板
    
    sz_main_board = code.startswith(('000', '001', '002', '003'))
    sh_main_board = code.startswith(('600', '601', '603', '605'))
    
    return sz_main_board or sh_main_board


if __name__ == "__main__":
    stocks = load_a_stocks()
    print(f"加载的主板股票列表: {stocks[:10]}...")  # 只打印前10个作为示例
    print(f"总共有 {len(stocks)} 只主板股票")
    
    # 打印一些统计信息
    sz_stocks = [s for s in stocks if s.endswith('.SZ')]
    sh_stocks = [s for s in stocks if s.endswith('.SH')]
    
    print(f"深圳主板股票数量: {len(sz_stocks)}")
    print(f"上海主板股票数量: {len(sh_stocks)}")