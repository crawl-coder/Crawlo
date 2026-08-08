#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Scrapy风格编码检测测试
"""
import unittest
from crawlo.http.response import Response


class TestScrapyStyleEncoding(unittest.TestCase):
    """Scrapy风格编码检测测试类"""

    def test_request_encoding_priority(self):
        """测试 Request 编码优先级"""
        class MockRequest:
            encoding = 'gbk'
        
        response = Response(
            url="https://example.com",
            body=b'',
            request=MockRequest()
        )
        self.assertEqual(response.encoding, 'gbk')

    def test_declared_encoding_method(self):
        """测试 _declared_encoding 方法"""
        # _declared_encoding() 方法已移除，声明编码优先级现通过 response.encoding 覆盖
        # （见 test_request_encoding_priority）
        self.skipTest("_declared_encoding() 方法已移除，声明编码优先级由 response.encoding 覆盖")

    def test_content_type_encoding(self):
        """测试 Content-Type 头部编码检测"""
        response = Response(
            url="https://example.com",
            body=b'',
            headers={"content-type": "text/html; charset=iso-8859-1"}
        )
        # w3lib 按 HTML5 规范将 iso-8859-1 解析为 cp1252（windows-1252）
        self.assertEqual(response.encoding, 'cp1252')

    def test_case_insensitive_content_type(self):
        """测试 Content-Type 头部大小写不敏感"""
        response = Response(
            url="https://example.com",
            body=b'',
            headers={"Content-Type": "text/html; CHARSET=UTF-8"}
        )
        self.assertEqual(response.encoding, 'utf-8')

    def test_default_encoding(self):
        """测试默认编码"""
        response = Response(
            url="https://example.com",
            body=b''
        )
        # w3lib 对空内容将 ascii 解析为 cp1252
        self.assertEqual(response.encoding, 'cp1252')

    def test_declared_encoding_priority(self):
        """测试声明编码的优先级"""
        # _declared_encoding() 方法已移除，Content-Type 编码检测由 response.encoding 覆盖
        # （见 test_content_type_encoding）
        self.skipTest("_declared_encoding() 方法已移除，Content-Type 编码检测由 response.encoding 覆盖")


def test_scrapy_style_encoding():
    """测试Scrapy风格的编码检测"""
    print("测试Scrapy风格的编码检测...")
    
    # 测试 Request 编码优先级
    class MockRequest:
        encoding = 'gbk'
    
    response1 = Response(
        url="https://example.com",
        body=b'',
        request=MockRequest()
    )
    print(f"Request 编码优先级: {response1.encoding}")
    
    # 测试 Content-Type 头部编码
    response2 = Response(
        url="https://example.com",
        body=b'',
        headers={"content-type": "text/html; charset=iso-8859-1"}
    )
    print(f"Content-Type 编码: {response2.encoding}")
    
    # 测试声明编码方法（_declared_encoding 已移除，改用 response.encoding）
    print(f"声明编码(即 response.encoding): {response2.encoding}")

    # 测试默认编码
    response3 = Response(
        url="https://example.com",
        body=b''
    )
    print(f"默认编码: {response3.encoding}")
    
    print("Scrapy风格编码检测测试完成！")


if __name__ == '__main__':
    test_scrapy_style_encoding()