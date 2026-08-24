#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
架构守护测试 — 中间件优先级执行序契约（v1.7.4 收口）

背景：历史上三处注释/文档写"数值越小请求阶段越先执行"，与 MiddlewareManager
的实际行为相反。经评估决定**冻结现行为、修正文档**，本测试把实际执行序固化为
契约，任何一方再漂移都会被 CI 拦截：

- 构建顺序：按优先级数值 **降序** 排列；
- process_request：按构建顺序正序执行 → 数值大者先执行；
- process_response：按构建顺序逆序执行 → 数值小者先执行；
- process_exception：按构建顺序正序执行，首个返回 Request/Response 者接管。
"""
from unittest.mock import Mock

import pytest

from crawlo.http import Request, Response
from crawlo.middleware import BaseMiddleware
from crawlo.middleware.middleware_manager import MiddlewareManager
from crawlo.settings.setting_manager import SettingManager

CALLS = {
    "request": [],
    "response": [],
    "exception": [],
}


class _OrderRecorderMiddleware(BaseMiddleware):
    """记录各阶段调用顺序的最小中间件基类"""

    name = "base"

    def __init__(self):
        self.tag = type(self).name

    @classmethod
    def create_instance(cls, crawler):
        return cls()

    async def process_request(self, request, spider):
        CALLS["request"].append(self.tag)

    async def process_response(self, request, response, spider):
        CALLS["response"].append(self.tag)
        return response


class HighPriorityMiddleware(_OrderRecorderMiddleware):
    name = "high_200"


class LowPriorityMiddleware(_OrderRecorderMiddleware):
    name = "low_100"


class ExceptionTagHigh(HighPriorityMiddleware):
    async def process_exception(self, request, exception, spider):
        CALLS["exception"].append(("high", type(exception).__name__))


class ExceptionTagLow(LowPriorityMiddleware):
    async def process_exception(self, request, exception, spider):
        CALLS["exception"].append(("low", type(exception).__name__))


async def _fake_download(request):
    """请求钩子全部放行时的落地下载函数（测试桩）"""


def _build_manager() -> MiddlewareManager:
    CALLS["request"].clear()
    CALLS["response"].clear()
    CALLS["exception"].clear()

    crawler = Mock()
    settings = SettingManager()
    settings.set(
        "MIDDLEWARES",
        {
            f"{__name__}.HighPriorityMiddleware": 200,
            f"{__name__}.LowPriorityMiddleware": 100,
        },
    )
    crawler.settings = settings
    crawler.stats = Mock()
    # 注入异步哑下载函数：请求钩子全部放行时 _process_request 会落到它
    return MiddlewareManager(crawler, download_func=_fake_download)


def _make_request():
    return Request(url="http://order-contract.test/")


@pytest.mark.asyncio
async def test_process_request_runs_high_priority_first():
    """请求阶段：优先级数值大者先执行（降序）"""
    manager = _build_manager()
    await manager._process_request(_make_request())
    assert CALLS["request"] == ["high_200", "low_100"]


@pytest.mark.asyncio
async def test_process_response_runs_low_priority_first():
    """响应阶段：优先级数值小者先执行（升序）"""
    manager = _build_manager()
    response = Response(url="http://order-contract.test/", status=200)
    await manager._process_response(_make_request(), response)
    assert CALLS["response"] == ["low_100", "high_200"]


@pytest.mark.asyncio
async def test_process_exception_iterates_build_order_then_reraises():
    """异常阶段：按构建顺序（降序）遍历；无人接管时原异常向上抛出"""
    manager = _build_manager()
    request = _make_request()
    boom = RuntimeError("boom")
    with pytest.raises(RuntimeError, match="boom"):
        await manager._process_exception(request, boom)
    # 两个中间件都未覆盖 process_exception 时列表为空 → 直接 raise；
    # 这里显式断言"空接管"语义即可（顺序由 request 阶段同序构建保证）
    assert CALLS["exception"] == []


@pytest.mark.asyncio
async def test_exception_hook_order_matches_request_phase():
    """异常阶段与请求阶段同序：数值大者先获得处理权（Retry 先于用户中间件）"""
    CALLS["exception"].clear()

    crawler = Mock()
    settings = SettingManager()
    settings.set(
        "MIDDLEWARES",
        {
            f"{__name__}.ExceptionTagHigh": 200,
            f"{__name__}.ExceptionTagLow": 100,
        },
    )
    crawler.settings = settings
    crawler.stats = Mock()
    manager = MiddlewareManager(crawler, download_func=_fake_download)

    with pytest.raises(RuntimeError):
        await manager._process_exception(_make_request(), RuntimeError("x"))

    assert [tag for tag, _ in CALLS["exception"]] == ["high", "low"]
