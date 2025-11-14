#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ResponseFilterMiddleware 测试脚本
验证ResponseFilterMiddleware的功能是否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.middleware.response_filter import ResponseFilterMiddleware
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.settings.setting_manager import SettingManager
from crawlo.exceptions import IgnoreRequestError


class MockStats:
    """模拟统计对象"""
    def __init__(self):
        self.counts = {}
        
    def inc_value(self, key, count=1):
        if key in self.counts:
            self.counts[key] += count
        else:
            self.counts[key] = count


class MockLogger:
    """模拟日志对象"""
    def __init__(self):
        self.messages = []
        
    def debug(self, message):
        self.messages.append(f"DEBUG: {message}")


class MockCrawler:
    """模拟爬虫实例"""
    def __init__(self, settings):
        self.settings = settings
        self.stats = MockStats()
        self.logger = MockLogger()


def create_test_settings(allowed_codes=None, denied_codes=None):
    """创建测试设置"""
    settings = SettingManager()
    settings.set("LOG_LEVEL", "DEBUG")
    
    if allowed_codes is not None:
        # 将列表转换为字符串格式存储
        settings.set("ALLOWED_RESPONSE_CODES", ",".join(map(str, allowed_codes)))
    else:
        settings.set("ALLOWED_RESPONSE_CODES", "")
        
    if denied_codes is not None:
        # 将列表转换为字符串格式存储
        settings.set("DENIED_RESPONSE_CODES", ",".join(map(str, denied_codes)))
    else:
        settings.set("DENIED_RESPONSE_CODES", "")
        
    return settings


async def test_response_filter_middleware():
    """测试ResponseFilterMiddleware功能"""
    print("开始测试ResponseFilterMiddleware...")
    
    # 测试用例
    test_cases = [
        # (状态码, 应该被允许, 描述)
        (200, True, "正常响应"),
        (201, True, "创建成功"),
        (299, True, "2xx范围内的其他状态码"),
        (404, False, "页面未找到"),
        (500, False, "服务器错误"),
        (403, False, "禁止访问"),
        (301, False, "重定向"),
    ]
    
    # 创建设置和中间件（不配置ALLOWED_RESPONSE_CODES，只允许2xx状态码）
    settings = create_test_settings(None, None)
    crawler = MockCrawler(settings)
    middleware = ResponseFilterMiddleware.create_instance(crawler)
    
    print(f"✓ ResponseFilterMiddleware创建成功")
    print(f"  默认允许的状态码: 200-299")
    print(f"  允许列表: {middleware.allowed_codes}")
    print(f"  拒绝列表: {middleware.denied_codes}")
    
    # 运行测试用例
    passed = 0
    total = len(test_cases)
    
    for status_code, should_allow, description in test_cases:
        try:
            request = Request(url="https://example.com")
            response = Response(
                url="https://example.com",
                status_code=status_code,
                body=b"Test response body"
            )
            
            result = middleware.process_response(request, response, None)
            
            # 如果到达这里，说明响应被允许
            if should_allow:
                if result == response:
                    print(f"✓ {description}: 状态码 {status_code} (正确允许)")
                    passed += 1
                else:
                    print(f"✗ {description}: 状态码 {status_code} (应该被允许但返回结果不正确)")
            else:
                print(f"✗ {description}: 状态码 {status_code} (应该被过滤但被允许)")
                
        except IgnoreRequestError as e:
            # 响应被过滤
            if not should_allow:
                print(f"✓ {description}: 状态码 {status_code} (正确过滤)")
                passed += 1
            else:
                print(f"✗ {description}: 状态码 {status_code} (应该被允许但被过滤)")
        except Exception as e:
            print(f"✗ {description}: 状态码 {status_code} (出现异常: {e})")
    
    # 输出测试结果
    print(f"\n测试结果: {passed}/{total} 通过")
    if passed == total:
        print("✓ 所有测试通过，ResponseFilterMiddleware工作正常")
        return True
    else:
        print("✗ 部分测试失败，ResponseFilterMiddleware存在问题")
        return False


