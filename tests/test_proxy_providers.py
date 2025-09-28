# tests/test_proxy_providers.py
import pytest
import pytest
import respx
from httpx import Response
from crawlo.proxy.providers import StaticProxyProvider, FileProxyProvider, APIProxyProvider
import tempfile
import os


@pytest.mark.asyncio
async def test_static_provider():
    """测试静态代理提供者"""
    provider = StaticProxyProvider(['http://1.1.1.1:8080', 'http://2.2.2.2:8080'])
    proxies = await provider.fetch_proxies()
    assert len(proxies) == 2
    assert 'http://1.1.1.1:8080' in proxies
    assert 'http://2.2.2.2:8080' in proxies


@pytest.mark.asyncio
async def test_file_provider():
    """测试文件代理提供者"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("http://a.com:8080\nhttp://b.com:8080\n")
        temp_path = f.name
    try:
        provider = FileProxyProvider(temp_path)
        proxies = await provider.fetch_proxies()
        assert len(proxies) == 2
        assert 'http://a.com:8080' in proxies
        assert 'http://b.com:8080' in proxies
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio
@respx.mock
async def test_api_provider():
    """使用 respx 拦截 HTTP 请求，更简洁可靠"""
    # 拦截 GET 请求
    respx.get("https://api.example.com").mock(
        return_value=Response(
            200,
            json=[
                {"ip": "1.1.1.1", "port": 8080},
                {"ip": "2.2.2.2", "port": 8080}
            ]
        )
    )

    provider = APIProxyProvider(url="https://api.example.com")
    proxies = await provider.fetch_proxies()

    assert len(proxies) == 2
    assert "http://1.1.1.1:8080" in proxies
    assert "http://2.2.2.2:8080" in proxies