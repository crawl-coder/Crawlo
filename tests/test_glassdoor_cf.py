#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Glassdoor Cloudflare 绕过验证测试
等待 CF 绕过后再读取页面内容
"""

import sys, os, asyncio, time, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def test_glassdoor_verify():
    from cloakbrowser import launch_async

    url = 'https://www.glassdoor.com'

    print('=' * 70)
    print('Glassdoor Cloudflare 绕过验证')
    print('=' * 70)
    print('\n1. 启动 CloakBrowser...')
    browser = await launch_async(headless=False, humanize=True, geoip=False)

    print('2. 创建页面...')
    context = await browser.new_context()
    page = await context.new_page()

    print(f'\n3. 导航到 {url}')
    start = time.time()
    await page.goto(url, wait_until='domcontentloaded', timeout=120000)
    print(f'   首屏加载: {time.time() - start:.1f}s')

    print('\n4. 等待 Cloudflare 绕过（最多 60 秒）...')
    bypass_start = time.time()
    bypassed = False

    for i in range(60):
        await asyncio.sleep(1)
        current_url = page.url

        # 页面正在导航中（CF 挑战刚解决），跳过 content 读取
        try:
            body = await page.content()
        except Exception:
            print(f'   [{i+1}s] 页面正在导航跳转中...')
            continue

        bl = body.lower()

        has_cf = any(kw in bl for kw in
            ['cf_chl_opt', 'just a moment', 'challenge-platform', '__cf_bm'])

        if not has_cf and current_url != 'about:blank':
            bypassed = True
            el = time.time() - bypass_start
            print(f'   CF 绕过成功! 耗时: {el:.0f}s')
            print(f'   最终 URL: {current_url}')
            break

    total = time.time() - start

    if bypassed:
        m = re.search(r'<title>(.*?)</title>', (await page.content()).lower())
        print(f'\n=== 绕过成功 ===')
        print(f'页面标题: {m.group(1)[:100] if m else "N/A"}')
        print(f'总耗时: {total:.1f}s')
    else:
        print(f'\n=== 60 秒内未绕过 ===')
        print(f'当前 URL: {page.url}')

    print('\n页面保持 30 秒供观察...')
    await asyncio.sleep(30)
    await browser.close()
    print('测试完成')


if __name__ == '__main__':
    asyncio.run(test_glassdoor_verify())
