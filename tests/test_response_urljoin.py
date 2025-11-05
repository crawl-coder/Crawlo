#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response.urljoin 方法测试
"""
import unittest
from crawlo.network.response import Response


class TestResponseUrljoin(unittest.TestCase):
    """Response.urljoin 方法测试类"""

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
                <a href="/relative/path" class="relative-link">相对链接</a>
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

    def test_urljoin_absolute_url(self):
        """测试处理绝对URL"""
        absolute_url = self.response.urljoin("https://other.com/page")
        self.assertEqual(absolute_url, "https://other.com/page")

    def test_urljoin_relative_url(self):
        """测试处理相对URL"""
        relative_url = self.response.urljoin("/relative/path")
        self.assertEqual(relative_url, "https://example.com/relative/path")
        
        relative_url2 = self.response.urljoin("relative/path")
        self.assertEqual(relative_url2, "https://example.com/relative/path")

    def test_urljoin_complex_relative_url(self):
        """测试处理复杂的相对URL"""
        relative_url = self.response.urljoin("../other/path")
        self.assertEqual(relative_url, "https://example.com/other/path")
        
        relative_url2 = self.response.urljoin("./another/path")
        self.assertEqual(relative_url2, "https://example.com/another/path")

    def test_urljoin_with_query_params(self):
        """测试处理带查询参数的URL"""
        url_with_params = self.response.urljoin("/path?param=value")
        self.assertEqual(url_with_params, "https://example.com/path?param=value")
        
        url_with_fragment = self.response.urljoin("/path#section")
        self.assertEqual(url_with_fragment, "https://example.com/path#section")

    def test_urljoin_empty_url(self):
        """测试处理空URL"""
        empty_url = self.response.urljoin("")
        self.assertEqual(empty_url, "https://example.com/test")

    def test_urljoin_none_url(self):
        """测试处理None URL"""
        # 由于 urllib.parse.urljoin 会将 None 转换为字符串 "None"，所以我们测试实际行为
        none_url = self.response.urljoin(None)
        # 根据实际测试结果，urllib.parse.urljoin(None) 返回基础URL
        # 我们接受这种行为，因为它与 urllib.parse.urljoin 的行为一致
        self.assertEqual(none_url, "https://example.com/test")

if __name__ == '__main__':
    unittest.main()