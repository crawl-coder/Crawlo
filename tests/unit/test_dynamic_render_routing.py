#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
DynamicRenderMiddleware 路由标记单元测试

验证中间件与 HybridDownloader 的协作契约：
- 仅在 DYNAMIC_RENDER_* 显式配置命中时才打 use_dynamic_loader /
  use_protocol_loader 标记；
- 零配置时不打标（交由 HybridDownloader 按 HYBRID_* 规则/默认协议路由），
  回归：修复前零配置会无条件打 use_protocol_loader，短路 HYBRID 规则。
"""
from unittest.mock import Mock

import pytest

from crawlo.middleware.dynamic_render_middleware import DynamicRenderMiddleware


def _make_middleware(
    dynamic_patterns=None,
    static_patterns=None,
    dynamic_domains=None,
    static_domains=None,
    default_dynamic=False,
) -> DynamicRenderMiddleware:
    crawler = Mock()
    settings = {
        "DYNAMIC_RENDER_ENABLED": True,
        "DYNAMIC_RENDER_CACHE_ENABLED": True,
        "DYNAMIC_RENDER_DEFAULT_DYNAMIC": default_dynamic,
        "DYNAMIC_RENDER_URL_PATTERNS": dynamic_patterns or [],
        "DYNAMIC_RENDER_STATIC_PATTERNS": static_patterns or [],
        "DYNAMIC_RENDER_DOMAINS": dynamic_domains or [],
        "DYNAMIC_RENDER_STATIC_DOMAINS": static_domains or [],
    }
    crawler.settings.get_bool.side_effect = lambda k, d=False: settings.get(k, d)
    crawler.settings.get_list.side_effect = lambda k, d=None: settings.get(k, d if d is not None else [])
    return DynamicRenderMiddleware.create_instance(crawler)


def _make_request(url: str, meta: dict = None):
    request = Mock()
    request.url = url
    request.meta = dict(meta or {})
    return request


@pytest.mark.asyncio
async def test_no_config_stamps_nothing():
    """回归主 bug：零配置不得打任何标记（否则短路 HYBRID_* 路由）"""
    mw = _make_middleware()
    request = _make_request("http://127.0.0.1:8000/d-detail/1")
    await mw.process_request(request, spider=Mock())
    assert 'use_dynamic_loader' not in request.meta
    assert 'use_protocol_loader' not in request.meta


@pytest.mark.asyncio
async def test_dynamic_pattern_stamps_dynamic():
    """显式动态 URL 模式命中 -> 打 use_dynamic_loader"""
    mw = _make_middleware(dynamic_patterns=[r"/d-"])
    request = _make_request("http://x.com/d-detail/1")
    await mw.process_request(request, spider=Mock())
    assert request.meta.get('use_dynamic_loader') is True
    assert 'use_protocol_loader' not in request.meta


@pytest.mark.asyncio
async def test_static_pattern_stamps_protocol():
    """显式静态 URL 模式命中 -> 打 use_protocol_loader（保留强制静态语义）"""
    mw = _make_middleware(static_patterns=[r"\.json$"])
    request = _make_request("http://x.com/api/data.json")
    await mw.process_request(request, spider=Mock())
    assert request.meta.get('use_protocol_loader') is True


@pytest.mark.asyncio
async def test_dynamic_domain_stamps_dynamic():
    """显式动态域名命中 -> 打 use_dynamic_loader"""
    mw = _make_middleware(dynamic_domains=["spa.example.com"])
    request = _make_request("https://spa.example.com/page/1")
    await mw.process_request(request, spider=Mock())
    assert request.meta.get('use_dynamic_loader') is True


@pytest.mark.asyncio
async def test_user_explicit_meta_not_overridden():
    """用户已在请求上显式指定 -> 中间件不覆盖"""
    mw = _make_middleware(dynamic_patterns=[r"/d-"])
    request = _make_request("http://x.com/d-detail/1", meta={'use_protocol_loader': True})
    await mw.process_request(request, spider=Mock())
    # 用户显式的 protocol 标记保持原样，未被动态模式改写
    assert request.meta['use_protocol_loader'] is True
    assert 'use_dynamic_loader' not in request.meta


@pytest.mark.asyncio
async def test_disabled_stamps_nothing():
    """enabled=False -> 完全不动 meta"""
    mw = _make_middleware()
    mw.enabled = False
    request = _make_request("http://spa.example.com/x")
    await mw.process_request(request, spider=Mock())
    assert request.meta == {}


@pytest.mark.asyncio
async def test_default_dynamic_true_stamps_dynamic():
    """DYNAMIC_RENDER_DEFAULT_DYNAMIC=True 时默认回退仍打 dynamic 标（保兼容）"""
    mw = _make_middleware(default_dynamic=True)
    request = _make_request("http://unknown.example.com/page")
    await mw.process_request(request, spider=Mock())
    assert request.meta.get('use_dynamic_loader') is True


@pytest.mark.asyncio
async def test_cache_holds_explicit_results_only():
    """"缓存只存显式命中的结果；缓存命中视为显式知识照常打标"""
    mw = _make_middleware(dynamic_patterns=[r"/d-"])
    first = _make_request("http://x.com/d-a")
    await mw.process_request(first, spider=Mock())
    assert first.meta.get('use_dynamic_loader') is True

    # 同域第二个请求走缓存路径，结果一致
    second = _make_request("http://x.com/s-b")
    await mw.process_request(second, spider=Mock())
    assert second.meta.get('use_dynamic_loader') is True

    # 缓存内容应来自显式命中而非默认回退：
    mw2 = _make_middleware()  # 零配置
    probe = _make_request("http://y.com/a")
    await mw2.process_request(probe, spider=Mock())
    assert mw2._domain_cache == {}  # 默认回退不写缓存


@pytest.mark.asyncio
async def test_static_pattern_wins_over_hybrid_style_dynamic_url():
    """同 URL 同时可被本中间件静态模式与外部规则解释时，
    本中间件显式静态命中优先打 protocol 标（强制语义不变）"""
    mw = _make_middleware(static_patterns=[r"/d-"])
    request = _make_request("http://x.com/d-detail/1")
    await mw.process_request(request, spider=Mock())
    assert request.meta.get('use_protocol_loader') is True
