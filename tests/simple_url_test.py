#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Response URL 处理方法简单测试
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 直接导入需要的模块
from urllib.parse import urlparse, urlsplit, parse_qs, urlencode, quote, unquote, urldefrag


def test_url_methods():
    """测试 URL 处理方法"""
    print("测试 Response URL 处理方法")
    
    # 测试数据
    test_url = "https://example.com/test?param1=value1&param2=value2#section1"
    print(f"测试URL: {test_url}")
    
    # 1. 测试 urlparse
    print("\n1. 测试 urlparse:")
    parsed = urlparse(test_url)
    print(f"  scheme: {parsed.scheme}")
    print(f"  netloc: {parsed.netloc}")
    print(f"  path: {parsed.path}")
    print(f"  query: {parsed.query}")
    print(f"  fragment: {parsed.fragment}")
    
    # 2. 测试 urlsplit
    print("\n2. 测试 urlsplit:")
    split_result = urlsplit(test_url)
    print(f"  scheme: {split_result.scheme}")
    print(f"  netloc: {split_result.netloc}")
    print(f"  path: {split_result.path}")
    print(f"  query: {split_result.query}")
    print(f"  fragment: {split_result.fragment}")
    
    # 3. 测试 parse_qs
    print("\n3. 测试 parse_qs:")
    query_dict = parse_qs(parsed.query)
    print(f"  解析结果: {query_dict}")
    
    # 4. 测试 urlencode
    print("\n4. 测试 urlencode:")
    test_dict = {"name": "张三", "age": 25, "city": "北京"}
    encoded = urlencode(test_dict)
    print(f"  编码结果: {encoded}")
    
    # 5. 测试 quote/unquote
    print("\n5. 测试 quote/unquote:")
    original = "hello world 你好"
    quoted = quote(original)
    print(f"  原始字符串: {original}")
    print(f"  URL编码: {quoted}")
    
    unquoted = unquote(quoted)
    print(f"  URL解码: {unquoted}")
    print(f"  编码解码是否一致: {original == unquoted}")
    
    # 6. 测试 urldefrag
    print("\n6. 测试 urldefrag:")
    url_without_frag, fragment = urldefrag(test_url)
    print(f"  去除片段的URL: {url_without_frag}")
    print(f"  片段: {fragment}")
    
    print("\n所有测试完成！")


if __name__ == '__main__':
    test_url_methods()