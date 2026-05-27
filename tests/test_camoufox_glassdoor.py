#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Camoufox 绕过 Glassdoor Cloudflare
直接调用 Camoufox 同步 API。
"""

import time, re


def test():
    from camoufox import Camoufox

    print('=' * 70)
    print('Camoufox Glassdoor Cloudflare 绕过')
    print('=' * 70)

    # 不传 addons 参数，让库使用默认行为
    fox = Camoufox(headless=False, humanize=True)

    print('\n正在启动 Camoufox...')
    try:
        api = fox.start()
    except Exception as e:
        print(f'启动失败: {e}')
        print('\n尝试不加载附加组件...')
        fox = Camoufox(headless=False, humanize=True, addons=[])
        try:
            api = fox.start()
        except Exception as e2:
            print(f'仍然失败: {e2}')
            return

    print('Camoufox 启动成功')

    # 创建页面
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('https://www.glassdoor.com', wait_until='domcontentloaded', timeout=120000)

        print(f'\n当前 URL: {page.url}')
        print('\n等待 CF 绕过（最多 60 秒）...')

        bypassed = False
        for i in range(60):
            time.sleep(1)
            try:
                body = page.content().lower()
                has_cf = any(kw in body for kw in
                    ['cf_chl_opt', 'just a moment', 'challenge-platform'])
                if not has_cf and page.url != 'about:blank':
                    bypassed = True
                    break
            except:
                continue

        print(f'CF 绕过: {"成功" if bypassed else "失败"}')
        print(f'URL: {page.url}')
        print('\n保持 30 秒...')
        time.sleep(30)
        browser.close()

    print('完成')


if __name__ == '__main__':
    test()
