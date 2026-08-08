#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
测试Response类中的选择器方法
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.http.response import Response


def test_response_selector_methods():
    """测试Response类中的选择器方法"""
    print("测试Response类中的选择器方法...")
    print("=" * 50)
    
    # 创建测试HTML响应
    html_content = """
    <html>
    <head>
        <title>测试页面</title>
    </head>
    <body>
        <div class="content">
            <h1>主标题</h1>
            <p class="intro">介绍段落</p>
            <ul class="list">
                <li>项目1</li>
                <li>项目2</li>
                <li>项目3</li>
            </ul>
            <a href="https://example.com" class="link">链接文本</a>
            <img src="image.jpg" alt="图片描述" class="image">
        </div>
    </body>
    </html>
    """
    
    # 创建Response对象
    response = Response(
        url="https://example.com/test",
        body=html_content.encode('utf-8'),
        headers={"content-type": "text/html; charset=utf-8"}
    )
    
    # 测试 get (CSS选择器)
    print("1. 测试 get (CSS选择器):")
    title_text = response.get('title')
    print(f"   标题文本: {title_text}")

    h1_text = response.get('.content h1')
    print(f"   H1文本: {h1_text}")
    print()

    # 测试 get (XPath选择器)
    print("2. 测试 get (XPath选择器):")
    title_text_xpath = response.get('//title')
    print(f"   标题文本: {title_text_xpath}")

    h1_text_xpath = response.get('//div[@class="content"]/h1')
    print(f"   H1文本: {h1_text_xpath}")
    print()

    # 测试 getall
    print("3. 测试 getall:")
    li_texts = response.getall('.list li')
    print(f"   列表项文本: {li_texts}")
    print()

    # 测试 attr
    print("4. 测试 attr:")
    link_href = response.attr('.link', 'href')
    print(f"   链接href: {link_href}")

    img_alt = response.attr('.image', 'alt')
    print(f"   图片alt: {img_alt}")
    print()

    # 测试 attrs
    print("5. 测试 attrs:")
    all_links = response.attrs('a', 'href')
    print(f"   所有链接href: {all_links}")

    all_images = response.attrs('img', 'src')
    print(f"   所有图片src: {all_images}")
    print()
    
    print("所有测试完成！")


if __name__ == '__main__':
    test_response_selector_methods()