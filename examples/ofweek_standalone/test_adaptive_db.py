#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""快速测试 adaptive=True 是否会自动创建数据库文件"""

import os
from crawlo.network.response import Response

print("="*60)
print("测试：adaptive=True 自动创建数据库文件")
print("="*60)

# 删除可能存在的旧文件
if os.path.exists('adaptive_fingerprints.db'):
    os.remove('adaptive_fingerprints.db')
    print("✓ 已删除旧的数据库文件")

# 创建 HTML 内容
html = """
<html>
<body>
    <div class="main_left">
        <div class="list_model">
            <div class="model_right model_right2">
                <h3><a href="/article1.html">测试文章1</a></h3>
            </div>
            <div class="model_right model_right2">
                <h3><a href="/article2.html">测试文章2</a></h3>
            </div>
        </div>
    </div>
</body>
</html>
"""

# 创建 Response 并使用 adaptive=True
response = Response(
    url='https://ee.ofweek.com/test.html',
    body=html.encode('utf-8')
)

print("\n使用 adaptive=True 提取元素...")
items = response.xpath(
    '//div[@class="model_right model_right2"]',
    adaptive=True,
    identifier='test_selector'
)

print(f"✓ 提取到 {len(items)} 个元素")
for i, item in enumerate(items, 1):
    title = item.xpath('./h3/a/text()').extract_first()
    print(f"  [{i}] {title}")

# 检查数据库文件
db_file = 'adaptive_fingerprints.db'
print(f"\n检查数据库文件: {db_file}")
if os.path.exists(db_file):
    file_size = os.path.getsize(db_file)
    print(f"✓✓✓ 数据库文件已自动创建！")
    print(f"  大小: {file_size} 字节")
    print(f"  路径: {os.path.abspath(db_file)}")
else:
    print("✗ 数据库文件不存在")

# 清理
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"\n✓ 已清理测试文件: {db_file}")
