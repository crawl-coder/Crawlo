#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理模块兼容性测试
验证统一版 ErrorHandler 的功能
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.error_handler import ErrorHandler, error_handler, handle_exception


class TestErrorHandlerCompatibility(unittest.TestCase):
    """错误处理模块兼容性测试"""

    def setUp(self):
        """测试前准备"""
        self.error_handler = ErrorHandler("test_logger")
        # 禁用实际日志输出
        self.error_handler.logger.error = MagicMock()
        self.error_handler.logger.debug = MagicMock()

    def test_init(self):
        """测试初始化"""
        self.assertIsInstance(self.error_handler, ErrorHandler)
        self.assertEqual(self.error_handler.logger.name, "test_logger")

    def test_handle_error(self):
        """测试错误处理"""
        test_exception = ValueError("Test error")
        
        # 测试不抛出异常的情况
        try:
            self.error_handler.handle_error(test_exception, raise_error=False)
        except Exception:
            self.fail("handle_error should not raise exception when raise_error=False")
        
        # 验证处理器被调用（通过检查日志是否被调用）
        self.assertTrue(self.error_handler.logger.error.called)

    def test_safe_call(self):
        """测试安全调用"""
        def failing_function():
            raise RuntimeError("Function failed")
        
        # 测试函数失败时返回默认值
        result = self.error_handler.safe_call(failing_function, default_return="default")
        self.assertEqual(result, "default")
        
        # 测试正常函数
        def normal_function(x, y):
            return x + y
        
        result = self.error_handler.safe_call(normal_function, 1, 2, default_return=0)
        self.assertEqual(result, 3)

    def test_retry_on_failure(self):
        """测试失败重试装饰器"""
        call_count = 0
        
        @self.error_handler.retry_on_failure(max_retries=2, delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        # 第三次调用应该成功
        result = failing_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_handle_exception_decorator(self):
        """测试异常处理装饰器"""
        @handle_exception(context="Test function", raise_error=False)
        def decorated_function():
            raise ValueError("Decorated function error")
        
        # 调用装饰后的函数不应该抛出异常
        try:
            decorated_function()
        except Exception:
            self.fail("Decorated function should not raise exception when raise_error=False")

    def test_async_handle_exception_decorator(self):
        """测试异步异常处理装饰器"""
        import asyncio
        
        @handle_exception(context="Async test function", raise_error=False)
        async def async_decorated_function():
            raise ValueError("Async decorated function error")
        
        # 调用装饰后的异步函数不应该抛出异常
        async def test_async():
            try:
                await async_decorated_function()
            except Exception:
                self.fail("Async decorated function should not raise exception when raise_error=False")
        
        asyncio.run(test_async())


if __name__ == '__main__':
    unittest.main()