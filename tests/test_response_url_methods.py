#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response URL 处理方法测试
"""
import unittest
from urllib.parse import urlparse, urlsplit, parse_qs, urlencode, quote, unquote, urldefrag


class TestUrlMethods(unittest.TestCase):
    """URL 处理方法测试类"""

    def setUp(self):
        """测试前准备"""
        self.test_url = "https://example.com/test?param1=value1&param2=value2#section1"

    def test_urlparse(self):
        """测试 urlparse 方法"""
        parsed = urlparse(self.test_url)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "example.com")
        self.assertEqual(parsed.path, "/test")
        self.assertEqual(parsed.query, "param1=value1&param2=value2")
        self.assertEqual(parsed.fragment, "section1")

    def test_urlsplit(self):
        """测试 urlsplit 方法"""
        split_result = urlsplit(self.test_url)
        self.assertEqual(split_result.scheme, "https")
        self.assertEqual(split_result.netloc, "example.com")
        self.assertEqual(split_result.path, "/test")
        self.assertEqual(split_result.query, "param1=value1&param2=value2")
        self.assertEqual(split_result.fragment, "section1")

    def test_parse_qs(self):
        """测试 parse_qs 方法"""
        query_dict = parse_qs("param1=value1&param2=value2&param2=value3")
        self.assertIn("param1", query_dict)
        self.assertIn("param2", query_dict)
        self.assertEqual(query_dict["param1"], ["value1"])
        self.assertEqual(query_dict["param2"], ["value2", "value3"])

    def test_urlencode(self):
        """测试 urlencode 方法"""
        query_dict = {"name": "张三", "age": 25, "city": "北京"}
        encoded = urlencode(query_dict)
        # 注意：urlencode 的顺序可能不同，所以我们检查是否包含所有键值对
        self.assertIn("name=%E5%BC%A0%E4%B8%89", encoded)
        self.assertIn("age=25", encoded)
        self.assertIn("city=%E5%8C%97%E4%BA%AC", encoded)

    def test_quote_unquote(self):
        """测试 quote 和 unquote 方法"""
        # 测试 quote
        original = "hello world 你好"
        quoted = quote(original)
        self.assertEqual(quoted, "hello%20world%20%E4%BD%A0%E5%A5%BD")
        
        # 测试 unquote
        unquoted = unquote(quoted)
        self.assertEqual(unquoted, original)

    def test_urldefrag(self):
        """测试 urldefrag 方法"""
        url_without_frag, fragment = urldefrag(self.test_url)
        self.assertEqual(url_without_frag, "https://example.com/test?param1=value1&param2=value2")
        self.assertEqual(fragment, "section1")


if __name__ == '__main__':
    unittest.main()