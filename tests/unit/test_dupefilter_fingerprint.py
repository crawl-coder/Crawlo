#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P0 回归测试：请求去重指纹默认排除 headers/meta
================================================

背景缺陷：指纹曾包含全部 headers 与部分 meta（proxy/download_slot/retry_times），
导致同一 URL 只要 UA/Cookie 变化或 slot 分配不同就去重失效（重复抓取/翻页死循环）。

修复语义（与 Scrapy 一致）：
- 默认仅 method + 规范化 URL + body 参与指纹；
- 需要时通过 ``DUPEFILTER_INCLUDE_HEADERS`` / ``DUPEFILTER_INCLUDE_META``
  显式纳入指定字段。
"""

from crawlo.filters.aioredis_filter import AioRedisFilter
from crawlo.filters.memory_filter import MemoryFilter
from crawlo.utils.request.fingerprint import FingerprintGenerator, generate_request_fingerprint


URL = "https://example.com/news/1.html"


def _fp(url=URL, body=b"", headers=None, meta=None, include_headers=None):
    return generate_request_fingerprint(
        "GET", url, body, headers or {}, meta or {}, include_headers
    )


class _Settings:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _Crawler:
    def __init__(self, data=None):
        self.settings = _Settings(data or {})
        self.stats = None


class _Req:
    def __init__(self, url=URL, headers=None, meta=None, body=b""):
        self.method = "GET"
        self.url = url
        self.body = body
        self.headers = headers or {}
        self.meta = meta or {}


def test_same_url_different_headers_same_fingerprint():
    """默认：UA/Cookie 等 headers 变化不影响指纹。"""
    assert _fp(headers={"User-Agent": "UA-A"}) == _fp(headers={"User-Agent": "UA-B"})
    assert _fp(headers={"Cookie": "sid=1"}) == _fp(headers={"Cookie": "sid=2"})


def test_same_url_different_body_different_fingerprint():
    """body 始终参与指纹（POST 语义正确性）。"""
    assert _fp(body=b"a=1") != _fp(body=b"a=2")


def test_different_url_different_fingerprint():
    assert _fp(url=URL) != _fp(url=URL + "?page=2")


def test_include_headers_still_works():
    """显式 include_headers 时，指定 header 仍参与指纹。"""
    assert generate_request_fingerprint(
        "GET", URL, b"", {"User-Agent": "UA-A"}, {}, ["User-Agent"]
    ) != generate_request_fingerprint(
        "GET", URL, b"", {"User-Agent": "UA-B"}, {}, ["User-Agent"]
    )
    # header 名称大小写不敏感
    assert generate_request_fingerprint(
        "GET", URL, b"", {"user-agent": "UA-A"}, {}, ["User-Agent"]
    ) == generate_request_fingerprint(
        "GET", URL, b"", {"User-Agent": "UA-A"}, {}, ["User-Agent"]
    )


def test_include_meta_still_works():
    """显式传入的 meta（调用方按 DUPEFILTER_INCLUDE_META 筛选）参与指纹。"""
    assert generate_request_fingerprint(
        "GET", URL, b"", {}, {"download_slot": "a"}
    ) != generate_request_fingerprint(
        "GET", URL, b"", {}, {"download_slot": "b"}
    )


def test_memory_filter_dedup_ignores_headers_by_default():
    """MemoryFilter：同 URL 不同 UA/Cookie 视为重复（去重不再被绕过）。"""
    crawler = _Crawler({
        "MEMORY_FILTER_MAX_CAPACITY": 1000,
        "MEMORY_FILTER_CLEANUP_THRESHOLD": 0.8,
    })
    filt = MemoryFilter(crawler)
    r1 = _Req(headers={"User-Agent": "UA-A", "Cookie": "sid=1"})
    r2 = _Req(headers={"User-Agent": "UA-B", "Cookie": "sid=2"})
    assert filt._get_fingerprint(r1) == filt._get_fingerprint(r2)


def test_memory_filter_include_headers_config():
    """配置 DUPEFILTER_INCLUDE_HEADERS 后，指定 header 差异导致不判重。"""
    crawler = _Crawler({
        "MEMORY_FILTER_MAX_CAPACITY": 1000,
        "MEMORY_FILTER_CLEANUP_THRESHOLD": 0.8,
        "DUPEFILTER_INCLUDE_HEADERS": ["User-Agent"],
    })
    filt = MemoryFilter(crawler)
    assert filt._get_fingerprint(
        _Req(headers={"User-Agent": "UA-A"})
    ) != filt._get_fingerprint(_Req(headers={"User-Agent": "UA-B"}))


def test_redis_filter_uses_same_default_semantics():
    """AioRedisFilter 与 MemoryFilter 共享 BaseFilter 指纹语义（跨端一致）。"""
    filt = AioRedisFilter(redis_key="test:dedup", client=None, stats=None)
    assert filt._get_fingerprint(
        _Req(headers={"User-Agent": "UA-A"})
    ) == filt._get_fingerprint(_Req(headers={"User-Agent": "UA-B"}))

    filt._dupe_include_headers = ["User-Agent"]
    assert filt._get_fingerprint(
        _Req(headers={"User-Agent": "UA-A"})
    ) != filt._get_fingerprint(_Req(headers={"User-Agent": "UA-B"}))


def test_legacy_request_fingerprint_api_preserved():
    """废弃的 request_fingerprint(request, include_headers) API 语义保留。"""
    import warnings

    from crawlo.utils.request.request import request_fingerprint

    r1 = _Req(headers={"User-Agent": "UA-A"})
    r2 = _Req(headers={"User-Agent": "UA-B"})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        # 默认不纳入 headers
        assert request_fingerprint(r1) == request_fingerprint(r2)
        # 显式 include_headers 时纳入
        assert request_fingerprint(r1, include_headers=["User-Agent"]) != request_fingerprint(
            r2, include_headers=["User-Agent"]
        )
