#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
"""
测试 MYSQL_UPDATE_COLUMNS 配置参数
验证是否解决了 MySQL 的 VALUES() 函数弃用警告问题
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.db_helper import SQLBuilder


def test_update_columns_syntax():
    """测试更新列语法是否正确"""
    print("测试 MYSQL_UPDATE_COLUMNS 配置参数...")
    
    # 测试数据
    table = "test_table"
    data = {
        "title": "测试标题",
        "publish_time": "2025-10-09 09:57",
        "url": "https://example.com/test",
        "content": "测试内容"
    }
    
    # 测试 MYSQL_UPDATE_COLUMNS 配置
    update_columns = ('title', 'publish_time')
    
    # 生成 SQL 语句
    sql = SQLBuilder.make_insert(
        table=table,
        data=data,
        auto_update=False,
        update_columns=update_columns,
        insert_ignore=False
    )
    
    print("生成的 SQL 语句:")
    print(sql)
    print()
    
    # 验证是否使用了正确的语法（不包含 VALUES() 函数作为函数调用）
    if "AS `excluded`" in sql and "ON DUPLICATE KEY UPDATE" in sql:
        print("✓ 正确使用了新的 MySQL 语法: INSERT ... VALUES (...) AS excluded ...")
        
        # 检查更新子句是否正确（不使用 VALUES() 函数）
        if "`title`=`excluded`.`title`" in sql and "`publish_time`=`excluded`.`publish_time`" in sql:
            if "VALUES(`title`)" not in sql and "VALUES(`publish_time`)" not in sql:
                print("✓ 更新子句正确使用了 excluded 别名，未使用 VALUES() 函数")
            else:
                print("✗ 更新子句错误地使用了 VALUES() 函数")
        else:
            print("✗ 更新子句语法不正确")
    else:
        print("✗ 未正确使用新的 MySQL 语法")
        
    # 测试批量插入
    print("\n测试批量插入...")
    datas = [data, data]  # 两条相同的数据用于测试
    
    batch_result = SQLBuilder.make_batch(
        table=table,
        datas=datas,
        auto_update=False,
        update_columns=update_columns
    )
    
    if batch_result:
        batch_sql, values_list = batch_result
        print("生成的批量 SQL 语句:")
        print(batch_sql)
        print()
        
        # 验证批量插入语法
        if "VALUES (%s)" in batch_sql and "AS `excluded`" in batch_sql and "ON DUPLICATE KEY UPDATE" in batch_sql:
            print("✓ 批量插入正确使用了新的 MySQL 语法")
            
            # 检查更新子句是否正确（不使用 VALUES() 函数）
            if "`title`=`excluded`.`title`" in batch_sql and "`publish_time`=`excluded`.`publish_time`" in batch_sql:
                if "VALUES(`title`)" not in batch_sql and "VALUES(`publish_time`)" not in batch_sql:
                    print("✓ 批量插入更新子句正确使用了 excluded 别名，未使用 VALUES() 函数")
                else:
                    print("✗ 批量插入更新子句错误地使用了 VALUES() 函数")
            else:
                print("✗ 批量插入更新子句语法不正确")
        else:
            print("✗ 批量插入未正确使用新的 MySQL 语法")


if __name__ == "__main__":
    test_update_columns_syntax()