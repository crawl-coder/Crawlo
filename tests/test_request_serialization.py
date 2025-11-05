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

from crawlo.network.request import Request
from crawlo.core.scheduler import Scheduler
from unittest.mock import Mock

# 模拟一个带 logger 的 Request
class TestRequest(Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加一个 logger 属性模拟问题
        from crawlo.utils.log import get_logger
        self.logger = get_logger("test_request")
        self.meta['spider_logger'] = get_logger("spider_logger")

def test_request_serialization():
    """测试 Request 序列化"""
    print("🔍 测试 Request 序列化修复...")
    
    # 创建一个带 logger 的请求
    request = TestRequest(
        url="https://example.com",
        meta={"test": "data"}  # 移除 Mock 对象
    )
    
    print(f"   📦 原始请求: {request}")
    print(f"   请求有 logger: {hasattr(request, 'logger')}")
    print(f"   meta 有 logger: {'spider_logger' in request.meta}")
    
    # 创建一个 mock scheduler 来测试清理
    class MockScheduler:
        def _deep_clean_loggers(self, request):
            return Scheduler._deep_clean_loggers(self, request)
        def _remove_logger_from_dict(self, d):
            return Scheduler._remove_logger_from_dict(self, d)
    
    scheduler = MockScheduler()
    
    # 执行清理
    scheduler._deep_clean_loggers(request)
    
    print(f"   🧹 清理后有 logger: {hasattr(request, 'logger')}")
    print(f"   🧹 清理后 meta 有 logger: {'spider_logger' in request.meta}")
    
    # 测试序列化
    try:
        serialized = pickle.dumps(request)
        print(f"   序列化成功，大小: {len(serialized)} bytes")
        
        # 测试反序列化
        deserialized = pickle.loads(serialized)
        print(f"   反序列化成功: {deserialized}")
        return True
        
    except Exception as e:
        print(f"   序列化失败: {e}")
        return False

if __name__ == "__main__":
    success = test_request_serialization()
    if success:
        print("Request 序列化修复成功！")
    else:
        print("❌ 序列化问题仍未解决")