#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
# @Time    :    2025-09-24 15:06
# @Author  :   crawl-coder
# @Desc    :   None
"""
import pymysql

from eastmoney_fin_report_crawler.settings import MYSQL_HOST, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD, MYSQL_PORT

# === 请按实际修改数据库配置 ===
DB_CONFIG = {
    'host': MYSQL_HOST,
    'port': MYSQL_PORT,
    'user': MYSQL_USER,
    'password': MYSQL_PASSWORD,
    'database': MYSQL_DB,
    'charset': 'utf8mb4'
}


def main():
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 查询 code 和 code_n 字段
    cursor.execute("SELECT `code`, `code_n` FROM `a_stock_info`")
    rows = cursor.fetchall()

    # 打印结果（或可写入文件）
    result = []
    for code, code_n in rows:
        code_str = f"{code}.{code_n}"
        result.append(code_str)
        print(code_str)

    cursor.close()
    conn.close()
    print(f"\n✅ 共读取 {len(rows)} 条记录")
    print(result)


if __name__ == "__main__":
    main()
