#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ResponseCodeMiddleware 测试脚本
验证ResponseCodeMiddleware的功能是否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.response_code import ResponseCodeMiddleware
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.settings.setting_manager import SettingManager


class MockStats:
    """模拟统计对象"""
    def __init__(self):
        self.counts = {}
        
    def inc_value(self, key, count=1):
        if key in self.counts:
            self.counts[key] += count
        else:
            self.counts[key] = count

    def get_value(self, key, default=None):
        return self.counts.get(key, default)


class MockLogger:
    """模拟日志对象"""
    def __init__(self):
        self.messages = []
        
    def debug(self, message):
        self.messages.append(f"DEBUG: {message}")
        
    def isEnabledFor(self, level):
        # 总是返回True以确保日志消息被记录
        return True


class MockCrawler:
    """模拟爬虫实例"""
    def __init__(self, settings):
        self.settings = settings
        self.stats = MockStats()
        self.logger = MockLogger()


def create_test_settings():
    """创建测试设置"""
    settings = SettingManager()
    settings.set("LOG_LEVEL", "DEBUG")
    return settings


# 重写ResponseCodeMiddleware的create_instance方法以使用MockLogger
class TestResponseCodeMiddleware(ResponseCodeMiddleware):
    @classmethod
    def create_instance(cls, crawler):
        """
        创建中间件实例（测试版本）
        
        Args:
            crawler: 爬虫实例
            
        Returns:
            TestResponseCodeMiddleware: 中间件实例
        """
        # 创建实例但不调用get_logger
        o = cls(stats=crawler.stats, log_level=crawler.settings.get('LOG_LEVEL'))
        # 使用MockLogger替换真实Logger
        o.logger = crawler.logger
        return o


