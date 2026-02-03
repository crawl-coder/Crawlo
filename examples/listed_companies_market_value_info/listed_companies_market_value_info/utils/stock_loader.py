#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
股票列表加载工具
从数据库表listed_stock_list中读取A股股票代码
"""
import pymysql
from crawlo.logging import get_logger

logger = get_logger(__name__)


def get_db_config():
    """
    获取数据库配置
    """
    # 动态导入以避免循环导入
    import importlib
    settings_module = importlib.import_module('listed_companies_market_value_info.settings')
    return {
        'host': settings_module.MYSQL_HOST,
        'port': settings_module.MYSQL_PORT,
        'user': settings_module.MYSQL_USER,
        'password': settings_module.MYSQL_PASSWORD,
        'database': settings_module.MYSQL_DB,
        'charset': 'utf8mb4'
    }


def load_a_stocks():
    """
    从数据库表listed_stock_list中读取A股股票代码
    
    Returns:
        list: A股股票代码列表，格式如['000001.SZ', '600000.SH']
    """
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 从listed_stock_list表中查询A股股票代码
        sql = "select stock_code, stock_name from listed_stock_list where stock_type in ('A股', '科创板', '创业板');"
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # 构建股票列表
        stocks = [(row[0], row[1]) for row in rows]
        
        cursor.close()
        conn.close()
        
        # print(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只A股股票代码")
        return stocks
        
    except Exception as e:
        logger.error(f"❌ 从listed_stock_list表加载股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


def load_a_stocks_market():
    """
    从数据库表listed_stock_list中读取A股股票代码

    Returns:
        list: A股股票代码列表，格式如['000001.SZ', '600000.SH']
    """
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()

        # 从listed_stock_list表中查询A股股票代码
        # sql = "select stock_code, stock_name from listed_stock_list where stock_type in ('A股', '科创板', '创业板');"
        sql = "select stock_code, stock_name from listed_stock_list where stock_type in ('A股', '科创板', '创业板') and stock_code not in (select stock_code from listed_companies_market_value_info where disclosure_date = Date(CURDATE())  group by stock_code);"

        cursor.execute(sql)
        rows = cursor.fetchall()

        # 构建股票列表
        stocks = [(row[0], row[1]) for row in rows]

        cursor.close()
        conn.close()

        logger.info(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只A股股票代码")
        return stocks

    except Exception as e:
        logger.error(f"❌ 从listed_stock_list表加载股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


def load_us_stocks():
    """
    从数据库表listed_stock_list中读取美股股票代码
    
    Returns:
        list: 美股股票代码列表，格式如['AAPL.O', 'MSFT.O']
    """
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 从listed_stock_list表中查询美股股票代码
        # sql = "select stock_code from listed_stock_list where stock_type in ('美股');"
        sql = "select stock_code from listed_stock_list where stock_type ='美股' and stock_code not in (select stock_code from us_stock_balance_sheet group by stock_code);"
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # 构建股票列表
        stocks = [row[0] for row in rows]
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只美股股票代码")
        return stocks
        
    except Exception as e:
        logger.error(f"❌ 从listed_stock_list表加载美股股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


def load_hk_stocks():
    """
    从数据库表listed_stock_list中读取港股股票代码
    
    Returns:
        list: 港股股票代码列表，格式如['00700.HK', '00981.HK']
    """
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 从listed_stock_list表中查询港股股票代码
        sql = "select stock_code from listed_stock_list where stock_type in ('港股');"
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # 构建股票列表
        stocks = [row[0] for row in rows]
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只港股股票代码")
        return stocks
        
    except Exception as e:
        logger.error(f"❌ 从listed_stock_list表加载港股股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


def load_nq_stocks(sql):
    """
    从数据库表listed_stock_list中读取新三板股票代码
    
    Returns:
        list: 新三板股票代码列表，格式如['830789.NQ', '830892.NQ']
    """
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 从listed_stock_list表中查询新三板股票代码
        # sql = "select stock_code,stock_name from listed_stock_list where stock_type in ('新三板') and stock_code not like '9%';"
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # 构建股票列表，包含(stock_code, stock_name)元组
        stocks = [(row[0], row[1]) for row in rows]
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只新三板股票代码")
        return stocks
        
    except Exception as e:
        logger.error(f"❌ 从listed_stock_list表加载新三板股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


def load_stocks_by_type(stock_type):
    """
    从数据库表listed_stock_list中读取指定类型的股票代码
    
    Args:
        stock_type (str or list): 股票类型，如'A股', '美股', '港股', '新三板' 或类型列表
    
    Returns:
        list: 股票代码列表
    """
    db_config = get_db_config()

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 处理输入参数
        if isinstance(stock_type, str):
            stock_types = [stock_type]
        else:
            stock_types = stock_type
        
        # 转义单引号以防止SQL注入
        escaped_types = [t.replace("'", "''") for t in stock_types]
        types_str = "','".join(escaped_types)
        
        # 从listed_stock_list表中查询指定类型的股票代码
        sql = f"select stock_code from listed_stock_list where stock_type in ('{types_str}');"
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # 构建股票列表
        stocks = [row[0] for row in rows]
        
        cursor.close()
        conn.close()
        
        logger.info(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只{','.join(stock_types)}股票代码")
        return stocks
        
    except Exception as e:
        logger.error(f"❌ 从listed_stock_list表加载{stock_type}股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


if __name__ == "__main__":
    stocks = load_a_stocks()
    print(f"加载的股票列表: {stocks[:10]}...")  # 只打印前10个作为示例