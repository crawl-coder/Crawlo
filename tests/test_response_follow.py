#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response.follow 方法测试
"""
import unittest
from unittest.mock import Mock

# 模拟 Request 类
class MockRequest:
    def __init__(self, url, callback=None, **kwargs):
        self.url = url
        self.callback = callback
        self.kwargs = kwargs

# 模拟 crawlo.Request
import sys
sys.modules['crawlo'] = Mock()
sys.modules['crawlo'].Request = MockRequest

from crawlo.network.response import Response


class TestResponseFollow(unittest.TestCase):
    """Response.follow 方法测试类"""

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
        
        # 创建模拟的请求对象
        mock_request = Mock()
        mock_request.callback = None
        
        self.response = Response(
            url="https://example.com/test",
            body=html_content.encode('utf-8'),
            headers={"content-type": "text/html; charset=utf-8"},
            request=mock_request
        )

    def test_follow_absolute_url(self):
        """测试处理绝对URL"""
        request = self.response.follow("https://other.com/page", callback=lambda r: None)
        self.assertEqual(request.url, "https://other.com/page")
        self.assertIsNotNone(request.callback)

    def test_follow_relative_url(self):
        """测试处理相对URL"""
        request = self.response.follow("/relative/path", callback=lambda r: None)
        self.assertEqual(request.url, "https://example.com/relative/path")
        self.assertIsNotNone(request.callback)

    def test_follow_complex_relative_url(self):
        """测试处理复杂的相对URL"""
        request = self.response.follow("../other/path", callback=lambda r: None)
        self.assertEqual(request.url, "https://example.com/other/path")
        
        request2 = self.response.follow("./another/path", callback=lambda r: None)
        self.assertEqual(request2.url, "https://example.com/another/path")

    def test_follow_with_query_params(self):
        """测试处理带查询参数的URL"""
        request = self.response.follow("/path?param=value", callback=lambda r: None)
        self.assertEqual(request.url, "https://example.com/path?param=value")
        
        request2 = self.response.follow("/path#section", callback=lambda r: None)
        self.assertEqual(request2.url, "https://example.com/path#section")

    def test_follow_with_additional_kwargs(self):
        """测试传递额外参数"""
        request = self.response.follow(
            "/path", 
            callback=lambda r: None,
            method="POST",
            headers={"User-Agent": "test"}
        )
        self.assertEqual(request.url, "https://example.com/path")
        self.assertEqual(request.kwargs.get("method"), "POST")
        self.assertEqual(request.kwargs.get("headers"), {"User-Agent": "test"})


if __name__ == '__main__':
    unittest.main()