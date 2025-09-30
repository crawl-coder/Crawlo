#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
简化选择器辅助工具测试
"""
from parsel import Selector


# 直接复制工具函数用于测试
def extract_text(elements, join_str=" "):
    """
    从元素列表中提取文本并拼接
    """
    texts = []
    for element in elements:
        if hasattr(element, 'xpath'):
            element_texts = element.xpath('.//text()').getall()
        else:
            element_texts = [str(element)]
        for text in element_texts:
            cleaned = text.strip()
            if cleaned:
                texts.append(cleaned)
    return join_str.join(texts)


def extract_texts(elements, join_str=" "):
    """
    从元素列表中提取多个文本列表
    """
    result = []
    for element in elements:
        if hasattr(element, 'xpath'):
            texts = element.xpath('.//text()').getall()
        else:
            texts = [str(element)]
        clean_texts = [text.strip() for text in texts if text.strip()]
        if clean_texts:
            result.append(join_str.join(clean_texts))
    return result


def extract_attr(elements, attr_name, default=None):
    """
    从元素列表中提取单个元素的属性值
    """
    if hasattr(elements, 'attrib'):
        return elements.attrib.get(attr_name, default)
    elif len(elements) > 0 and hasattr(elements[0], 'attrib'):
        return elements[0].attrib.get(attr_name, default)
    return default


def extract_attrs(elements, attr_name):
    """
    从元素列表中提取多个元素的属性值列表
    """
    result = []
    for element in elements:
        if hasattr(element, 'attrib'):
            attr_value = element.attrib.get(attr_name)
            if attr_value is not None:
                result.append(attr_value)
    return result


def is_xpath(query):
    """
    判断查询语句是否为XPath
    """
    return query.startswith(('/', '//', './'))


def test_selector_helper():
    """测试选择器辅助工具"""
    print("测试选择器辅助工具...")
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
    test_selector_helper()