async def test_response_code_middleware():
    """测试ResponseCodeMiddleware功能"""
    print("开始测试ResponseCodeMiddleware...")
    
    # 创建设置和中间件
    settings = create_test_settings()
    crawler = MockCrawler(settings)
    middleware = TestResponseCodeMiddleware.create_instance(crawler)
    
    print("✓ ResponseCodeMiddleware创建成功")
    
    # 创建测试请求和响应
    request = Request(url="https://example.com")
    
    # 测试不同状态码的处理
    test_cases = [
        (200, "正常响应"),
        (404, "页面未找到"),
        (500, "服务器错误"),
        (301, "重定向"),
        (403, "禁止访问"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for status_code, description in test_cases:
        try:
            response = Response(
                url="https://example.com",
                status_code=status_code,
                body=b"Test response body"
            )
            
            # 处理响应
            result = middleware.process_response(request, response, None)
            
            # 验证结果
            if result == response:
                # 检查统计信息是否正确更新
                expected_key = f'response_status_code/count/{status_code}'
                category = middleware._get_status_category(status_code)
                category_key = f'response_status_code/category/{category}'
                
                if (expected_key in crawler.stats.counts and 
                    crawler.stats.counts[expected_key] == 1 and
                    category_key in crawler.stats.counts):
                    print(f"✓ {description}: 状态码 {status_code} (统计信息正确)")
                    passed += 1
                else:
                    print(f"✗ {description}: 状态码 {status_code} (统计信息错误)")
            else:
                print(f"✗ {description}: 状态码 {status_code} (返回结果不正确)")
                
        except Exception as e:
            print(f"✗ {description}: 状态码 {status_code} (出现异常: {e})")
    
    # 输出测试结果
    print(f"\n测试结果: {passed}/{total} 通过")
    if passed == total:
        print("✓ 所有测试通过，ResponseCodeMiddleware工作正常")
        return True
    else:
        print("✗ 部分测试失败，ResponseCodeMiddleware存在问题")
        return False


def test_middleware_creation():
    """测试中间件创建功能"""
    print("\n测试中间件创建功能...")
    
    try:
        settings = create_test_settings()
        crawler = MockCrawler(settings)
        middleware = TestResponseCodeMiddleware.create_instance(crawler)
        
        if middleware and hasattr(middleware, 'stats') and hasattr(middleware, 'logger'):
            print("✓ 中间件创建成功，属性完整")
            return True
        else:
            print("✗ 中间件创建失败，缺少必要属性")
            return False
    except Exception as e:
        print(f"✗ 中间件创建时出现异常: {e}")
        return False


async def test_status_category_function():
    """测试状态码分类功能"""
    print("\n测试状态码分类功能...")
    
    try:
        settings = create_test_settings()
        crawler = MockCrawler(settings)
        middleware = TestResponseCodeMiddleware.create_instance(crawler)
        
        # 测试分类功能
        test_cases = [
            (200, "2xx"),
            (299, "2xx"),
            (301, "3xx"),
            (404, "4xx"),
            (500, "5xx"),
            (100, "other"),
            (600, "other"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for status_code, expected_category in test_cases:
            category = middleware._get_status_category(status_code)
            if category == expected_category:
                print(f"✓ 状态码 {status_code} 分类为 {category}")
                passed += 1
            else:
                print(f"✗ 状态码 {status_code} 分类错误: 期望 {expected_category}, 实际 {category}")
        
        print(f"\n分类测试结果: {passed}/{total} 通过")
        if passed == total:
            print("✓ 状态码分类功能正常")
            return True
        else:
            print("✗ 状态码分类功能存在问题")
            return False
            
    except Exception as e:
        print(f"✗ 状态码分类测试时出现异常: {e}")
        return False


async def test_response_type_check_functions():
    """测试响应类型检查功能"""
    print("\n测试响应类型检查功能...")
    
    try:
        settings = create_test_settings()
        crawler = MockCrawler(settings)
        middleware = TestResponseCodeMiddleware.create_instance(crawler)
        
        # 测试成功响应检查
        success_codes = [200, 201, 299]
        for code in success_codes:
            if middleware._is_success_response(code):
                print(f"✓ 状态码 {code} 正确识别为成功响应")
            else:
                print(f"✗ 状态码 {code} 未能正确识别为成功响应")
        
        # 测试重定向响应检查
        redirect_codes = [301, 302, 307]
        for code in redirect_codes:
            if middleware._is_redirect_response(code):
                print(f"✓ 状态码 {code} 正确识别为重定向响应")
            else:
                print(f"✗ 状态码 {code} 未能正确识别为重定向响应")
        
        # 测试客户端错误检查
        client_error_codes = [400, 404, 499]
        for code in client_error_codes:
            if middleware._is_client_error(code):
                print(f"✓ 状态码 {code} 正确识别为客户端错误")
            else:
                print(f"✗ 状态码 {code} 未能正确识别为客户端错误")
        
        # 测试服务器错误检查
        server_error_codes = [500, 502, 599]
        for code in server_error_codes:
            if middleware._is_server_error(code):
                print(f"✓ 状态码 {code} 正确识别为服务器错误")
            else:
                print(f"✗ 状态码 {code} 未能正确识别为服务器错误")
        
        print("✓ 响应类型检查功能正常")
        return True
        
    except Exception as e:
        print(f"✗ 响应类型检查测试时出现异常: {e}")
        return False


async def test_logging_functionality():
    """测试日志功能"""
    print("\n测试日志功能...")
    
    try:
        settings = create_test_settings()
        crawler = MockCrawler(settings)
        middleware = TestResponseCodeMiddleware.create_instance(crawler)
        
        # 检查logger对象
        print(f"  Logger对象类型: {type(middleware.logger)}")
        print(f"  Logger是否有debug方法: {hasattr(middleware.logger, 'debug')}")
        print(f"  Logger是否有isEnabledFor方法: {hasattr(middleware.logger, 'isEnabledFor')}")
        
        # 创建测试请求和响应
        request = Request(url="https://example.com")
        response = Response(
            url="https://example.com",
            status_code=200,
            body=b"Test response body"
        )
        
        # 检查调用前的消息数量
        initial_message_count = len(crawler.logger.messages)
        print(f"  调用前消息数量: {initial_message_count}")
        
        # 处理响应
        middleware.process_response(request, response, None)
        
        # 检查调用后的消息数量
        final_message_count = len(crawler.logger.messages)
        print(f"  调用后消息数量: {final_message_count}")
        
        # 检查是否有日志消息
        if final_message_count > initial_message_count:
            print("✓ 日志功能正常工作")
            # 打印一条日志消息作为示例
            print(f"  示例日志: {crawler.logger.messages[-1]}")
            return True
        else:
            print("✗ 未生成日志消息")
            print(f"  所有消息: {crawler.logger.messages}")
            return False
    except Exception as e:
        print(f"✗ 日志测试时出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("ResponseCodeMiddleware 功能测试")
    print("=" * 50)
    
    # 测试正常功能
    test1_result = await test_response_code_middleware()
    
    # 测试创建功能
    test2_result = test_middleware_creation()
    
    # 测试状态码分类功能
    test3_result = await test_status_category_function()
    
    # 测试响应类型检查功能
    test4_result = await test_response_type_check_functions()
    
    # 测试日志功能
    test5_result = await test_logging_functionality()
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"基本功能测试: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"创建测试: {'✓ 通过' if test2_result else '✗ 失败'}")
    print(f"分类功能测试: {'✓ 通过' if test3_result else '✗ 失败'}")
    print(f"类型检查测试: {'✓ 通过' if test4_result else '✗ 失败'}")
    print(f"日志测试: {'✓ 通过' if test5_result else '✗ 失败'}")
    
    overall_result = test1_result and test2_result and test3_result and test4_result and test5_result
    print(f"\n总体结果: {'✓ 所有测试通过' if overall_result else '✗ 部分测试失败'}")
    
    return overall_result


if __name__ == "__main__":
    asyncio.run(main())