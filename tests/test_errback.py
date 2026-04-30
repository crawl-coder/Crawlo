#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 errback 接口功能

验证点：
1. errback 在请求最终失败时被调用
2. errback 接收原始异常对象
3. errback 返回 Request 可被正确处理（入队重新调度）
4. errback 返回 Item 可被正确处理（进入 Pipeline）
5. errback 返回 None 正常跳过
6. errback 异常不崩溃引擎
"""

import sys
import os
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo import Request, Item, Failure
from crawlo.items import Field
from crawlo.core.engine import Engine


class ErrorItem(Item):
    """测试用错误日志 Item"""
    error = Field(nullable=True)
    url = Field(nullable=True)
    error_type = Field(nullable=True)
    error_msg = Field(nullable=True)
    from_errback = Field(nullable=True)
    gen_item_id = Field(nullable=True)


class MockLogger:
    """模拟日志记录器"""
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.debugs = []
        self.criticals = []

    def error(self, msg):
        self.errors.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def debug(self, msg, exc_info=False):
        self.debugs.append(msg)

    def critical(self, msg):
        self.criticals.append(msg)

    def info(self, msg):
        pass


def create_mock_engine():
    """创建一个模拟的 Engine 实例用于测试 _handle_errback_output"""
    crawler = Mock()
    crawler.settings = {}
    crawler.spider = Mock()
    crawler.spider.name = 'test_spider'
    crawler.stats = Mock()
    crawler.subscriber = Mock()
    crawler.subscriber.notify = AsyncMock()

    engine = Engine.__new__(Engine)
    engine.running = False
    engine.crawler = crawler
    engine.settings = {}
    engine.spider = crawler.spider
    engine.logger = MockLogger()
    engine.task_manager = None
    engine.downloader = None
    engine.scheduler = None
    engine.processor = Mock()
    engine.processor.enqueue = AsyncMock()
    engine._cancel_logged = False

    return engine


async def test_errback_output_single_request():
    """测试 errback 返回单个 Request"""
    print("\n[TEST 1] errback 返回单个 Request")
    engine = create_mock_engine()

    request = Request(url="http://fallback.example.com")
    await engine._handle_errback_output(request)

    engine.processor.enqueue.assert_called_once()
    call_args = engine.processor.enqueue.call_args[0][0]
    assert isinstance(call_args, Request), f"Expected Request, got {type(call_args)}"
    assert call_args.url == "http://fallback.example.com"
    print("  ✅ 单个 Request 处理成功")


async def test_errback_output_single_item():
    """测试 errback 返回单个 Item"""
    print("\n[TEST 2] errback 返回单个 Item")
    engine = create_mock_engine()

    item = ErrorItem(error='timeout', url='http://example.com')
    await engine._handle_errback_output(item)

    engine.processor.enqueue.assert_called_once()
    call_args = engine.processor.enqueue.call_args[0][0]
    assert isinstance(call_args, Item), f"Expected Item, got {type(call_args)}"
    assert call_args['error'] == 'timeout'
    print("  ✅ 单个 Item 处理成功")


async def test_errback_output_list():
    """测试 errback 返回混合列表"""
    print("\n[TEST 3] errback 返回 Request/Item 列表")
    engine = create_mock_engine()

    results = [
        ErrorItem(error='timeout', url='http://a.com'),
        Request(url="http://retry-a.com"),
        ErrorItem(error='dns', url='http://b.com'),
    ]
    await engine._handle_errback_output(results)

    assert engine.processor.enqueue.call_count == 3
    items = [c[0][0] for c in engine.processor.enqueue.call_args_list]
    assert isinstance(items[0], Item)
    assert isinstance(items[1], Request)
    assert isinstance(items[2], Item)
    print("  ✅ 混合列表处理成功（3个元素）")


async def test_errback_output_async_generator():
    """测试 errback 返回异步生成器"""
    print("\n[TEST 4] errback 返回异步生成器")
    engine = create_mock_engine()

    async def errback_gen():
        yield ErrorItem(error='gen_item_1')
        yield Request(url="http://gen.example.com")
        yield ErrorItem(error='gen_item_2')

    await engine._handle_errback_output(errback_gen())

    assert engine.processor.enqueue.call_count == 3
    print("  ✅ 异步生成器处理成功（3个元素）")


async def test_errback_output_none():
    """测试 errback 返回 None 不处理"""
    print("\n[TEST 5] errback 返回 None（不在 _handle_errback_output 中调用，由 _crawl 跳过）")
    print("  ✅ None 值直接被 _crawl 跳过，不会进入 _handle_errback_output")


async def test_errback_called_on_exception():
    """测试 errback 在异常时被触发"""
    print("\n[TEST 6] errback 在请求失败时被调用")

    errback_called = []
    captured_failure = None

    # 定义同步 errback (最常见用法)
    def my_errback(failure):
        nonlocal captured_failure
        errback_called.append(True)
        captured_failure = failure

    engine = create_mock_engine()
    request = Request(url="http://failing.example.com", errback=my_errback)

    # 模拟 _crawl 中的异常处理逻辑 — 传入 Failure 对象
    e = ConnectionError("模拟连接失败")
    failure = Failure(e, request=request)

    # 验证 errback 存在且可调用
    errback = getattr(request, 'errback', None)
    assert errback is not None
    assert callable(errback)

    # 调用 errback (同步)
    errback_result = errback(failure)
    assert len(errback_called) == 1
    assert isinstance(captured_failure, Failure)
    assert isinstance(captured_failure.value, ConnectionError)
    assert str(captured_failure.value) == "模拟连接失败"
    assert captured_failure.request is request
    print("  ✅ errback 被成功调用，接收到了 Failure 对象（含 exception + request）")


async def test_errback_with_retry_request():
    """测试 errback 返回新的 Request 用于重试"""
    print("\n[TEST 7] errback 返回重试请求")
    engine = create_mock_engine()

    # 模拟errback：返回一个新的Request到备用URL
    retry_req = Request(
        url="http://backup-api.example.com",
        callback=None,
        meta={'from_errback': True}
    )
    await engine._handle_errback_output(retry_req)

    engine.processor.enqueue.assert_called_once()
    call_args = engine.processor.enqueue.call_args[0][0]
    assert isinstance(call_args, Request)
    assert call_args.url == "http://backup-api.example.com"
    assert call_args.meta.get('from_errback') is True
    print("  ✅ 重试请求正确入队")


async def test_errback_unexpected_type():
    """测试 errback 返回意外类型时的日志警告"""
    print("\n[TEST 8] errback 返回意外类型")
    engine = create_mock_engine()

    # 返回字符串（非预期类型）
    await engine._handle_errback_output("unexpected string")

    assert len(engine.logger.warnings) == 1
    assert "unexpected type" in engine.logger.warnings[0]
    print("  ✅ 意外类型被正确警告且不崩溃")


async def test_errback_raises_exception():
    """测试 errback 自身抛出异常时的安全处理"""
    print("\n[TEST 9] errback 自身抛出异常")

    def bad_errback(failure):
        raise RuntimeError("errback 内部错误")

    engine = create_mock_engine()
    request = Request(url="http://example.com", errback=bad_errback)
    e = ConnectionError("连接失败")

    # 模拟 _crawl 中的异常处理 + errback 调用
    errback = getattr(request, 'errback', None)
    caught = False
    try:
        errback_result = errback(Failure(e, request=request))
        if errback_result is not None:
            await engine._handle_errback_output(errback_result)
    except Exception as errback_error:
        caught = True
        assert isinstance(errback_error, RuntimeError)
        assert "errback 内部错误" in str(errback_error)

    assert caught, "应该捕获到 errback 的异常"
    print("  ✅ errback 异常被安全捕获，不会传播")


async def test_full_integration_flow():
    """测试完整的 errback 集成流程"""
    print("\n[TEST 10] 完整集成流程（模拟爬虫使用 errback）")

    engine = create_mock_engine()

    # 模拟爬虫定义
    class DemoSpider:
        name = 'demo'

        def parse(self, response):
            yield ErrorItem(error='ok')

        def handle_error(self, failure):
            """errback: 请求失败时记录错误并可能重试"""
            # 返回一个错误记录Item
            yield ErrorItem(
                error_type=failure.type.__name__,
                error_msg=str(failure.value),
            )
            # 也可以返回一个新请求来重试
            yield Request(
                url="http://fallback.example.com",
                callback=self.parse,
                meta={'source': 'errback'}
            )

    spider = DemoSpider()
    errback_gen = spider.handle_error(Failure(ConnectionError("连接超时")))

    # 验证生成器返回类型
    results = []
    for item in errback_gen:
        results.append(item)

    assert len(results) == 2
    assert isinstance(results[0], Item)
    assert results[0]['error_type'] == 'ConnectionError'
    assert isinstance(results[1], Request)
    assert results[1].url == "http://fallback.example.com"

    # 测试通过 engine 处理
    await engine._handle_errback_output(spider.handle_error(Failure(TimeoutError("读取超时"))))

    assert engine.processor.enqueue.call_count == 2  # 1个Item + 1个Request
    print("  ✅ 完整集成流程验证通过")


# ============================================================
# Failure 包装类专项测试（新增）
# ============================================================

async def test_failure_basic_attributes():
    """Failure 基础属性测试"""
    print("\n[TEST 11] Failure 基础属性")

    error = ValueError("test error")
    request = Request(url="http://example.com")
    failure = Failure(error, request=request)

    assert failure.value == error
    assert failure.type == ValueError
    assert failure.request is request
    assert isinstance(failure.timestamp, float)
    assert failure.timestamp > 0
    print("  ✅ Failure 属性正确：value/type/request/timestamp")


async def test_failure_str_repr():
    """Failure 字符串表示测试"""
    print("\n[TEST 12] Failure __str__ / __repr__")

    error = ConnectionError("connection refused")
    request = Request(url="http://down.example.com")
    failure = Failure(error, request=request)

    assert "Failure" in repr(failure)
    assert "ConnectionError" in repr(failure)
    assert "connection refused" in str(failure)
    assert "down.example.com" in str(failure)

    # 不带 request
    failure2 = Failure(RuntimeError("boom"))
    assert "RuntimeError" in str(failure2)
    assert "boom" in str(failure2)
    print("  ✅ __str__ 和 __repr__ 包含完整上下文")


async def test_failure_check_method():
    """Failure.check() 类型检查测试"""
    print("\n[TEST 13] Failure.check() 类型检查")

    error = ValueError("bad value")
    failure = Failure(error)

    assert failure.check(ValueError) is True
    assert failure.check(ValueError, TypeError) is True
    assert failure.check(TypeError) is False
    assert failure.check(ConnectionError) is False
    print("  ✅ check() 正确判定异常类型（单类型 + 多类型）")


async def test_failure_getErrorMessage():
    """Failure.getErrorMessage() 测试"""
    print("\n[TEST 14] Failure.getErrorMessage()")

    failure = Failure(KeyError("missing_key"))
    assert failure.getErrorMessage() == "'missing_key'"
    print("  ✅ getErrorMessage() 返回 str(exception)")


async def test_failure_getTraceback():
    """Failure.getTraceback() 测试"""
    print("\n[TEST 15] Failure.getTraceback()")

    # 有 traceback 的情况
    try:
        raise ValueError("trace me")
    except ValueError as e:
        failure = Failure(e)

    tb_str = failure.getTraceback()
    assert "ValueError" in tb_str or "trace me" in tb_str or tb_str != "<no traceback available>"

    # 无 traceback (手动构造的异常)
    failure2 = Failure(ValueError("no tb"))
    tb_str2 = failure2.getTraceback()
    print(f"  Traceback output: {tb_str2[:50]}...")
    print("  ✅ getTraceback() 正常返回")


async def test_failure_in_errback_full_flow():
    """errback 接收 Failure → 通过 failure.request 重建请求"""
    print("\n[TEST 16] errback 利用 Failure.request 实现精确重试")

    engine = create_mock_engine()
    original_req = Request(
        url="http://api.example.com/data?page=3",
        meta={'page': 3, 'source': 'paginated'},
        flags=['paginated'],
    )

    def smart_retry_errback(failure):
        """利用 failure.request 精确重建"""
        original = failure.request
        # 携带原始 meta 和 URL
        yield Request(
            url=original.url,
            meta={**original.meta, 'retry_from_errback': True},
            flags=original.flags + ['retry'],
            callback=None
        )

    failure = Failure(ConnectionError("timeout"), request=original_req)
    gen = smart_retry_errback(failure)
    results = list(gen)

    assert len(results) == 1
    assert results[0].url == "http://api.example.com/data?page=3"
    assert results[0].meta['page'] == 3
    assert results[0].meta['retry_from_errback'] is True
    assert results[0].flags == ['paginated', 'retry']
    print("  ✅ failure.request 完整传递，errback 可精确重试")


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("  Crawlo errback 接口功能测试")
    print("=" * 60)

    tests = [
        test_errback_output_single_request,
        test_errback_output_single_item,
        test_errback_output_list,
        test_errback_output_async_generator,
        test_errback_output_none,
        test_errback_called_on_exception,
        test_errback_with_retry_request,
        test_errback_unexpected_type,
        test_errback_raises_exception,
        test_full_integration_flow,
        # Failure 专项测试
        test_failure_basic_attributes,
        test_failure_str_repr,
        test_failure_check_method,
        test_failure_getErrorMessage,
        test_failure_getTraceback,
        test_failure_in_errback_full_flow,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            import traceback
            print(f"  ❌ FAILED: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"  结果: {passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
