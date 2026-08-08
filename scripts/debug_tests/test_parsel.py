#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
parsel 库测试
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from parsel import Selector, SelectorList
    print("parsel 导入成功")
    
    # 测试基本功能
    html = "<html><body><h1>测试标题</h1></body></html>"
    selector = Selector(html)
    print("Selector 创建成功")
    
    elements = selector.css('h1')
    print("CSS 选择器执行成功")
    
    text = elements.get()
    print(f"获取文本: {text}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()