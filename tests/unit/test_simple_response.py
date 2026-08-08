#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response 简单功能测试
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.network.response import Response


def test_basic_functionality():
    """测试基本功能"""
    print("测试基本功能...")
    
    # 创建一个简单的HTML响应
    html_content = """
    <html>
    <head>
        <title>测试页面</title>
    </head>
    <body>
        <div class="content">
            <h1>主标题</h1>
            <p class="intro">这是介绍段落</p>
        </div>
    </body>
    </html>
    """
    
    response = Response(
        url="https://example.com/test",
        body=html_content.encode('utf-8'),
        headers={"content-type": "text/html; charset=utf-8"}
    )
    
    # 测试基本属性
    print(f"URL: {response.url}")
    print(f"状态码: {response.status_code}")
    
    # 测试文本提取（使用新方法）
    title = response.extract_text('title')
    print(f"标题: {title}")
    
    h1_text = response.extract_text('.content h1')
    print(f"H1文本: {h1_text}")
    
    intro_text = response.extract_text('.intro')
    print(f"介绍文本: {intro_text}")
    
    # 测试XPath（使用新方法）
    title_xpath = response.extract_text('//title')
    print(f"XPath标题: {title_xpath}")
    
    print("基本功能测试完成")


if __name__ == '__main__':
    test_basic_functionality()