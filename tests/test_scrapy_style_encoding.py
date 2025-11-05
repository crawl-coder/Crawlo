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
from crawlo.network.response import Response


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
        class MockRequest:
            encoding = 'gbk'
        
        response = Response(
            url="https://example.com",
            body=b'',
            request=MockRequest()
        )
        self.assertEqual(response._declared_encoding(), 'gbk')

    def test_content_type_encoding(self):
        """测试 Content-Type 头部编码检测"""
        response = Response(
            url="https://example.com",
            body=b'',
            headers={"content-type": "text/html; charset=iso-8859-1"}
        )
        self.assertEqual(response.encoding, 'iso-8859-1')

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
        self.assertEqual(response.encoding, 'utf-8')

    def test_declared_encoding_priority(self):
        """测试声明编码的优先级"""
        # 模拟没有request编码的情况
        response = Response(
            url="https://example.com",
            body=b'',
            headers={"content-type": "text/html; charset=iso-8859-1"}
        )
        # 应该返回Content-Type中的编码
        self.assertEqual(response._declared_encoding(), 'iso-8859-1')


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
    
    # 测试声明编码方法
    declared_enc = response2._declared_encoding()
    print(f"声明编码: {declared_enc}")
    
    # 测试默认编码
    response3 = Response(
        url="https://example.com",
        body=b''
    )
    print(f"默认编码: {response3.encoding}")
    
    print("Scrapy风格编码检测测试完成！")


if __name__ == '__main__':
    test_scrapy_style_encoding()