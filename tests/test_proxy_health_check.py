# tests/test_proxy_health_check.py
import pytest
from unittest.mock import AsyncMock, patch
from crawlo.proxy.health_check import check_single_proxy
import httpx


@pytest.mark.asyncio
@patch('httpx.AsyncClient')
async def test_health_check_success(mock_client_class):
    """测试健康检查：成功"""
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_client_class.return_value.__aenter__.return_value.get.return_value = mock_resp

    proxy_info = {'url': 'http://good:8080', 'healthy': False}
    await check_single_proxy(proxy_info)

    assert proxy_info['healthy'] is True
    assert proxy_info['failures'] == 0


@pytest.mark.asyncio
@patch('httpx.AsyncClient')
async def test_health_check_failure(mock_client_class):
    """测试健康检查：失败"""
    mock_client_class.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Failed")

    proxy_info = {'url': 'http://bad:8080', 'healthy': True, 'failures': 0}
    await check_single_proxy(proxy_info)

    assert proxy_info['healthy'] is False
    assert proxy_info['failures'] == 1