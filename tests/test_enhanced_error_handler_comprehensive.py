#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强错误处理工具综合测试
测试 ErrorContext, DetailedException, ErrorHandler 的更多功能
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import traceback

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.error_handler import (
    ErrorHandler, 
    ErrorContext, 
    DetailedException, 
    handle_exception
)


class TestErrorContext(unittest.TestCase):
    """错误上下文测试"""

    def test_error_context_initialization(self):
        """测试错误上下文初始化"""
        context = ErrorContext(
            context="测试上下文",
            module="test_module",
            function="test_function"
        )
        
        self.assertEqual(context.context, "测试上下文")
        self.assertEqual(context.module, "test_module")
        self.assertEqual(context.function, "test_function")
        self.assertIsNotNone(context.timestamp)
        
    def test_error_context_string_representation(self):
        """测试错误上下文字符串表示"""
        context = ErrorContext(
            context="测试上下文",
            module="test_module",
            function="test_function"
        )
        
        context_str = str(context)
        self.assertIn("Module: test_module", context_str)
        self.assertIn("Function: test_function", context_str)
        self.assertIn("Context: 测试上下文", context_str)
        self.assertIn("Time:", context_str)


class TestDetailedException(unittest.TestCase):
    """详细异常测试"""

    def test_detailed_exception_initialization(self):
        """测试详细异常初始化"""
        context = ErrorContext(context="测试上下文")
        
        exception = DetailedException(
            message="测试异常消息",
            context=context,
            error_code="TEST_001",
            detail1="详细信息1",
            detail2="详细信息2"
        )
        
        self.assertIn("测试异常消息", str(exception))
        self.assertEqual(exception.context, context)
        self.assertEqual(exception.error_code, "TEST_001")
        self.assertEqual(exception.details["detail1"], "详细信息1")
        self.assertEqual(exception.details["detail2"], "详细信息2")
        self.assertIsNotNone(exception.timestamp)
        
    def test_detailed_exception_without_context(self):
        """测试没有上下文的详细异常"""
        exception = DetailedException(
            message="测试异常消息",
            error_code="TEST_002"
        )
        
        self.assertEqual(str(exception), "测试异常消息")
        self.assertIsNone(exception.context)
        self.assertEqual(exception.error_code, "TEST_002")
        self.assertIsNotNone(exception.timestamp)
        
    def test_detailed_exception_string_with_context(self):
        """测试带上下文的详细异常字符串表示"""
        context = ErrorContext(context="测试上下文")
        exception = DetailedException(
            message="测试异常消息",
            context=context
        )
        
        exception_str = str(exception)
        self.assertIn("测试异常消息", exception_str)
        self.assertIn("测试上下文", exception_str)
        
    def test_get_full_details(self):
        """测试获取完整详情"""
        context = ErrorContext(context="测试上下文")
        exception = DetailedException(
            message="测试异常消息",
            context=context,
            error_code="TEST_003",
            detail1="详细信息1"
        )
        
        details = exception.get_full_details()
        self.assertIn("测试异常消息", details["message"])
        self.assertEqual(details["error_code"], "TEST_003")
        self.assertIn("测试上下文", details["context"])
        self.assertEqual(details["details"]["detail1"], "详细信息1")
        self.assertEqual(details["exception_type"], "DetailedException")


class TestErrorHandler(unittest.TestCase):
    """统一错误处理器测试"""

    def setUp(self):
        """测试前准备"""
        self.handler = ErrorHandler("test_logger", "ERROR")
        
    def test_handler_initialization(self):
        """测试处理器初始化"""
        self.assertEqual(len(self.handler.error_history), 0)
        self.assertEqual(self.handler.max_history_size, 100)
        
    def test_handle_error_without_raising(self):
        """测试不抛出异常的错误处理"""
        try:
            raise ValueError("测试错误")
        except Exception as e:
            # 处理错误但不重新抛出
            error_details = self.handler.handle_error(e, raise_error=False, log_error=False)
            
            # 验证返回的错误详情
            self.assertIsInstance(error_details, dict)
            self.assertEqual(error_details["exception_type"], "ValueError")
            self.assertEqual(error_details["message"], "测试错误")
            
    def test_safe_call_success(self):
        """测试安全调用成功"""
        def normal_function(x, y):
            return x + y
            
        result = self.handler.safe_call(normal_function, 1, 2, default_return=0)
        self.assertEqual(result, 3)
        
    def test_safe_call_with_exception(self):
        """测试安全调用异常"""
        def failing_function():
            raise RuntimeError("函数执行失败")
            
        result = self.handler.safe_call(failing_function, default_return="默认值")
        self.assertEqual(result, "默认值")
        
    def test_get_and_clear_error_history(self):
        """测试获取和清空错误历史"""
        # 产生一些错误
        try:
            raise ValueError("错误1")
        except Exception as e:
            self.handler.handle_error(e, raise_error=False, log_error=False)
            
        try:
            raise RuntimeError("错误2")
        except Exception as e:
            self.handler.handle_error(e, raise_error=False, log_error=False)
            
        # 检查历史记录
        history = self.handler.get_error_history()
        self.assertEqual(len(history), 2)
        
        # 清空历史记录
        self.handler.clear_error_history()
        history = self.handler.get_error_history()
        self.assertEqual(len(history), 0)
        
    def test_error_history_size_limit(self):
        """测试错误历史大小限制"""
        # 产生超过100个错误
        for i in range(110):
            try:
                raise ValueError(f"错误{i}")
            except Exception as e:
                self.handler.handle_error(e, raise_error=False, log_error=False)
                
        # 检查历史记录大小限制
        history = self.handler.get_error_history()
        self.assertEqual(len(history), 100)  # 应该限制在100个


class TestHandleExceptionDecorator(unittest.TestCase):
    """异常处理装饰器测试"""

    def test_handle_exception_decorator_sync(self):
        """测试同步函数的异常处理装饰器"""
        @handle_exception(context="测试装饰器", module="test_module", raise_error=False)
        def failing_function():
            raise ValueError("装饰器测试错误")
            
        # 调用应该捕获异常但不抛出
        try:
            result = failing_function()
            self.assertIsNone(result)  # 默认返回None
        except Exception:
            self.fail("异常应该被捕获")
            
    def test_handle_exception_decorator_async(self):
        """测试异步函数的异常处理装饰器"""
        @handle_exception(context="异步测试装饰器", module="test_module", raise_error=False)
        async def async_failing_function():
            raise RuntimeError("异步装饰器测试错误")
            
        # 异步调用
        async def test_async():
            try:
                result = await async_failing_function()
                self.assertIsNone(result)  # 默认返回None
            except Exception:
                self.fail("异常应该被捕获")
                
        # 使用事件循环运行异步函数
        asyncio.run(test_async())
        
    def test_handle_exception_decorator_with_detailed_exception(self):
        """测试装饰器处理详细异常"""
        @handle_exception(context="详细异常测试", module="test_module", raise_error=False)
        def function_with_detailed_exception():
            context = ErrorContext(context="函数内部上下文")
            raise DetailedException("详细异常消息", context=context, error_code="DETAIL_001")
            
        # 调用应该捕获异常
        try:
            result = function_with_detailed_exception()
            self.assertIsNone(result)
        except Exception:
            self.fail("详细异常应该被捕获")


if __name__ == '__main__':
    unittest.main()