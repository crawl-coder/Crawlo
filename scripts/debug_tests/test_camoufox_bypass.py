#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Camoufox 实战绕过测试
=====================
使用 CamoufoxDownloader 直接请求 Cloudflare 防护网站，
验证 bypass 绕过能力。
"""

import sys, os, asyncio, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlo.network.request import Request
from crawlo.network.response import Response

# 测试网站（上一轮检测确认有 CF 防护的）
TEST_URLS = [
    ('TechCrunch', 'https://techcrunch.com'),
    ('Glassdoor', 'https://www.glassdoor.com'),
    ('Crunchbase', 'https://www.crunchbase.com'),
]


async def test_camoufox_bypass():
    """使用 Camoufox 绕过测试"""
    from unittest.mock import Mock, MagicMock
    from crawlo.downloader.camoufox_downloader import CamoufoxDownloader

    # 创建模拟 crawler
    mock_crawler = MagicMock()

    def mock_get(key, default=None):
        config = {
            'CAMOUFOX_HEADLESS': True,
            'CAMOUFOX_HUMANIZE': True,
            'CAMOUFOX_SOLVE_CLOUDFLARE': True,
            'CAMOUFOX_PAGE_TIMEOUT': 30000,
            'CAMOUFOX_NAVIGATION_TIMEOUT': 60000,
            'CAMOUFOX_DOWNLOAD_TIMEOUT': 90000,
            'CAMOUFOX_BROWSER_ARGS': [],
        }
        return config.get(key, default)

    def mock_get_bool(key, default=False):
        bool_config = {
            'CAMOUFOX_HEADLESS': True,
            'CAMOUFOX_HUMANIZE': True,
            'CAMOUFOX_SOLVE_CLOUDFLARE': True,
        }
        return bool_config.get(key, default)

    def mock_get_int(key, default=0):
        int_config = {
            'CAMOUFOX_PAGE_TIMEOUT': 30000,
            'CAMOUFOX_NAVIGATION_TIMEOUT': 60000,
            'CAMOUFOX_DOWNLOAD_TIMEOUT': 90000,
        }
        return int_config.get(key, default)

    mock_crawler.settings.get = mock_get
    mock_crawler.settings.get_bool = mock_get_bool
    mock_crawler.settings.get_int = mock_get_int

    downloader = CamoufoxDownloader(mock_crawler)
    downloader.open()

    print('=' * 70)
    print('Camoufox Cloudflare 绕过测试')
    print('=' * 70)

    try:
        for name, url in TEST_URLS:
            print(f'\n--- {name} ({url}) ---')

            request = Request(url=url, callback=lambda r: None)

            start = time.time()
            try:
                response = await downloader.download(request)
                elapsed = time.time() - start

                if isinstance(response, Response):
                    body_text = response.body.decode('utf-8', errors='ignore').lower()
                    has_cf = any(kw in body_text for kw in [
                        'cf_chl_opt', 'just a moment', 'checking your browser',
                        'turnstile', 'challenge-platform', '__cf_bm'
                    ])

                    if has_cf:
                        status = 'CF 绕过失败（内容仍含 CF 特征）'
                    elif response.status == 200:
                        status = '绕过成功!'
                    else:
                        status = f'未知结果 (status={response.status})'

                    print(f'   状态: {response.status} | 大小: {len(response.body):,}B')
                    print(f'   耗时: {elapsed:.1f}s | 结果: {status}')
                else:
                    print(f'   [!] 非 Response 返回值: {type(response).__name__}')

            except Exception as e:
                elapsed = time.time() - start
                print(f'   [!] 下载异常: {type(e).__name__}: {str(e)[:100]}')
                print(f'   耗时: {elapsed:.1f}s')

    finally:
        await downloader.close()

    print('\n' + '=' * 70)
    print('测试完成')


if __name__ == '__main__':
    asyncio.run(test_camoufox_bypass())
