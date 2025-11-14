#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
简化版指纹一致性测试
==============
验证框架中各组件对相同数据生成一致的指纹
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.fingerprint import FingerprintGenerator


def test_fingerprint_consistency():
    """测试指纹一致性"""
    # 测试数据
    test_data = {
        "title": "Test Title",
        "url": "https://example.com",
        "content": "Test content",
        "price": 99.99
    }
    
    # 使用指纹生成器生成指纹
    fingerprint1 = FingerprintGenerator.data_fingerprint(test_data)
    fingerprint2 = FingerprintGenerator.data_fingerprint(test_data)
    
    # 验证相同数据生成相同指纹
    print(f"First fingerprint: {fingerprint1}")
    print(f"Second fingerprint: {fingerprint2}")
    print(f"指纹一致: {fingerprint1 == fingerprint2}")
    
    # 测试请求指纹
    method = "GET"
    url = "https://example.com"
    body = b""
    headers = {"User-Agent": "test-agent"}
    
    request_fingerprint1 = FingerprintGenerator.request_fingerprint(method, url, body, headers)
    request_fingerprint2 = FingerprintGenerator.request_fingerprint(method, url, body, headers)
    
    print(f"\nRequest fingerprint 1: {request_fingerprint1}")
    print(f"Request fingerprint 2: {request_fingerprint2}")
    print(f"请求指纹一致: {request_fingerprint1 == request_fingerprint2}")


if __name__ == '__main__':
    test_fingerprint_consistency()