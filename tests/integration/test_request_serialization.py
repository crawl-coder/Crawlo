#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Request 序列化问题修复
"""
import pickle
import sys
sys.path.insert(0, "..")

from crawlo.http.request import Request
from unittest.mock import Mock
from crawlo.logging import get_logger

# 模拟一个带 logger 的 Request
class TestRequest(Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加一个 logger 属性模拟问题
        self.logger = get_logger("test_request")
        self.meta['spider_logger'] = get_logger("spider_logger")

def test_request_serialization():
    """测试 Request 序列化"""
    print("🔍 测试 Request 序列化修复...")
    
    # 创建一个带 logger 的请求
    request = TestRequest(
        url="https://example.com",
        meta={"test": "data"}
    )
    
    print(f"   📦 原始请求: {request}")
    print(f"   请求有 logger: {hasattr(request, 'logger')}")
    print(f"   meta 有 logger: {'spider_logger' in request.meta}")
    
    # 测试 pickle 序列化：重构后 logger 在 Request 构造时由 _safe_deepcopy_meta 清理，
    # 序列化不应再因 logger 失败
    serialized = pickle.dumps(request)
    print(f"   序列化成功，大小: {len(serialized)} bytes")
    
    # 测试反序列化
    deserialized = pickle.loads(serialized)
    print(f"   反序列化成功: {deserialized}")
    return True

if __name__ == "__main__":
    success = test_request_serialization()
    if success:
        print("Request 序列化修复成功！")
    else:
        print("❌ 序列化问题仍未解决")