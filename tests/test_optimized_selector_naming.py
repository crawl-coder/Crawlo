#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
优化后的选择器命名测试
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils import (
    extract_text,
    extract_texts,
    extract_attr,
    extract_attrs,
    is_xpath
)
from parsel import Selector


def test_optimized_naming():
    """测试优化后的命名"""
    print("测试优化后的选择器命名...")
    print("=" * 50)
    
    # 创建测试HTML
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
    
    selector = Selector(text=html_content)
    
    # 测试 is_xpath
    print("1. 测试 is_xpath:")
    print(f"   '/' 开头: {is_xpath('/')}")
    print(f"   '//' 开头: {is_xpath('//title')}")
    print(f"   './' 开头: {is_xpath('./div')}")
    print(f"   'title' 开头: {is_xpath('title')}")
    print()
    
    # 测试 extract_text
    print("2. 测试 extract_text:")
    title_elements = selector.css('title')
    title_text = extract_text(title_elements)
    print(f"   标题文本: {title_text}")
    
    h1_elements = selector.css('.content h1')
    h1_text = extract_text(h1_elements)
    print(f"   H1文本: {h1_text}")
    print()
    
    # 测试 extract_texts
    print("3. 测试 extract_texts:")
    li_elements = selector.css('.list li')
    li_texts = extract_texts(li_elements)
    print(f"   列表项文本: {li_texts}")
    print()
    
    # 测试 extract_attr
    print("4. 测试 extract_attr:")
    link_elements = selector.css('.link')
    link_href = extract_attr(link_elements, 'href')
    print(f"   链接href: {link_href}")
    
    img_elements = selector.css('.image')
    img_alt = extract_attr(img_elements, 'alt')
    print(f"   图片alt: {img_alt}")
    print()
    
    # 测试 extract_attrs
    print("5. 测试 extract_attrs:")
    all_links = selector.css('a')
    all_hrefs = extract_attrs(all_links, 'href')
    print(f"   所有链接href: {all_hrefs}")
    
    all_images = selector.css('img')
    all_srcs = extract_attrs(all_images, 'src')
    print(f"   所有图片src: {all_srcs}")
    print()
    
    print("所有测试完成！")


if __name__ == '__main__':
    test_optimized_naming()