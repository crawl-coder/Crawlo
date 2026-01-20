#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
股票列表加载工具
从数据库表listed_stock_list中读取A股股票代码
"""

import pymysql
from eastmoney_fin_report_crawler.settings import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


def load_a_stocks():
    """
    从数据库表listed_stock_list中读取A股股票代码
    
    Returns:
        list: A股股票代码列表，格式如['000001.SZ', '600000.SH']
    """
    db_config = {
        'host': MYSQL_HOST,
        'port': MYSQL_PORT,
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'database': MYSQL_DB,
        'charset': 'utf8mb4'
    }

    try:
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 从listed_stock_list表中查询A股股票代码
        sql = "select stock_code from listed_stock_list where stock_type in ('A股', '科创板', '创业板');"
        cursor.execute(sql)
        # cursor.execute(
        #     "SELECT stock_code FROM listed_stock_list WHERE stock_type = %s",
        #     ('A股',)
        # )
        rows = cursor.fetchall()
        
        # 构建股票列表
        stocks = [row[0] for row in rows]
        
        cursor.close()
        conn.close()
        
        print(f"✅ 成功从listed_stock_list表加载 {len(stocks)} 只A股股票代码")
        return stocks
        
    except Exception as e:
        print(f"❌ 从listed_stock_list表加载股票数据失败: {e}")
        # 如果加载失败，返回空列表让调用方决定如何处理
        return []


if __name__ == "__main__":
    stocks = load_a_stocks()
    print(f"加载的股票列表: {stocks[:10]}...")  # 只打印前10个作为示例