#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
RetryMiddleware 优先级调整符号语义回归测试（v1.7.4 收口追加）

背景：历史上 `_retry` 对"已取反的内部值"做 `+ retry_priority` 加法，
导致默认 RETRY_PRIORITY=-100 实际把 NORMAL 重试升级为等效 HIGH——
与注释/文档"负数降低优先级"相反。修复后对内部值做减法（= 对用户值加）。

约定（与 crawlo.http.request.RequestPriority 一致）：
- 用户优先级：正值更高；内部存储 = -用户值；
- RETRY_PRIORITY 作用于用户标度：负数 = 降低重试优先级；
- 已知限制：重试默认由 MiddlewareManager 内存递归重新下载、不重新入队，
  该值仅在副本被再次调度时被队列消费。
"""
from unittest.mock import Mock

from crawlo.http.request import Request
from crawlo.middleware.retry import RetryMiddleware


def _make_middleware(retry_priority: int) -> RetryMiddleware:
    return RetryMiddleware(
        retry_http_codes=[500, 502],
        ignore_http_codes=[],
        max_retry_times=3,
        retry_exceptions=[],
        stats=Mock(),
        retry_priority=retry_priority,
    )


def _retry_once(request: Request, retry_priority: int) -> Request:
    spider = Mock(_closing=False)
    mw = _make_middleware(retry_priority)
    copy = mw._retry(request, "503", spider)
    assert copy is not None, "可重试异常必须产出重试副本"
    return copy


def test_negative_adjustment_lowers_user_priority():
    """默认 -100：NORMAL(0) 重试后等效用户优先级应降为 -100（LOW 档方向）"""
    request = Request(url="http://t/1", priority=0)
    copy = _retry_once(request, -100)
    # 内部存储为取反值：用户 -100 ⇔ internal +100
    assert copy.priority == 100
    assert -copy.priority == -100


def test_positive_adjustment_raises_user_priority():
    """正值调整 = 提升重试优先级"""
    request = Request(url="http://t/2", priority=0)
    copy = _retry_once(request, 50)
    assert copy.priority == -50
    assert -copy.priority == 50


def test_high_request_with_default_drops_to_normal():
    """HIGH(100) 请求按默认 -100 调整后回到 NORMAL 档"""
    request = Request(url="http://t/3", priority=100)
    copy = _retry_once(request, -100)
    assert -copy.priority == 0


def test_original_request_priority_untouched():
    """副本调整不得污染原请求的优先级"""
    request = Request(url="http://t/4", priority=0)
    original_internal = request.priority
    _retry_once(request, -100)
    assert request.priority == original_internal


def test_copy_preserves_sign_through_double_negation():
    """copy() 的双重取反对不同初始档位都保持语义"""
    for user_prio in (200, 100, 0, -100, -200):
        request = Request(url="http://t/5", priority=user_prio)
        copy = request.copy()
        assert copy.priority == request.priority, f"user={user_prio} 时副本 internal 不一致"
        assert -copy.priority == user_prio
