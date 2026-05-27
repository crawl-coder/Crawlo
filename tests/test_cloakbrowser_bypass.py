#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 实战绕过测试
========================
验证 CloakBrowser 对 Cloudflare 防护网站的绕过能力。
"""

import sys, os, asyncio, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlo.network.request import Request
from crawlo.network.response import Response

TEST_URLS = [
    ('TechCrunch', 'https://techcrunch.com'),
    ('Glassdoor',  'https://www.glassdoor.com'),
    ('Crunchbase', 'https://www.crunchbase.com'),
]


async def test_cloakbrowser_bypass():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.settings.get.side_effect = lambda k, d=None: {
        'CLOAKBROWSER_HEADLESS': False,
        'CLOAKBROWSER_HUMANIZE': True,
        'CLOAKBROWSER_GEOIP': False,
        'CLOAKBROWSER_LAUNCH_TIMEOUT': 60000,
        'CLOAKBROWSER_PAGE_TIMEOUT': 120000,
        'CLOAKBROWSER_DOWNLOAD_TIMEOUT': 180000,
    }.get(k, d)
    mock.settings.get_bool.side_effect = lambda k, d=False: {'CLOAKBROWSER_HEADLESS': False}.get(k, d)
    mock.settings.get_int.side_effect = lambda k, d=0: {
        'CLOAKBROWSER_LAUNCH_TIMEOUT': 60000,
        'CLOAKBROWSER_PAGE_TIMEOUT': 120000,
        'CLOAKBROWSER_DOWNLOAD_TIMEOUT': 180000,
    }.get(k, d)

    dl = CloakBrowserDownloader(mock)
    dl.open()  # 非 async，仅标记打开状态

    print('=' * 70)
    print('CloakBrowser Cloudflare 绕过测试')
    print('=' * 70)

    try:
        for name, url in TEST_URLS:
            print(f'\n--- {name} ({url}) ---')
            request = Request(url=url, callback=lambda r: None)

            start = time.time()
            try:
                response = await dl.download(request)
                elapsed = time.time() - start

                if response is None:
                    print(f'   X 浏览器未成功启动 | 耗时: {elapsed:.1f}s')
                else:
                    status = response.status if hasattr(response, 'status') else getattr(response, 'status_code', 0)
                    body = getattr(response, 'body', b'')
                    body_text = body.decode('utf-8', errors='ignore').lower() if body else ''

                    has_cf = any(kw in body_text for kw in [
                        'cf_chl_opt', 'just a moment', 'checking your browser',
                        'turnstile', 'challenge-platform'
                    ])

                    if has_cf:
                        result = 'X 绕过失败（内容仍含 CF 特征）'
                    elif status == 200:
                        result = 'V 绕过成功!'
                    else:
                        result = f'? 未知 (status={status})'

                    print(f'   状态: {status} | 大小: {len(body):,}B | 耗时: {elapsed:.1f}s | {result}')

            except Exception as e:
                elapsed = time.time() - start
                print(f'   X 异常: {type(e).__name__}: {str(e)[:120]} | 耗时: {elapsed:.1f}s')

    finally:
        print('\n' + '=' * 70)
        print('浏览器将在 60 秒后关闭，请观察窗口中的页面行为...')
        print('=' * 70)
        await asyncio.sleep(60)
        await dl.close()

    print('\n' + '=' * 70)
    print('测试完成')


if __name__ == '__main__':
    asyncio.run(test_cloakbrowser_bypass())
