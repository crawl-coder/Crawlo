#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""CloakBrowserDownloader CF 绕过验证"""

import sys, os, asyncio, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crawlo.network.request import Request
from unittest.mock import MagicMock


async def verify_fix():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader

    mock = MagicMock()
    mock.settings.get.side_effect = lambda k, d=None: {'CLOAKBROWSER_HEADLESS': False, 'CLOAKBROWSER_HUMANIZE': True}.get(k, d)
    mock.settings.get_bool.side_effect = lambda k, d=False: {'CLOAKBROWSER_HEADLESS': False}.get(k, d)
    mock.settings.get_int.return_value = 0
    mock.settings.get_list.return_value = []
    mock.settings.getbool = lambda k, d=False: False

    dl = CloakBrowserDownloader(mock)
    dl.open()

    print('=' * 70)
    print('CloakBrowser CF 绕过 - Glassdoor')
    print(f'load_timeout: {dl.load_timeout}ms')
    print('=' * 70)

    url = 'https://www.glassdoor.com'
    request = Request(url=url, callback=lambda r: None)

    start = time.time()
    try:
        response = await dl.download(request)
        total = time.time() - start

        body = response.body.decode('utf-8', errors='ignore').lower()
        has_cf = any(kw in body for kw in ['cf_chl_opt', 'just a moment', 'challenge-platform'])

        import re
        m = re.search(r'<title>(.*?)</title>', body)
        title = m.group(1)[:80] if m else 'N/A'

        print(f'\n状态: {response.status} | URL: {response.url}')
        print(f'大小: {len(response.body):,}B | 耗时: {total:.1f}s')
        print(f'标题: {title}')
        print(f'CF绕过: {"成功" if not has_cf else "仍含CF特征"}')
        print(f'\n页面保持 3 秒后 about:blank,等待手动观察...')

    except Exception as e:
        print(f'异常: {type(e).__name__}: {str(e)[:150]}')

    finally:
        await dl.close()

    print('完成')


if __name__ == '__main__':
    asyncio.run(verify_fix())