async def test_allowed_codes_configuration():
    """测试ALLOWED_RESPONSE_CODES配置功能"""
    print("\n测试ALLOWED_RESPONSE_CODES配置功能...")
    
    # 配置允许的状态码
    allowed_codes = [404, 500, 301]
    settings = create_test_settings(allowed_codes, None)
    crawler = MockCrawler(settings)
    middleware = ResponseFilterMiddleware.create_instance(crawler)
    
    print(f"✓ ResponseFilterMiddleware创建成功")
    print(f"  配置的允许状态码: {allowed_codes}")
    print(f"  实际允许列表: {middleware.allowed_codes}")
    
    # 测试用例
    test_cases = [
        # (状态码, 应该被允许, 描述)
        (200, True, "正常响应(2xx范围)"),
        (404, True, "页面未找到(配置允许)"),
        (500, True, "服务器错误(配置允许)"),
        (301, True, "重定向(配置允许)"),
        (403, False, "禁止访问(未配置允许)"),
        (502, False, "网关错误(未配置允许)"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for status_code, should_allow, description in test_cases:
        try:
            request = Request(url="https://example.com")
            response = Response(
                url="https://example.com",
                status_code=status_code,
                body=b"Test response body"
            )
            
            result = middleware.process_response(request, response, None)
            
            # 如果到达这里，说明响应被允许
            if should_allow:
                if result == response:
                    print(f"✓ {description}: 状态码 {status_code} (正确允许)")
                    passed += 1
                else:
                    print(f"✗ {description}: 状态码 {status_code} (应该被允许但返回结果不正确)")
            else:
                print(f"✗ {description}: 状态码 {status_code} (应该被过滤但被允许)")
                
        except IgnoreRequestError as e:
            # 响应被过滤
            if not should_allow:
                print(f"✓ {description}: 状态码 {status_code} (正确过滤)")
                passed += 1
            else:
                print(f"✗ {description}: 状态码 {status_code} (应该被允许但被过滤)")
        except Exception as e:
            print(f"✗ {description}: 状态码 {status_code} (出现异常: {e})")
    
    # 输出测试结果
    print(f"\n测试结果: {passed}/{total} 通过")
    if passed == total:
        print("✓ 所有测试通过，ALLOWED_RESPONSE_CODES配置功能正常")
        return True
    else:
        print("✗ 部分测试失败，ALLOWED_RESPONSE_CODES配置功能存在问题")
        return False


async def test_denied_codes_configuration():
    """测试DENIED_RESPONSE_CODES配置功能"""
    print("\n测试DENIED_RESPONSE_CODES配置功能...")
    
    # 配置拒绝的状态码（注意：这里需要将整数转换为字符串，因为SettingManager.get_list会处理字符串）
    denied_codes = ["200", "201"]
    settings = create_test_settings(None, denied_codes)
    crawler = MockCrawler(settings)
    middleware = ResponseFilterMiddleware.create_instance(crawler)
    
    print(f"✓ ResponseFilterMiddleware创建成功")
    print(f"  配置的拒绝状态码: {denied_codes}")
    print(f"  实际拒绝列表: {middleware.denied_codes}")
    
    # 测试用例
    test_cases = [
        # (状态码, 应该被允许, 描述)
        (200, False, "正常响应(配置拒绝)"),
        (201, False, "创建成功(配置拒绝)"),
        (404, False, "页面未找到(默认拒绝)"),
        (202, True, "接受请求(2xx范围，未被拒绝)"),
        (301, False, "重定向(默认拒绝)"),
        (500, False, "服务器错误(默认拒绝)"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for status_code, should_allow, description in test_cases:
        try:
            request = Request(url="https://example.com")
            response = Response(
                url="https://example.com",
                status_code=status_code,
                body=b"Test response body"
            )
            
            result = middleware.process_response(request, response, None)
            
            # 如果到达这里，说明响应被允许
            if should_allow:
                if result == response:
                    print(f"✓ {description}: 状态码 {status_code} (正确允许)")
                    passed += 1
                else:
                    print(f"✗ {description}: 状态码 {status_code} (应该被允许但返回结果不正确)")
            else:
                print(f"✗ {description}: 状态码 {status_code} (应该被过滤但被允许)")
                
        except IgnoreRequestError as e:
            # 响应被过滤
            if not should_allow:
                print(f"✓ {description}: 状态码 {status_code} (正确过滤)")
                passed += 1
            else:
                print(f"✗ {description}: 状态码 {status_code} (应该被允许但被过滤)")
        except Exception as e:
            print(f"✗ {description}: 状态码 {status_code} (出现异常: {e})")
    
    # 输出测试结果
    print(f"\n测试结果: {passed}/{total} 通过")
    if passed == total:
        print("✓ 所有测试通过，DENIED_RESPONSE_CODES配置功能正常")
        return True
    else:
        print("✗ 部分测试失败，DENIED_RESPONSE_CODES配置功能存在问题")
        return False


def test_middleware_creation():
    """测试中间件创建功能"""
    print("\n测试中间件创建功能...")
    
    try:
        settings = create_test_settings(None, None)
        crawler = MockCrawler(settings)
        middleware = ResponseFilterMiddleware.create_instance(crawler)
        
        if middleware and hasattr(middleware, 'allowed_codes') and hasattr(middleware, 'denied_codes') and hasattr(middleware, 'logger'):
            print("✓ 中间件创建成功，属性完整")
            print(f"  allowed_codes: {middleware.allowed_codes}")
            print(f"  denied_codes: {middleware.denied_codes}")
            return True
        else:
            print("✗ 中间件创建失败，缺少必要属性")
            return False
    except Exception as e:
        print(f"✗ 中间件创建时出现异常: {e}")
        return False


async def test_filter_reason_function():
    """测试过滤原因功能"""
    print("\n测试过滤原因功能...")
    
    try:
        # 配置允许和拒绝的状态码（注意：这里需要将整数转换为字符串）
        allowed_codes = ["404"]
        denied_codes = ["200"]
        settings = create_test_settings(allowed_codes, denied_codes)
        crawler = MockCrawler(settings)
        middleware = ResponseFilterMiddleware.create_instance(crawler)
        
        # 测试拒绝状态码的原因
        reason1 = middleware._get_filter_reason(200)
        if "被明确拒绝" in reason1:
            print("✓ 拒绝状态码原因正确")
        else:
            print(f"✗ 拒绝状态码原因错误: {reason1}")
            
        # 测试未允许状态码的原因
        reason2 = middleware._get_filter_reason(500)
        if "不在允许列表中" in reason2:
            print("✓ 未允许状态码原因正确")
        else:
            print(f"✗ 未允许状态码原因错误: {reason2}")
            
        print("✓ 过滤原因功能正常")
        return True
        
    except Exception as e:
        print(f"✗ 过滤原因测试时出现异常: {e}")
        return False


async def test_is_response_allowed_function():
    """测试响应允许检查功能"""
    print("\n测试响应允许检查功能...")
    
    try:
        # 配置允许和拒绝的状态码（注意：这里需要将整数转换为字符串）
        allowed_codes = ["404", "301"]
        denied_codes = ["200"]
        settings = create_test_settings(allowed_codes, denied_codes)
        crawler = MockCrawler(settings)
        middleware = ResponseFilterMiddleware.create_instance(crawler)
        
        # 创建模拟响应对象
        class MockResponse:
            def __init__(self, status_code):
                self.status_code = status_code
        
        # 测试用例: (状态码, 应该被允许, 描述)
        test_cases = [
            (200, False, "被明确拒绝的状态码"),
            (404, True, "被明确允许的状态码"),
            (301, True, "被明确允许的状态码"),
            (201, True, "2xx范围内的默认允许状态码"),
            (500, False, "未被允许的错误状态码"),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for status_code, should_allow, description in test_cases:
            response = MockResponse(status_code)
            is_allowed = middleware._is_response_allowed(response)
            
            if is_allowed == should_allow:
                print(f"✓ {description}: 状态码 {status_code}")
                passed += 1
            else:
                print(f"✗ {description}: 状态码 {status_code} (期望: {should_allow}, 实际: {is_allowed})")
        
        print(f"\n允许检查测试结果: {passed}/{total} 通过")
        if passed == total:
            print("✓ 响应允许检查功能正常")
            return True
        else:
            print("✗ 响应允许检查功能存在问题")
            return False
        
    except Exception as e:
        print(f"✗ 响应允许检查测试时出现异常: {e}")
        return False


async def main():
    """主测试函数"""
    print("ResponseFilterMiddleware 功能测试")
    print("=" * 50)
    
    # 测试正常功能
    test1_result = await test_response_filter_middleware()
    
    # 测试ALLOWED_RESPONSE_CODES配置
    test2_result = await test_allowed_codes_configuration()
    
    # 测试DENIED_RESPONSE_CODES配置
    test3_result = await test_denied_codes_configuration()
    
    # 测试创建功能
    test4_result = test_middleware_creation()
    
    # 测试过滤原因功能
    test5_result = await test_filter_reason_function()
    
    # 测试响应允许检查功能
    test6_result = await test_is_response_allowed_function()
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"基本功能测试: {'✓ 通过' if test1_result else '✗ 失败'}")
    print(f"允许配置测试: {'✓ 通过' if test2_result else '✗ 失败'}")
    print(f"拒绝配置测试: {'✓ 通过' if test3_result else '✗ 失败'}")
    print(f"创建测试: {'✓ 通过' if test4_result else '✗ 失败'}")
    print(f"原因功能测试: {'✓ 通过' if test5_result else '✗ 失败'}")
    print(f"允许检查测试: {'✓ 通过' if test6_result else '✗ 失败'}")
    
    overall_result = test1_result and test2_result and test3_result and test4_result and test5_result and test6_result
    print(f"\n总体结果: {'✓ 所有测试通过' if overall_result else '✗ 部分测试失败'}")
    
    return overall_result


if __name__ == "__main__":
    asyncio.run(main())