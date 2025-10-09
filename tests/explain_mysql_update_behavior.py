# -*- coding: utf-8 -*-
"""
解释 MySQL ON DUPLICATE KEY UPDATE 行为
帮助理解为什么在使用 MYSQL_UPDATE_COLUMNS 时可能显示"未插入新记录"
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.db_helper import SQLBuilder


def explain_mysql_behavior():
    """解释 MySQL ON DUPLICATE KEY UPDATE 的行为"""
    print("=== MySQL ON DUPLICATE KEY UPDATE 行为解释 ===\n")
    
    # 模拟实际使用的数据
    table = "news_items"
    item_data = {
        'title': '新一代OLED屏下光谱颜色传感技术：解锁显示新密码，重塑视觉新体验',
        'publish_time': '2025-10-09 09:57',
        'url': 'https://ee.ofweek.com/2025-10/ART-8460-2806-30671544.html',
        'source': '',
        'content': '在全球智能手机市场竞争日趋白热化的当下，消费者对手机屏幕显示效果的要求愈发严苛...'
    }
    
    print("当使用 MYSQL_UPDATE_COLUMNS 配置时:")
    print("MYSQL_UPDATE_COLUMNS = ('title', 'publish_time')")
    print()
    
    # 生成 SQL
    sql = SQLBuilder.make_insert(
        table=table,
        data=item_data,
        auto_update=False,
        update_columns=('title', 'publish_time'),
        insert_ignore=False
    )
    
    print("生成的 SQL 语句:")
    print(sql)
    print()
    
    print("MySQL 行为说明:")
    print("1. 如果这是一条新记录（没有主键或唯一键冲突）:")
    print("   - MySQL 会正常插入记录")
    print("   - 返回影响行数为 1")
    print()
    print("2. 如果遇到主键或唯一键冲突:")
    print("   - MySQL 会执行 ON DUPLICATE KEY UPDATE 子句")
    print("   - 更新指定的字段: title 和 publish_time")
    print()
    print("3. 关键点 - 如果更新的字段值与现有记录完全相同:")
    print("   - MySQL 不会实际更新任何数据")
    print("   - 返回影响行数为 0")
    print("   - 这就是你看到 'SQL执行成功但未插入新记录' 的原因")
    print()
    
    print("如何验证是否真的更新了数据:")
    print("1. 检查数据库中的记录是否发生变化")
    print("2. 如果内容字段有变化但未在 update_columns 中指定，则不会更新")
    print("3. 可以在 update_columns 中添加更多字段以确保更新")
    print()
    
    print("建议的配置:")
    print("# 如果希望在冲突时更新更多字段，可以这样配置:")
    print("MYSQL_UPDATE_COLUMNS = ('title', 'publish_time', 'content')")
    print()
    print("# 或者如果希望完全替换记录:")
    print("MYSQL_AUTO_UPDATE = True")
    print("MYSQL_UPDATE_COLUMNS = ()  # 空元组")


if __name__ == "__main__":
    explain_mysql_behavior()