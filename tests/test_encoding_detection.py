#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response 编码检测优化测试
"""
import unittest

# 模拟 Response 类的部分功能用于测试
class MockResponse:
    def __init__(self, body, headers=None, request=None):
        self.body = body
        self.headers = headers or {}
        self.request = request
        self._DEFAULT_ENCODING = "ascii"
    
    def _determine_encoding(self):
        """简化版编码检测"""
        # 1. 优先使用声明的编码
        declared_encoding = self._declared_encoding()
        if declared_encoding:
            return declared_encoding
            
        # 2. 默认使用 utf-8
        return 'utf-8'
        
    def _declared_encoding(self):
        """获取声明的编码"""
        # 1. Request 中指定的编码
        if self.request and getattr(self.request, 'encoding', None):
            return self.request.encoding
            
        # 2. 从 Content-Type 头中检测
        content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
        if content_type:
            import re
            charset_match = re.search(r"charset=([\w-]+)", content_type, re.I)
            if charset_match:
                return charset_match.group(1).lower()
        
        return None


class TestDetermineEncoding(unittest.TestCase):
    """编码检测测试类"""

    def test_request_encoding_priority(self):
        """测试 Request 编码优先级"""
        class MockRequest:
            encoding = 'gbk'
        
        response = MockResponse(b'', request=MockRequest())
        encoding = response._determine_encoding()
        self.assertEqual(encoding, 'gbk')

    def test_content_type_encoding(self):
        """测试 Content-Type 头部编码检测"""
        response = MockResponse(
            b'',
            headers={"content-type": "text/html; charset=iso-8859-1"}
        )
        encoding = response._determine_encoding()
        self.assertEqual(encoding, 'iso-8859-1')

    def test_default_encoding(self):
        """测试默认编码"""
        response = MockResponse(b'')
        encoding = response._determine_encoding()
        self.assertEqual(encoding, 'utf-8')

    def test_case_insensitive_content_type(self):
        """测试 Content-Type 头部大小写不敏感"""
        response = MockResponse(
            b'',
            headers={"Content-Type": "text/html; CHARSET=UTF-8"}
        )
        encoding = response._determine_encoding()
        self.assertEqual(encoding, 'utf-8')
        
    def test_declared_encoding_with_request(self):
        """测试声明编码 - Request优先级"""
        class MockRequest:
            encoding = 'gbk'
        
        response = MockResponse(b'', request=MockRequest())
        declared_encoding = response._declared_encoding()
        self.assertEqual(declared_encoding, 'gbk')
        
    def test_declared_encoding_with_content_type(self):
        """测试声明编码 - Content-Type"""
        response = MockResponse(
            b'',
            headers={"content-type": "text/html; charset=iso-8859-1"}
        )
        declared_encoding = response._declared_encoding()
        self.assertEqual(declared_encoding, 'iso-8859-1')


def test_encoding_detection():
    """简单测试编码检测功能"""
    print("测试编码检测功能...")
    
    # 测试 Request 编码优先级
    class MockRequest:
        encoding = 'gbk'
    
    response1 = MockResponse(b'', request=MockRequest())
    encoding1 = response1._determine_encoding()
    print(f"Request 编码优先级: {encoding1}")
    
    # 测试 Content-Type 头部编码
    response2 = MockResponse(
        b'',
        headers={"content-type": "text/html; charset=iso-8859-1"}
    )
    encoding2 = response2._determine_encoding()
    print(f"Content-Type 编码: {encoding2}")
    
    # 测试默认编码
    response3 = MockResponse(b'')
    encoding3 = response3._determine_encoding()
    print(f"默认编码: {encoding3}")
    
    print("编码检测测试完成！")


if __name__ == '__main__':
    test_encoding_detection()