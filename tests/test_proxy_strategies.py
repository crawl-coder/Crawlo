# tests/test_proxy_strategies.py
import pytest
from crawlo import Request
from crawlo.proxy.strategies import STRATEGIES


@pytest.fixture
def mock_proxies():
    """提供测试用的代理列表"""
    return [
        {'url': 'http://p1:8080'},
        {'url': 'http://p2:8080'},
        {'url': 'http://p3:8080'},
    ]


@pytest.fixture
def mock_stats():
    """提供测试用的统计信息"""
    return {
        'http://p1:8080': {'total': 10},
        'http://p2:8080': {'total': 5},
        'http://p3:8080': {'total': 1},
    }


@pytest.fixture
def mock_request():
    """提供测试用的请求对象"""
    return Request("https://example.com")


def test_random_strategy(mock_proxies, mock_request, mock_stats):
    """测试随机策略"""
    strategy = STRATEGIES['random']
    chosen = strategy(mock_proxies, mock_request, mock_stats)
    assert chosen in [p['url'] for p in mock_proxies]


def test_least_used_strategy(mock_proxies, mock_request, mock_stats):
    """测试最少使用策略"""
    strategy = STRATEGIES['least_used']
    chosen = strategy(mock_proxies, mock_request, mock_stats)
    assert chosen == 'http://p3:8080'  # total=1


def test_domain_rule_strategy(mock_proxies, mock_request, mock_stats):
    """测试域名规则策略"""
    from crawlo.proxy.strategies.domain_rule import domain_rule_strategy
    request = Request("https://taobao.com/item/123")
    rules = {'taobao.com': 'http://special:8080'}

    # Monkey patch 确保有回退策略
    old_strategy = STRATEGIES['least_used']
    try:
        STRATEGIES['least_used'] = lambda p, r, s: 'http://fallback:8080'
        chosen = domain_rule_strategy(mock_proxies, request, mock_stats, rules)
        assert chosen == 'http://special:8080'
    finally:
        STRATEGIES['least_used'] = old_strategy