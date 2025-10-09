# -*- coding: utf-8 -*-
"""
模拟 MySQL ON DUPLICATE KEY UPDATE 行为测试
演示不同情况下的影响行数
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.db_helper import SQLBuilder


def simulate_mysql_scenarios():
    """模拟不同的 MySQL 场景"""
    print("=== MySQL 场景模拟测试 ===\n")
    
    table = "news_items"
    
    # 场景1: 新记录插入
    print("场景1: 插入新记录")
    new_data = {
        'title': '新文章标题',
        'publish_time': '2025-10-09 10:00',
        'url': 'https://example.com/new-article',
        'source': '新来源',
        'content': '新文章内容'
    }
    
    sql1 = SQLBuilder.make_insert(
        table=table,
        data=new_data,
        auto_update=False,
        update_columns=('title', 'publish_time'),
        insert_ignore=False
    )
    
    print(f"SQL: {sql1[:100]}...")
    print("预期行为: 正常插入，影响行数 = 1")
    print()
    
    # 场景2: 冲突但字段值相同
    print("场景2: 主键冲突，更新字段值相同")
    duplicate_data = {
        'title': '已有文章标题',  # 假设数据库中已存在相同标题的记录
        'publish_time': '2025-10-09 09:00',  # 与数据库中记录相同的发布时间
        'url': 'https://example.com/existing-article',
        'source': '来源',
        'content': '文章内容'
    }
    
    sql2 = SQLBuilder.make_insert(
        table=table,
        data=duplicate_data,
        auto_update=False,
        update_columns=('title', 'publish_time'),
        insert_ignore=False
    )
    
    print(f"SQL: {sql2[:100]}...")
    print("预期行为: 触发 ON DUPLICATE KEY UPDATE，但字段值未变化，影响行数 = 0")
    print()
    
    # 场景3: 冲突且字段值不同
    print("场景3: 主键冲突，更新字段值不同")
    updated_data = {
        'title': '已有文章标题',  # 与数据库中记录相同
        'publish_time': '2025-10-09 11:00',  # 与数据库中记录不同的发布时间
        'url': 'https://example.com/existing-article',
        'source': '来源',
        'content': '文章内容'
    }
    
    sql3 = SQLBuilder.make_insert(
        table=table,
        data=updated_data,
        auto_update=False,
        update_columns=('title', 'publish_time'),
        insert_ignore=False
    )
    
    print(f"SQL: {sql3[:100]}...")
    print("预期行为: 触发 ON DUPLICATE KEY UPDATE，字段值变化，影响行数 = 2")
    print("(MySQL 5.7+ 版本中，更新操作返回的影响行数为 2)")
    print()
    
    # 场景4: 使用 INSERT IGNORE
    print("场景4: 使用 INSERT IGNORE")
    ignore_data = {
        'title': '忽略重复标题',  # 假设数据库中已存在相同标题的记录
        'publish_time': '2025-10-09 12:00',
        'url': 'https://example.com/ignore-article',
        'source': '忽略来源',
        'content': '忽略内容'
    }
    
    sql4 = SQLBuilder.make_insert(
        table=table,
        data=ignore_data,
        auto_update=False,
        update_columns=(),
        insert_ignore=True
    )
    
    print(f"SQL: {sql4[:100]}...")
    print("预期行为: 遇到重复记录时忽略插入，影响行数 = 0")
    print()
    
    # 场景5: 使用 REPLACE INTO
    print("场景5: 使用 REPLACE INTO")
    replace_data = {
        'title': '替换文章标题',  # 假设数据库中已存在相同标题的记录
        'publish_time': '2025-10-09 13:00',
        'url': 'https://example.com/replace-article',
        'source': '替换来源',
        'content': '替换内容'
    }
    
    sql5 = SQLBuilder.make_insert(
        table=table,
        data=replace_data,
        auto_update=True,  # 使用 REPLACE INTO
        update_columns=(),
        insert_ignore=False
    )
    
    print(f"SQL: {sql5[:100]}...")
    print("预期行为: 删除旧记录并插入新记录，影响行数 = 2")
    print()
    
    print("=== 总结 ===")
    print("1. 当使用 MYSQL_UPDATE_COLUMNS 时，影响行数为 0 并不表示错误")
    print("2. 这可能意味着更新的字段值与现有记录相同")
    print("3. 如果需要确保更新，可以在 update_columns 中包含更多字段")
    print("4. 如果需要完全替换记录，使用 MYSQL_AUTO_UPDATE = True")


if __name__ == "__main__":
    simulate_mysql_scenarios()