# tests/test_proxy_middleware_integration.py
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from crawlo import Request, Response, Spider
from crawlo.proxy.middleware import ProxyMiddleware
from crawlo.proxy.stats import ProxyStats


@pytest.fixture
def crawler():
    class MockSettings:
        def get(self, key, default=None):
            defaults = {
                'PROXY_ENABLED': True,
                'PROXIES': ['http://p1:8080', 'http://p2:8080'],
                'PROXY_SELECTION_STRATEGY': 'random',
                'PROXY_REQUEST_DELAY_ENABLED': False,
                'PROXY_MAX_RETRY_COUNT': 1,
            }
            return defaults.get(key, default)

        def get_bool(self, key, default=None):
            return self.get(key, default)

        def get_int(self, key, default=None):
            return self.get(key, default)

        def get_float(self, key, default=None):
            return self.get(key, default)

        def get_list(self, key, default=None):
            return self.get(key, default)

    class MockCrawler:
        def __init__(self):
            self.settings = MockSettings()

    return MockCrawler()


@pytest.fixture
def middleware(crawler):
    mw = ProxyMiddleware.create_instance(crawler)
    mw._load_providers = Mock()
    mw._update_proxy_pool = AsyncMock()
    mw._health_check = AsyncMock()
    mw.scheduler = None

    mw.proxies = [
        {
            'url': 'http://p1:8080',
            'healthy': True,
            'failures': 0,
            'last_health_check': 0,
            'unhealthy_since': 0
        },
        {
            'url': 'http://p2:8080',
            'healthy': True,
            'failures': 0,
            'last_health_check': 0,
            'unhealthy_since': 0
        },
    ]
    mw.stats = ProxyStats()
    for p in mw.proxies:
        mw.stats.record(p['url'], 'total')

    asyncio.get_event_loop().run_until_complete(mw._initial_setup())
    return mw


@pytest.fixture
def spider():
    return Mock(spec=Spider, logger=Mock())


def test_process_request_sets_proxy(middleware, spider):
    request = Request("https://example.com")
    result = asyncio.get_event_loop().run_until_complete(
        middleware.process_request(request, spider)
    )
    assert result is None
    assert hasattr(request, 'proxy')
    assert request.proxy in ['http://p1:8080', 'http://p2:8080']


def test_process_response_records_success(middleware, spider):
    request = Request("https://example.com")
    request.proxy = 'http://p1:8080'
    response = Response("https://example.com", body=b"ok", headers={})
    middleware.stats.record(request.proxy, 'total')
    middleware.process_response(request, response, spider)
    assert middleware.stats.get(request.proxy)['success'] == 1


def test_process_exception_switches_proxy(middleware, spider):
    request = Request("https://example.com")
    request.proxy = 'http://p1:8080'
    request.meta['proxy_retry_count'] = 0

    result = middleware.process_exception(request, Exception("Timeout"), spider)
    assert result is not None
    assert result.proxy != 'http://p1:8080'
    assert result.meta['proxy_retry_count'] == 1

    final = middleware.process_exception(result, Exception("Timeout"), spider)
    assert final is None


def test_mark_failure_disables_proxy(middleware):
    proxy_url = 'http://p1:8080'
    p = next(p for p in middleware.proxies if p['url'] == proxy_url)
    p['failures'] = 2

    middleware._mark_failure(proxy_url)
    assert p['failures'] == 3
    assert p['healthy'] is False
    assert p['unhealthy_since'] > 0


@pytest.mark.asyncio
async def test_request_delay(middleware, spider):
    """测试请求延迟功能：验证是否调用了 asyncio.sleep"""
    with patch("crawlo.proxy.middleware.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        middleware.delay_enabled = True  # 注意：这里应该是 delay_enabled 而不是 request_delay_enabled
        middleware.request_delay = 0.1
        middleware._last_req_time = time.time() - 0.05  # 50ms 前

        request = Request("https://a.com")
        await middleware.process_request(request, spider)

        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 0.04 <= delay <= 0.06