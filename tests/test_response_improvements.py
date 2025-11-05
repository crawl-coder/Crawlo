#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response 改进功能测试
"""
import unittest
from crawlo.network.response import Response


class TestResponseImprovements(unittest.TestCase):
    """Response 改进功能测试类"""

    def setUp(self):
        """测试前准备"""
        # 创建一个模拟的HTML响应
        html_content = """
        <html>
        <head>
            <title>测试页面</title>
        </head>
        <body>
            <div class="content">
                <h1>主标题</h1>
                <p class="intro">这是介绍段落</p>
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
        
        self.response = Response(
            url="https://example.com/test",
            body=html_content.encode('utf-8'),
            headers={"content-type": "text/html; charset=utf-8"}
        )

    def test_extract_text_with_css(self):
        """测试使用CSS选择器提取文本"""
        # 测试提取单个元素文本
        title = self.response.extract_text('title')
        self.assertEqual(title, "测试页面")
        
        # 测试提取class元素文本
        h1_text = self.response.extract_text('.content h1')
        self.assertEqual(h1_text, "主标题")
        
        # 测试提取带有默认值的情况
        non_exist = self.response.extract_text('.non-exist', default='默认值')
        self.assertEqual(non_exist, '默认值')

    def test_extract_text_with_xpath(self):
        """测试使用XPath选择器提取文本"""
        # 测试提取单个元素文本
        title = self.response.extract_text('//title')
        self.assertEqual(title, "测试页面")
        
        # 测试提取class元素文本
        h1_text = self.response.extract_text('//div[@class="content"]/h1')
        self.assertEqual(h1_text, "主标题")

    def test_extract_texts_with_css(self):
        """测试使用CSS选择器提取多个文本"""
        # 测试提取多个li元素的文本
        list_items = self.response.extract_texts('.list li')
        expected = ["项目1", "项目2", "项目3"]
        self.assertEqual(list_items, expected)
        
        # 测试提取不存在元素的默认值
        non_exist = self.response.extract_texts('.non-exist', default=['默认值'])
        self.assertEqual(non_exist, ['默认值'])

    def test_extract_texts_with_xpath(self):
        """测试使用XPath选择器提取多个文本"""
        # 测试提取多个li元素的文本
        list_items = self.response.extract_texts('//ul[@class="list"]/li')
        expected = ["项目1", "项目2", "项目3"]
        self.assertEqual(list_items, expected)

    def test_extract_attr(self):
        """测试提取元素属性"""
        # 测试提取链接的href属性
        link_href = self.response.extract_attr('.link', 'href')
        self.assertEqual(link_href, "https://example.com")
        
        # 测试提取图片的alt属性
        img_alt = self.response.extract_attr('.image', 'alt')
        self.assertEqual(img_alt, "图片描述")
        
        # 测试提取不存在属性的默认值
        non_exist = self.response.extract_attr('.link', 'non-exist', default='默认值')
        self.assertEqual(non_exist, '默认值')

    def test_extract_attrs(self):
        """测试提取多个元素的属性"""
        # 测试提取所有li元素的属性（这里我们测试class属性）
        list_classes = self.response.extract_attrs('.list li', 'class')
        # 注意：在当前HTML中li元素没有class属性，所以应该返回空列表
        self.assertEqual(list_classes, [])
        
        # 测试提取所有图片元素的alt属性
        img_alts = self.response.extract_attrs('.image', 'alt')
        self.assertEqual(img_alts, ['图片描述'])
        
        # 测试提取不存在元素时的默认值
        non_exist = self.response.extract_attrs('.non-exist-elements', 'alt', default=['默认值'])
        self.assertEqual(non_exist, ['默认值'])

    def test_extract_text_from_elements(self):
        """测试从复杂元素中提取文本"""
        # 创建包含嵌套标签的HTML
        complex_html = """
        <div class="complex">
            <p>段落文本 <strong>粗体文本</strong> 普通文本</p>
            <p>第二段落 <em>斜体文本</em></p>
        </div>
        """
        
        complex_response = Response(
            url="https://example.com/complex",
            body=complex_html.encode('utf-8')
        )
        
        # 测试提取复杂元素的文本
        complex_text = complex_response.extract_text('.complex p', join_str=' ')
        self.assertIn("段落文本", complex_text)
        self.assertIn("粗体文本", complex_text)
        self.assertIn("普通文本", complex_text)

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试空响应
        empty_response = Response(url="https://example.com/empty", body=b"")
        empty_text = empty_response.extract_text('title', default='默认标题')
        self.assertEqual(empty_text, '默认标题')
        
        # 测试只包含空白字符的元素
        whitespace_html = "<div class='whitespace'>   </div>"
        whitespace_response = Response(
            url="https://example.com/whitespace",
            body=whitespace_html.encode('utf-8')
        )
        whitespace_text = whitespace_response.extract_text('.whitespace')
        self.assertEqual(whitespace_text, '')


if __name__ == '__main__':
    unittest.main()