#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
简化选择器测试
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 直接导入需要的模块
from parsel import Selector, SelectorList


class MockResponse:
    """模拟Response类用于测试"""
    
    def __init__(self, text):
        self._text = text
        self._selector_instance = None
    
    @property
    def text(self):
        return self._text
    
    @property
    def _selector(self):
        if self._selector_instance is None:
            self._selector_instance = Selector(self.text)
        return self._selector_instance

    def xpath(self, query):
        return self._selector.xpath(query)

    def css(self, query):
        return self._selector.css(query)

    def _is_xpath(self, query):
        return query.startswith(('/', '//', './'))

    def _extract_text_from_elements(self, elements, join_str=" "):
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

    def extract_text(self, xpath_or_css, join_str=" ", default=''):
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
            return self._extract_text_from_elements(elements, join_str)
        except Exception:
            return default

    def extract_texts(self, xpath_or_css, join_str=" ", default=None):
        if default is None:
            default = []
            
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
                
            result = []
            for element in elements:
                if hasattr(element, 'xpath'):
                    texts = element.xpath('.//text()').getall()
                else:
                    texts = [str(element)]
                    
                clean_texts = [text.strip() for text in texts if text.strip()]
                if clean_texts:
                    result.append(join_str.join(clean_texts))
                    
            return result if result else default
        except Exception:
            return default

    def extract_attr(self, xpath_or_css, attr_name, default=None):
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
            if hasattr(elements, 'attrib'):
                return elements.attrib.get(attr_name, default)
            elif len(elements) > 0 and hasattr(elements[0], 'attrib'):
                return elements[0].attrib.get(attr_name, default)
            return default
        except Exception:
            return default

    def extract_attrs(self, xpath_or_css, attr_name, default=None):
        if default is None:
            default = []
            
        try:
            elements = self.xpath(xpath_or_css) if self._is_xpath(xpath_or_css) else self.css(xpath_or_css)
            if not elements:
                return default
                
            result = []
            for element in elements:
                if hasattr(element, 'attrib'):
                    attr_value = element.attrib.get(attr_name)
                    if attr_value is not None:
                        result.append(attr_value)
                        
            return result if result else default
        except Exception:
            return default


def test_selector_methods():
    """测试选择器方法"""
    print("测试选择器方法...")
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
    
    response = MockResponse(html_content)
    
    # 测试 extract_text
    print("1. 测试 extract_text:")
    title = response.extract_text('title')
    print(f"   标题: {title}")
    
    h1_text = response.extract_text('.content h1')
    print(f"   H1文本: {h1_text}")
    
    # 测试XPath
    title_xpath = response.extract_text('//title')
    print(f"   XPath标题: {title_xpath}")
    
    print()
    
    # 测试 extract_texts
    print("2. 测试 extract_texts:")
    list_items = response.extract_texts('.list li')
    print(f"   列表项: {list_items}")
    
    # 测试XPath
    list_items_xpath = response.extract_texts('//ul[@class="list"]/li')
    print(f"   XPath列表项: {list_items_xpath}")
    
    print()
    
    # 测试 extract_attr
    print("3. 测试 extract_attr:")
    link_href = response.extract_attr('.link', 'href')
    print(f"   链接href: {link_href}")
    
    img_alt = response.extract_attr('.image', 'alt')
    print(f"   图片alt: {img_alt}")
    
    # 测试XPath
    link_href_xpath = response.extract_attr('//a[@class="link"]', 'href')
    print(f"   XPath链接href: {link_href_xpath}")
    
    print()
    
    # 测试 extract_attrs
    print("4. 测试 extract_attrs:")
    all_links = response.extract_attrs('a', 'href')
    print(f"   所有链接: {all_links}")
    
    print()
    
    # 测试边界情况
    print("5. 测试边界情况:")
    non_exist = response.extract_text('.non-exist', default='默认文本')
    print(f"   不存在元素的默认值: {non_exist}")
    
    non_exist_attr = response.extract_attr('.non-exist', 'href', default='默认链接')
    print(f"   不存在属性的默认值: {non_exist_attr}")
    
    print()
    print("所有测试完成！")


if __name__ == '__main__':
    test_selector_methods()