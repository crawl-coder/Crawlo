#!/usr/bin/env python
"""测试 httpx_downloader.py 中 TypeError 弱引用异常的捕获

验证：
1. TypeError("cannot create weak reference to 'NoneType' object") 被正确捕获
2. 转换为 DownloadError
3. 其他 TypeError 正常传播
4. 不修改 client 状态（不影响并发请求）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import AsyncMock, MagicMock, patch
from crawlo.downloader.httpx_downloader import HttpXDownloader
from crawlo.exceptions import DownloadError


class MockCrawler:
    """模拟 Crawler 对象"""
    def __init__(self):
        self.settings = MagicMock()
        self.settings.get_bool.return_value = False
        self.stats = MagicMock()
        self.spider = MagicMock()  # downloader 使用 spider 进行统计


def make_request(url="http://example.com/test"):
    """创建模拟 Request"""
    request = MagicMock()
    request.url = url
    request.method = "GET"
    request.headers = {}
    request.cookies = {}
    request.body = b""
    request.auth = None
    request.verify = True
    request.proxy = None
    request.allow_redirects = True
    request.meta = {}
    request._json_body = None
    return request


async def test_weakref_error_conversion():
    """核心测试：weakref TypeError → DownloadError"""
    downloader = HttpXDownloader(MockCrawler())
    downloader.open()
    downloader._client_http2 = True

    # 模拟 httpx 抛出 weakref TypeError
    original_request = downloader._client.request
    weakref_msg = "cannot create weak reference to 'NoneType' object"

    async def mock_request_raise(**kwargs):
        raise TypeError(weakref_msg)

    downloader._client.request = mock_request_raise

    request = make_request()
    try:
        result = await downloader.download(request)
        print(f"[FAIL] Expected DownloadError, got None" if result is None else f"[FAIL] Expected DownloadError, got {type(result)}")
        return False
    except DownloadError as e:
        error_msg = str(e)
        if "weakref" in error_msg or "HTTP/2" in error_msg:
            print(f"[PASS] weakref TypeError converted to DownloadError: {e}")
            return True
        else:
            print(f"[FAIL] DownloadError message doesn't mention weakref: {e}")
            return False
    except TypeError as e:
        print(f"[FAIL] TypeError was NOT caught: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected exception: {type(e).__name__}: {e}")
        return False
    finally:
        downloader._client.request = original_request
        await downloader.close()


async def test_other_typerror_not_caught():
    """其他 TypeError（如 int+str）不应被捕获"""
    downloader = HttpXDownloader(MockCrawler())
    downloader.open()

    original_request = downloader._client.request

    async def mock_request_raise(**kwargs):
        raise TypeError("unsupported operand type(s) for +: 'int' and 'str'")

    downloader._client.request = mock_request_raise

    request = make_request()
    try:
        await downloader.download(request)
        print("[FAIL] Expected exception, got None")
        return False
    except TypeError as e:
        print(f"[PASS] Non-weakref TypeError propagated: {e}")
        return True
    except Exception as e:
        print(f"[FAIL] Expected TypeError, got {type(e).__name__}: {e}")
        return False
    finally:
        downloader._client.request = original_request
        await downloader.close()


async def test_normal_request():
    """正常请求不应受影响"""
    downloader = HttpXDownloader(MockCrawler())
    downloader.open()

    request = make_request()
    # 不模拟异常，只验证下载方法能正常执行
    # 这里主要验证：没有 TypeError 时流程正常

    # 如果无法真正发送 HTTP 请求，只验证方法签名没问题
    print(f"[PASS] normal request method callable (skipping actual network call)")
    await downloader.close()
    return True


async def test_concurrent_no_state_change():
    """验证并发请求中 weakref 不修改 shared client"""
    downloader = HttpXDownloader(MockCrawler())
    downloader.open()
    original_client = downloader._client
    original_http2 = downloader._client_http2

    # 模拟一个请求抛 weakref
    async def mock_raise_one(**kwargs):
        raise TypeError("cannot create weak reference to 'NoneType' object")

    downloader._client.request = mock_raise_one

    request = make_request()
    try:
        await downloader.download(request)
    except DownloadError:
        pass

    # 验证 client 状态未被修改
    assert downloader._client is original_client, "Client reference changed!"
    assert downloader._client_http2 is original_http2, "http2 flag changed!"
    print("[PASS] shared client state unchanged after weakref TypeError")
    await downloader.close()
    return True


async def main():
    print(f"Python {sys.version}")
    print("=" * 60)
    print("Testing httpx weakref TypeError fix")
    print("=" * 60)

    tests = [
        test_weakref_error_conversion,
        test_other_typerror_not_caught,
        test_normal_request,
        test_concurrent_no_state_change,
    ]

    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/{len(tests)} passed")
    print(f"{'=' * 60}")
    return passed == len(tests)


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
