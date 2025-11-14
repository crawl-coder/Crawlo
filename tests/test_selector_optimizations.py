#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
选择器方法优化测试
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.network.response import Response


def test_selector_optimizations():
    """测试选择器方法优化"""
    print("测试选择器方法优化...")
    print("=" * 50)
    
    # 创建一个复杂的HTML响应
    html_content = """
    <html>
    <head>
        <title>测试页面标题</title>
    </head>
    <body>
        <div class="content">
            <h1>主标题</h1>
            <p class="intro">这是介绍段落</p>
            <div class="article">
                <p>第一段内容 <strong>粗体文本</strong> 普通文本</p>
                <p>第二段内容 <em>斜体文本</em></p>
            </div>
            <ul class="list">
                <li>项目1</li>
                <li>项目2</li>
                <li>项目3</li>
            </ul>
            <a href="https://example.com" class="link">链接文本</a>
            <img src="image.jpg" alt="图片描述" class="image">
            <div class="products">
                <div class="product" data-id="1">
                    <h2>产品A</h2>
                    <p class="price">¥99.99</p>
                </div>
                <div class="product" data-id="2">
                    <h2>产品B</h2>
                    <p class="price">¥149.99</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    response = Response(
        url="https://example.com/test",
        body=html_content.encode('utf-8'),
        headers={"content-type": "text/html; charset=utf-8"}
    )
    
    # 测试 extract_text 方法
    print("1. 测试 extract_text 方法:")
    title = response.extract_text('title')
    print(f"   标题: {title}")
    
    h1_text = response.extract_text('.content h1')
    print(f"   H1文本: {h1_text}")
    
    # 测试XPath
    title_xpath = response.extract_text('//title')
    print(f"   XPath标题: {title_xpath}")
    
    # 测试复杂文本提取
    complex_text = response.extract_text('.article p', join_str=' ')
    print(f"   复杂文本: {complex_text}")
    
    print()
    
    # 测试 extract_texts 方法
    print("2. 测试 extract_texts 方法:")
    list_items = response.extract_texts('.list li')
    print(f"   列表项: {list_items}")
    
    # 测试XPath
    list_items_xpath = response.extract_texts('//ul[@class="list"]/li')
    print(f"   XPath列表项: {list_items_xpath}")
    
    # 测试多个元素
    product_names = response.extract_texts('.product h2')
    print(f"   产品名称: {product_names}")
    
    product_prices = response.extract_texts('.price')
    print(f"   产品价格: {product_prices}")
    
    print()
    
    # 测试 extract_attr 方法
    print("3. 测试 extract_attr 方法:")
    link_href = response.extract_attr('.link', 'href')
    print(f"   链接href: {link_href}")
    
    img_alt = response.extract_attr('.image', 'alt')
    print(f"   图片alt: {img_alt}")
    
    # 测试XPath
    link_href_xpath = response.extract_attr('//a[@class="link"]', 'href')
    print(f"   XPath链接href: {link_href_xpath}")
    
    print()
    
    # 测试 extract_attrs 方法
    print("4. 测试 extract_attrs 方法:")
    product_ids = response.extract_attrs('.product', 'data-id')
    print(f"   产品ID: {product_ids}")
    
    # 测试XPath
    product_ids_xpath = response.extract_attrs('//div[@class="product"]', 'data-id')
    print(f"   XPath产品ID: {product_ids_xpath}")
    
    # 测试所有链接
    all_links = response.extract_attrs('a', 'href')
    print(f"   所有链接: {all_links}")
    
    print()
    
    # 测试边界情况
    print("5. 测试边界情况:")
    # 测试默认值
    non_exist = response.extract_text('.non-exist', default='默认文本')
    print(f"   不存在元素的默认值: {non_exist}")
    
    non_exist_attr = response.extract_attr('.non-exist', 'href', default='默认链接')
    print(f"   不存在属性的默认值: {non_exist_attr}")
    
    print()
    
    # 测试空响应
    print("6. 测试空响应:")
    empty_response = Response(url="https://example.com/empty", body=b"")
    empty_text = empty_response.extract_text('title', default='默认标题')
    print(f"   空响应默认值: {empty_text}")
    
    print()
    print("所有测试完成！")


if __name__ == '__main__':
    test_selector_optimizations()