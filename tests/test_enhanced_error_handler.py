#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版错误处理工具测试
"""
import sys
import os
import asyncio
import traceback

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.enhanced_error_handler import EnhancedErrorHandler, ErrorContext, DetailedException, handle_exception


def test_basic_error_handling():
    """测试基本错误处理"""
    print("🔍 1. 测试基本错误处理...")
    
    try:
        handler = EnhancedErrorHandler("test_logger")
        
        # 测试同步函数错误处理
        def failing_function():
            raise ValueError("测试错误")
        
        context = ErrorContext(context="测试同步函数", module="test_module", function="failing_function")
        
        try:
            handler.safe_call(failing_function, context=context)
            print("   ✅ 同步函数错误处理成功")
        except Exception as e:
            print(f"   ❌ 同步函数错误处理失败: {e}")
            return False
            
        # 测试普通函数的错误处理（不是异步函数）
        def normal_function():
            return "正常返回值"
        
        context = ErrorContext(context="测试普通函数", module="test_module", function="normal_function")
        
        result = handler.safe_call(normal_function, context=context)
        if result == "正常返回值":
            print("   ✅ 普通函数处理成功")
        else:
            print("   ❌ 普通函数处理失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ 基本错误处理测试失败: {e}")
        traceback.print_exc()
        return False


def test_detailed_exception():
    """测试详细异常"""
    print("🔍 2. 测试详细异常...")
    
    try:
        # 创建错误上下文
        context = ErrorContext(
            context="数据库连接失败",
            module="database_module",
            function="connect_to_db"
        )
        
        # 创建详细异常
        exception = DetailedException(
            "无法连接到数据库",
            context=context,
            error_code="DB_CONN_001",
            host="localhost",
            port=5432,
            database="test_db"
        )
        
        # 验证异常信息
        assert "无法连接到数据库" in str(exception)
        assert "数据库连接失败" in str(exception)
        
        # 获取完整详情
        details = exception.get_full_details()
        assert details["error_code"] == "DB_CONN_001"
        assert details["exception_type"] == "DetailedException"
        
        print("   ✅ 详细异常测试成功")
        return True
        
    except Exception as e:
        print(f"   ❌ 详细异常测试失败: {e}")
        traceback.print_exc()
        return False


async def test_retry_decorator():
    """测试重试装饰器"""
    print("🔍 3. 测试重试装饰器...")
    
    try:
        handler = EnhancedErrorHandler("test_retry_logger")
        
        # 测试同步函数重试
        attempt_count = 0
        
        @handler.retry_on_failure(max_retries=2, delay=0.1)
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError(f"尝试 {attempt_count} 失败")
            return "成功"
        
        # 第一次调用应该成功（第3次尝试）
        result = failing_function()
        assert result == "成功"
        assert attempt_count == 3
        
        print("   ✅ 同步函数重试测试成功")
        
        # 测试异步函数重试
        async_attempt_count = 0
        
        @handler.retry_on_failure(max_retries=2, delay=0.1)
        async def async_failing_function():
            nonlocal async_attempt_count
            async_attempt_count += 1
            if async_attempt_count < 3:
                raise RuntimeError(f"异步尝试 {async_attempt_count} 失败")
            return "异步成功"
        
        # 异步调用
        result = await async_failing_function()
        assert result == "异步成功"
        assert async_attempt_count == 3
        
        print("   ✅ 异步函数重试测试成功")
        return True
        
    except Exception as e:
        print(f"   ❌ 重试装饰器测试失败: {e}")
        traceback.print_exc()
        return False


async def test_exception_decorator():
    """测试异常装饰器"""
    print("🔍 4. 测试异常装饰器...")
    
    try:
        # 测试同步函数装饰器
        @handle_exception(context="测试装饰器", module="test_module", function="decorated_function", raise_error=False)
        def decorated_function():
            raise ValueError("装饰器测试错误")
        
        # 调用应该捕获异常但不抛出
        try:
            decorated_function()
            print("   ✅ 同步函数装饰器测试成功")
        except Exception:
            print("   ❌ 同步函数装饰器测试失败：异常未被捕获")
            return False
            
        # 测试异步函数装饰器
        @handle_exception(context="异步测试装饰器", module="test_module", function="async_decorated_function", raise_error=False)
        async def async_decorated_function():
            raise RuntimeError("异步装饰器测试错误")
        
        # 异步调用
        try:
            await async_decorated_function()
            print("   ✅ 异步函数装饰器测试成功")
        except Exception:
            print("   ❌ 异步函数装饰器测试失败：异常未被捕获")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ 异常装饰器测试失败: {e}")
        traceback.print_exc()
        return False


def test_error_history():
    """测试错误历史记录"""
    print("🔍 5. 测试错误历史记录...")
    
    try:
        handler = EnhancedErrorHandler("history_test_logger")
        
        # 产生一些错误
        def error_function():
            raise ValueError("历史记录测试错误")
        
        context = ErrorContext(context="测试历史记录", module="history_module")
        
        # 记录几个错误
        for i in range(3):
            try:
                handler.safe_call(error_function, context=context)
            except:
                pass  # 忽略异常
        
        # 检查历史记录
        history = handler.get_error_history()
        assert len(history) == 3
        
        # 检查历史记录内容
        for record in history:
            assert "历史记录测试错误" in record["message"]
            assert record["exception_type"] == "ValueError"
        
        print("   ✅ 错误历史记录测试成功")
        return True
        
    except Exception as e:
        print(f"   ❌ 错误历史记录测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 开始增强版错误处理工具测试...")
    print("=" * 50)
    
    tests = [
        test_basic_error_handling,
        test_detailed_exception,
        test_retry_decorator,
        test_exception_decorator,
        test_error_history
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
                print(f"✅ {test_func.__name__} 通过")
            else:
                print(f"❌ {test_func.__name__} 失败")
        except Exception as e:
            print(f"❌ {test_func.__name__} 异常: {e}")
            traceback.print_exc()
        print()
    
    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！增强版错误处理工具工作正常")
        return 0
    else:
        print("❌ 部分测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)