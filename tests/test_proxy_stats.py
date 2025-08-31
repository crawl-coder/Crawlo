# tests/test_proxy_stats.py
from crawlo.proxy.stats import ProxyStats


def test_proxy_stats():
    """测试代理统计功能"""
    stats = ProxyStats()
    url = 'http://proxy1:8080'

    stats.record(url, 'success')
    stats.record(url, 'success')
    stats.record(url, 'failure')

    assert stats.get(url)['success'] == 2
    assert stats.get(url)['failure'] == 1
    assert stats.get(url)['total'] == 3

    all_data = stats.all()
    assert url in all_data
    assert all_data[url]['success'] == 2