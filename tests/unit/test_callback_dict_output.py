#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P0 回归测试：Spider 回调直接返回 / yield dict 不再丢数据
==========================================================

背景缺陷：
- ``async def parse: return {...}`` 曾被静默丢弃（仅 WARNING）；
- ``def parse: return {...}`` 同样被丢弃；
- ``yield {...}`` 会在 ``_handle_spider_output`` 抛 OutputError。

修复语义：在产出边界（``process_callback_output`` / ``_handle_errback_output``）
把 dict 统一包装为 ``Item``（字段内容不变），``Request`` / ``Item`` 原样透传；
引擎边界 ``_handle_spider_output`` 保持严格的 ``Request | Item`` 契约。
"""

import asyncio
import logging

import pytest

from crawlo import Item, Request
from crawlo.core.engine_generation import RequestGenerationMixin
from crawlo.core.engine_helpers import process_callback_output
from crawlo.core.errors import OutputError
from crawlo.http.response import Response


class _Spider:
    name = "test_spider"

    async def parse_async_return_dict(self, response):
        return {"url": response.url}

    def parse_sync_return_dict(self, response):
        return {"url": response.url}

    async def parse_async_return_item(self, response):
        return Item(url=response.url)

    async def parse_async_return_request(self, response):
        return Request("https://example.com/next")

    async def parse_async_return_list(self, response):
        return [{"url": response.url}, Request("https://example.com/next")]

    async def parse_yield_dict(self, response):
        yield {"url": response.url}
        yield Request("https://example.com/next")


def _response():
    req = Request("https://example.com/a")
    return Response(url="https://example.com/a", status=200, body=b"<html/>", request=req)


async def _collect(spider, cb):
    out = await process_callback_output(
        spider, cb, {}, _response(), logging.getLogger("test")
    )
    if out is None:
        return []
    return [x async for x in out]


@pytest.mark.asyncio
async def test_async_parse_return_dict_produces_item():
    """async parse 直接 return dict → 产出 Item。"""
    spider = _Spider()
    outputs = await _collect(spider, spider.parse_async_return_dict)
    assert len(outputs) == 1
    assert isinstance(outputs[0], Item)
    assert outputs[0]["url"] == "https://example.com/a"


@pytest.mark.asyncio
async def test_sync_parse_return_dict_produces_item():
    """同步 parse return dict → 产出 Item。"""
    spider = _Spider()
    outputs = await _collect(spider, spider.parse_sync_return_dict)
    assert len(outputs) == 1
    assert isinstance(outputs[0], Item)
    assert outputs[0]["url"] == "https://example.com/a"


@pytest.mark.asyncio
async def test_parse_return_item_unaffected():
    """返回 Item 的行为不变（回归保护）。"""
    spider = _Spider()
    outputs = await _collect(spider, spider.parse_async_return_item)
    assert len(outputs) == 1 and isinstance(outputs[0], Item)


@pytest.mark.asyncio
async def test_parse_return_request_unaffected():
    """返回 Request 的行为不变（回归保护）。"""
    spider = _Spider()
    outputs = await _collect(spider, spider.parse_async_return_request)
    assert len(outputs) == 1 and isinstance(outputs[0], Request)


@pytest.mark.asyncio
async def test_parse_return_mixed_list():
    """返回 [dict, Request] → dict 包装为 Item、Request 原样。"""
    spider = _Spider()
    outputs = await _collect(spider, spider.parse_async_return_list)
    assert [type(x).__name__ for x in outputs] == ["Item", "Request"]


@pytest.mark.asyncio
async def test_handle_spider_output_rejects_raw_dict():
    """引擎边界契约保持严格：裸 dict 直接进入仍抛 OutputError。"""

    class _Processor:
        def __init__(self):
            self.outputs = []

        async def enqueue(self, obj):
            self.outputs.append(obj)

    class _Crawler:
        class _Subscriber:
            def notify(self, *args, **kwargs):
                return asyncio.sleep(0)

        subscriber = _Subscriber()
        spider = _Spider()

    stub = object.__new__(RequestGenerationMixin)
    stub.processor = _Processor()
    stub.crawler = _Crawler()
    stub.spider = _Spider()

    async def raw_dict_gen():
        yield {"url": "https://example.com/a"}

    with pytest.raises(OutputError):
        await stub._handle_spider_output(raw_dict_gen())


@pytest.mark.asyncio
async def test_parse_yield_dict_produces_item_via_producer():
    """yield dict 经产出边界规范化 → Item（引擎端保持严格 Request|Item 契约）。"""
    spider = _Spider()
    outputs = await _collect(spider, spider.parse_yield_dict)
    assert [type(x).__name__ for x in outputs] == ["Item", "Request"]
    assert outputs[0]["url"] == "https://example.com/a"


@pytest.mark.asyncio
async def test_errback_return_dict_produces_item():
    """errback 返回 dict → 产出边界规范化后交由引擎处理（与 callback 语义一致）。"""

    class _Processor:
        def __init__(self):
            self.outputs = []

        async def enqueue(self, obj):
            self.outputs.append(obj)

    class _Crawler:
        class _Subscriber:
            def notify(self, *args, **kwargs):
                return asyncio.sleep(0)

        subscriber = _Subscriber()
        spider = _Spider()

    stub = object.__new__(RequestGenerationMixin)
    stub.processor = _Processor()
    stub.crawler = _Crawler()
    stub.spider = _Spider()

    await stub._handle_errback_output({"url": "https://example.com/err"})
    assert len(stub.processor.outputs) == 1
    assert isinstance(stub.processor.outputs[0], Item)
    assert stub.processor.outputs[0]["url"] == "https://example.com/err"
