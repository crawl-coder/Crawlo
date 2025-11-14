#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
"""
MySQL 管道集成测试
验证 MYSQL_UPDATE_COLUMNS 配置在实际使用中是否解决了 MySQL 警告问题
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.db_helper import SQLBuilder


def test_complete_workflow():
    """测试完整的数据插入工作流程"""
    print("=== MySQL 管道集成测试 ===\n")
    
    # 模拟实际使用的配置
    table = "news_items"
    item_data = {
        'title': '新一代OLED屏下光谱颜色传感技术：解锁显示新密码，重塑视觉新体验',
        'publish_time': '2025-10-09 09:57',
        'url': 'https://ee.ofweek.com/2025-10/ART-8460-2806-30671544.html',
        'source': '',
        'content': '在全球智能手机市场竞争日趋白热化的当下，消费者对手机屏幕显示效果的要求愈发严苛...'
    }
    
    print("1. 测试单条插入 SQL 生成...")
    # 测试单条插入
    single_sql = SQLBuilder.make_insert(
        table=table,
        data=item_data,
        auto_update=False,  # 不使用 REPLACE INTO
        insert_ignore=False,  # 不使用 INSERT IGNORE
        update_columns=('title', 'publish_time')  # 冲突时更新指定列
    )
    
    print("生成的单条插入 SQL:")
    print(single_sql)
    print()
    
    # 验证语法正确性
    if "AS `excluded`" in single_sql and "`title`=`excluded`.`title`" in single_sql:
        print("✓ 单条插入正确使用了新的 MySQL 语法")
    else:
        print("✗ 单条插入语法不正确")
    
    print("\n2. 测试批量插入 SQL 生成...")
    # 测试批量插入
    batch_data = [item_data, item_data]  # 模拟重复数据
    batch_result = SQLBuilder.make_batch(
        table=table,
        datas=batch_data,
        auto_update=False,
        update_columns=('title', 'publish_time')
    )
    
    if batch_result:
        batch_sql, values_list = batch_result
        print("生成的批量插入 SQL:")
        print(batch_sql)
        print(f"参数值列表数量: {len(values_list)}")
        print()
        
        # 验证语法正确性
        if "AS `excluded`" in batch_sql and "`title`=`excluded`.`title`" in batch_sql:
            print("✓ 批量插入正确使用了新的 MySQL 语法")
        else:
            print("✗ 批量插入语法不正确")
    
    print("\n3. 测试不同配置组合...")
    
    # 测试仅使用 INSERT IGNORE
    ignore_sql = SQLBuilder.make_insert(
        table=table,
        data=item_data,
        auto_update=False,
        insert_ignore=True,
        update_columns=()  # 不指定更新列
    )
    
    print("INSERT IGNORE SQL:")
    print(ignore_sql)
    print()
    
    if "INSERT IGNORE" in ignore_sql and "AS `excluded`" not in ignore_sql:
        print("✓ INSERT IGNORE 模式正确")
    else:
        print("✗ INSERT IGNORE 模式不正确")
    
    # 测试使用 REPLACE INTO
    replace_sql = SQLBuilder.make_insert(
        table=table,
        data=item_data,
        auto_update=True,  # 使用 REPLACE INTO
        insert_ignore=False,
        update_columns=()  # 不指定更新列
    )
    
    print("REPLACE INTO SQL:")
    print(replace_sql)
    print()
    
    if "REPLACE INTO" in replace_sql and "AS `excluded`" not in replace_sql:
        print("✓ REPLACE INTO 模式正确")
    else:
        print("✗ REPLACE INTO 模式不正确")
    
    # 测试普通 INSERT
    normal_sql = SQLBuilder.make_insert(
        table=table,
        data=item_data,
        auto_update=False,
        insert_ignore=False,
        update_columns=()  # 不指定更新列
    )
    
    print("普通 INSERT SQL:")
    print(normal_sql)
    print()
    
    if "INSERT INTO" in normal_sql and "AS `excluded`" not in normal_sql:
        print("✓ 普通 INSERT 模式正确")
    else:
        print("✗ 普通 INSERT 模式不正确")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_complete_workflow()