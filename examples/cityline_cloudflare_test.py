#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cityline Cloudflare 绕过测试
=============================
测试三种动态下载器（Playwright / Camoufox / CloakBrowser）对
https://www.cityline.com.hk/Events.html 的 Cloudflare 绕过能力。

用法：
    python examples/cityline_cloudflare_test.py [--playwright] [--camoufox] [--cloakbrowser]
    不加参数则测试所有可用的下载器。
"""

import sys
import os
import asyncio
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
from crawlo.http.request import Request
from crawlo.http.response import Response

TEST_URL = 'https://www.cityline.com.hk/Events.html'
TEST_NAME = 'Cityline'

# Cloudflare 检测关键词
CF_KEYWORDS = [
    'cf_chl_opt', 'just a moment', 'checking your browser',
    'turnstile', 'challenge-platform', '__cf_bm',
    'cf-ray', 'cf-browser-verification', 'cdn-cgi/challenge',
]


def check_cloudflare_blocked(body_text: str) -> tuple:
    """检查响应是否包含 Cloudflare 拦截特征"""
    found = [kw for kw in CF_KEYWORDS if kw in body_text.lower()]
    return len(found) > 0, found


def make_mock_settings(config: dict, bool_keys: list = None, int_keys: list = None):
    """创建模拟 settings 对象"""
    mock = MagicMock()
    bool_keys = bool_keys or []
    int_keys = int_keys or []

    def mock_get(key, default=None):
        return config.get(key, default)

    def mock_get_bool(key, default=False):
        if key in config:
            return config[key]
        return key in bool_keys or default

    def mock_get_int(key, default=0):
        if key in config:
            return config[key]
        return default

    mock.get = mock_get
    mock.get_bool = mock_get_bool
    mock.get_int = mock_get_int
    return mock


async def test_playwright():
    """测试 PlaywrightDownloader"""
    print(f"\n{'='*60}")
    print(f"📦 PlaywrightDownloader")
    print(f"{'='*60}")

    config = {
        'PLAYWRIGHT_HEADLESS': False,
        'PLAYWRIGHT_TIMEOUT': 30000,
        'PLAYWRIGHT_LOAD_TIMEOUT': 30000,
        'PLAYWRIGHT_VIEWPORT_WIDTH': 1920,
        'PLAYWRIGHT_VIEWPORT_HEIGHT': 1080,
    }
    bool_keys = ['PLAYWRIGHT_HEADLESS']

    mock_crawler = MagicMock()
    mock_crawler.settings.get = make_mock_settings(config).get
    mock_crawler.settings.get_bool = make_mock_settings(config, bool_keys).get_bool
    mock_crawler.settings.get_int = make_mock_settings(config, int_keys=[]).get_int

    from crawlo.downloader.playwright_downloader import PlaywrightDownloader
    downloader = PlaywrightDownloader(mock_crawler)
    downloader.open()

    try:
        request = Request(url=TEST_URL, callback=lambda r: None)
        start = time.time()
        response = await downloader.download(request)
        elapsed = time.time() - start
        _print_result(response, elapsed)
    except Exception as e:
        print(f"  ❌ 异常: {type(e).__name__}: {str(e)[:150]}")
    finally:
        await downloader.close()


async def test_camoufox():
    """测试 CamoufoxDownloader"""
    print(f"\n{'='*60}")
    print(f"🦊 CamoufoxDownloader")
    print(f"{'='*60}")

    config = {
        'CAMOUFOX_HEADLESS': False,
        'CAMOUFOX_HUMANIZE': True,
        'CAMOUFOX_SOLVE_CLOUDFLARE': True,
        'CAMOUFOX_TIMEOUT': 30000,
        'CAMOUFOX_LOAD_TIMEOUT': 60000,
        'CAMOUFOX_VIEWPORT_WIDTH': 1920,
        'CAMOUFOX_VIEWPORT_HEIGHT': 1080,
        'CAMOUFOX_BLOCK_RESOURCES': ['image', 'font', 'media'],
        'CAMOUFOX_WAIT_STRATEGY': 'auto',
        'CAMOUFOX_WAIT_TIMEOUT': 10000,
        'BROWSER_WAIT_STRATEGY': 'auto',
    }
    bool_keys = [
        'CAMOUFOX_HEADLESS', 'CAMOUFOX_HUMANIZE',
        'CAMOUFOX_SOLVE_CLOUDFLARE',
    ]

    mock_crawler = MagicMock()
    mock_crawler.settings.get = make_mock_settings(config).get
    mock_crawler.settings.get_bool = make_mock_settings(config, bool_keys).get_bool
    mock_crawler.settings.get_int = make_mock_settings(config, int_keys=[]).get_int

    from crawlo.downloader.camoufox_downloader import CamoufoxDownloader
    downloader = CamoufoxDownloader(mock_crawler)
    downloader.open()

    try:
        request = Request(url=TEST_URL, callback=lambda r: None)
        start = time.time()
        response = await downloader.download(request)
        elapsed = time.time() - start
        _print_result(response, elapsed)
    except Exception as e:
        print(f"  ❌ 异常: {type(e).__name__}: {str(e)[:150]}")
    finally:
        await downloader.close()


async def test_cloakbrowser():
    """测试 CloakBrowserDownloader"""
    print(f"\n{'='*60}")
    print(f"🕵️  CloakBrowserDownloader")
    print(f"{'='*60}")

    config = {
        'CLOAKBROWSER_HEADLESS': False,
        'CLOAKBROWSER_HUMANIZE': True,
        'CLOAKBROWSER_GEOIP': True,
        'CLOAKBROWSER_TIMEOUT': 120000,
        'CLOAKBROWSER_LOAD_TIMEOUT': 60000,
        'CLOAKBROWSER_VIEWPORT_WIDTH': 1920,
        'CLOAKBROWSER_VIEWPORT_HEIGHT': 1080,
        'CLOAKBROWSER_MAX_PAGES': 5,
        'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font', 'media'],
        'CLOAKBROWSER_WAIT_STRATEGY': 'auto',
        'CLOAKBROWSER_WAIT_TIMEOUT': 10000,
        'CLOAKBROWSER_STEALTH_ARGS': True,
        'BROWSER_WAIT_STRATEGY': 'auto',
    }
    bool_keys = [
        'CLOAKBROWSER_HEADLESS', 'CLOAKBROWSER_HUMANIZE',
        'CLOAKBROWSER_GEOIP', 'CLOAKBROWSER_STEALTH_ARGS',
    ]

    mock_crawler = MagicMock()
    mock_crawler.settings.get = make_mock_settings(config).get
    mock_crawler.settings.get_bool = make_mock_settings(config, bool_keys).get_bool
    mock_crawler.settings.get_int = make_mock_settings(config, int_keys=[]).get_int

    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    downloader = CloakBrowserDownloader(mock_crawler)
    downloader.open()

    try:
        request = Request(url=TEST_URL, callback=lambda r: None)
        start = time.time()
        response = await downloader.download(request)
        elapsed = time.time() - start
        _print_result(response, elapsed)
    except Exception as e:
        print(f"  ❌ 异常: {type(e).__name__}: {str(e)[:150]}")
    finally:
        await downloader.close()


def _print_result(response, elapsed):
    """打印测试结果"""
    if not isinstance(response, Response):
        print(f"  ⚠️  非 Response 类型: {type(response).__name__}")
        return

    body_text = response.body.decode('utf-8', errors='ignore')
    is_blocked, found_kw = check_cloudflare_blocked(body_text)

    print(f"  URL:    {response.url}")
    print(f"  状态码: {response.status}")
    print(f"  大小:   {len(response.body):,} 字节")
    print(f"  耗时:   {elapsed:.1f}s")

    # 提取页面标题
    title_start = body_text.find('<title>')
    title_end = body_text.find('</title>')
    if title_start != -1 and title_end != -1:
        title = body_text[title_start + 7:title_end].strip()[:60]
        print(f"  标题:   {title}")

    # 提取可见文本量
    import re
    visible_text = re.sub(r'<[^>]+>', ' ', body_text)
    visible_text = re.sub(r'\s+', ' ', visible_text).strip()
    print(f"  可见文本: {len(visible_text):,} 字符")

    if is_blocked:
        print(f"  ❌ Cloudflare 拦截: 检测到 {len(found_kw)} 个特征→ {found_kw[:4]}")
    elif response.status == 200 and len(visible_text) > 200:
        print(f"  ✅ 绕过成功! 页面正常加载")
        # 显示前100字符
        print(f"  页面预览: {visible_text[:120]}...")
    else:
        print(f"  ⚠️  结果不确定 (status={response.status}, text={len(visible_text)} chars)")


async def main():
    """运行所有可用的动态下载器测试"""
    args = set(sys.argv[1:])
    test_all = not args or '--all' in args

    print(f"\n{'#'*60}")
    print(f"# Cityline Cloudflare 绕过测试")
    print(f"# 目标: {TEST_URL}")
    print(f"{'#'*60}\n")

    results = []

    if test_all or '--playwright' in args:
        try:
            await test_playwright()
            results.append(('Playwright', '✅ 完成'))
        except Exception as e:
            print(f"  💥 Playwright 测试崩溃: {e}")
            results.append(('Playwright', '💥 崩溃'))

    if test_all or '--camoufox' in args:
        try:
            await test_camoufox()
            results.append(('Camoufox', '✅ 完成'))
        except Exception as e:
            print(f"  💥 Camoufox 测试崩溃: {e}")
            results.append(('Camoufox', '💥 崩溃'))

    if test_all or '--cloakbrowser' in args:
        try:
            await test_cloakbrowser()
            results.append(('CloakBrowser', '✅ 完成'))
        except Exception as e:
            print(f"  💥 CloakBrowser 测试崩溃: {e}")
            results.append(('CloakBrowser', '💥 崩溃'))

    # 总结
    print(f"\n{'='*60}")
    print("测试总结:")
    for name, status in results:
        print(f"  {name}: {status}")
    print(f"{'='*60}")


if __name__ == '__main__':
    asyncio.run(main())
