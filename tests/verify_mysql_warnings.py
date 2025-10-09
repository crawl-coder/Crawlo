# -*- coding: utf-8 -*-
"""
验证 MySQL 警告是否已解决
通过模拟实际运行环境来检查
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.db_helper import SQLBuilder
from crawlo.pipelines.mysql_pipeline import BaseMySQLPipeline, AsyncmyMySQLPipeline, AiomysqlMySQLPipeline


def verify_mysql_syntax():
    """验证 MySQL 语法是否正确，不会产生警告"""
    print("=== 验证 MySQL 语法是否正确 ===\n")
    
    # 模拟实际使用的数据
    test_data = {
        'title': '新一代OLED屏下光谱颜色传感技术：解锁显示新密码，重塑视觉新体验',
        'publish_time': '2025-10-09 09:57',
        'url': 'https://ee.ofweek.com/2025-10/ART-8460-2806-30671544.html',
        'source': '',
        'content': '在全球智能手机市场竞争日趋白热化的当下，消费者对手机屏幕显示效果的要求愈发严苛...'
    }
    
    # 模拟 ofweek_standalone 项目的配置
    update_columns = ('title', 'publish_time')
    
    print("1. 检查 SQLBuilder 生成的语法...")
    sql = SQLBuilder.make_insert(
        table="news_items",
        data=test_data,
        auto_update=False,
        update_columns=update_columns,
        insert_ignore=False
    )
    
    print("生成的 SQL:")
    print(sql[:200] + "..." if len(sql) > 200 else sql)
    print()
    
    # 检查是否包含弃用的 VALUES() 函数用法
    if "VALUES(`title`)" in sql or "VALUES(`publish_time`)" in sql:
        print("✗ 发现弃用的 VALUES() 函数用法，会产生警告")
        return False
    else:
        print("✓ 未发现弃用的 VALUES() 函数用法")
    
    if "AS `excluded`" in sql and "ON DUPLICATE KEY UPDATE" in sql:
        print("✓ 正确使用了新的 MySQL 语法")
    else:
        print("✗ 未正确使用新的 MySQL 语法")
        return False
    
    # 检查更新子句
    if "`title`=`excluded`.`title`" in sql and "`publish_time`=`excluded`.`publish_time`" in sql:
        print("✓ 更新子句正确使用了 excluded 别名")
    else:
        print("✗ 更新子句语法不正确")
        return False
    
    print("\n2. 检查批量插入语法...")
    batch_result = SQLBuilder.make_batch(
        table="news_items",
        datas=[test_data, test_data],
        auto_update=False,
        update_columns=update_columns
    )
    
    if batch_result:
        batch_sql, _ = batch_result
        print("生成的批量 SQL:")
        print(batch_sql[:200] + "..." if len(batch_sql) > 200 else batch_sql)
        print()
        
        # 检查批量插入语法
        if "VALUES(`title`)" in batch_sql or "VALUES(`publish_time`)" in batch_sql:
            print("✗ 批量插入中发现弃用的 VALUES() 函数用法，会产生警告")
            return False
        else:
            print("✓ 批量插入未发现弃用的 VALUES() 函数用法")
        
        if "AS `excluded`" in batch_sql and "ON DUPLICATE KEY UPDATE" in batch_sql:
            print("✓ 批量插入正确使用了新的 MySQL 语法")
        else:
            print("✗ 批量插入未正确使用新的 MySQL 语法")
            return False
        
        # 检查批量更新子句
        if "`title`=`excluded`.`title`" in batch_sql and "`publish_time`=`excluded`.`publish_time`" in batch_sql:
            print("✓ 批量插入更新子句正确使用了 excluded 别名")
        else:
            print("✗ 批量插入更新子句语法不正确")
            return False
    
    print("\n=== 验证完成 ===")
    print("✓ 所有语法检查通过，应该不会再出现 MySQL 的 VALUES() 函数弃用警告")
    return True


if __name__ == "__main__":
    success = verify_mysql_syntax()
    if success:
        print("\n🎉 MySQL 语法问题已解决！")
    else:
        print("\n❌ 仍存在 MySQL 语法问题需要修复")