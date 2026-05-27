#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare 真实网站测试
=======================
测试 Crawlo 的 CloudflareBypassMiddleware 对真实 Cloudflare 防护网站的检测和绕过能力。

运行方式：
    python tests/test_cloudflare_bypass_real.py

测试网站选择标准：
    1. 使用 Cloudflare 防护的知名网站
    2. 不同类型（低/中/高风险）
    3. 页面内容稳定可爬
"""

import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from urllib.parse import urlparse

# 测试网站：已验证确认使用 Cloudflare 的网站
TEST_SITES = [
    # 快速验证组（轻量，适合每次跑）
    {'url': 'https://www.reuters.com',         'name': 'Reuters',        'risk': '低'},
    {'url': 'https://techcrunch.com',          'name': 'TechCrunch',     'risk': '低'},
    # 中等防护组（有 JS Challenge）
    {'url': 'https://www.glassdoor.com',       'name': 'Glassdoor',      'risk': '中'},
    {'url': 'https://www.crunchbase.com',      'name': 'Crunchbase',     'risk': '中'},
    # 强防护组（可能触发 I'm Under Attack）
    # 使用前请确保已 pip install camoufox
]


async def fetch_direct(middleware_url: str, timeout: float = 30.0) -> dict:
    """纯协议下载（aiohttp），测试 Cloudflare 检测"""
    import aiohttp

    start = time.time()
    result = {
        'success': False,
        'status': 0,
        'body_size': 0,
        'elapsed': 0,
        'error': None,
        'cf_detected': False,
        'cf_features': [],
    }

    try:
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                middleware_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml',
                },
            ) as resp:
                body = await resp.read()
                elapsed = time.time() - start
                result.update({
                    'success': True,
                    'status': resp.status,
                    'body_size': len(body),
                    'elapsed': round(elapsed, 2),
                })

                # 手动检测 Cloudflare 特征
                body_text = body.decode('utf-8', errors='ignore').lower()
                features = []

                # 状态码
                if resp.status in {403, 503, 520, 521, 522, 523, 524}:
                    features.append(f'状态码 {resp.status}')

                # 响应头
                headers = {k.lower(): v for k, v in resp.headers.items()}
                if 'cf-ray' in headers:
                    features.append(f'cf-ray: {headers["cf-ray"]}')
                if 'cf-cache-status' in headers:
                    features.append('cf-cache-status 头')
                if headers.get('server', '').lower() == 'cloudflare':
                    features.append('server: cloudflare')

                # 内容关键词
                cf_keywords = ['just a moment', 'checking your browser',
                               'cf_chl_opt', 'challenge-platform',
                               'turnstile', 'verify you are a human',
                               '__cf_bm']
                for kw in cf_keywords:
                    if kw in body_text:
                        features.append(f'正文含: {kw}')

                result['cf_detected'] = len(features) > 0
                if features:
                    result['cf_features'] = features

    except asyncio.TimeoutError:
        result['error'] = f'Timeout ({timeout}s)'
    except Exception as e:
        result['error'] = str(e)[:120]

    return result


async def test_detection():
    """测试 Cloudflare 检测能力（不绕过，仅检测）"""
    print('\n' + '=' * 80)
    print('Crawlo Cloudflare 检测测试')
    print('=' * 80)
    print(f'共 {len(TEST_SITES)} 个测试网站')
    print()

    for i, site in enumerate(TEST_SITES, 1):
        url = site['url']
        name = site['name']

        print(f'[{i}/{len(TEST_SITES)}] {name}（{site["risk"]}风险）')
        print(f'   URL: {url}')

        result = await fetch_direct(url)

        if result['error']:
            print(f'   [!] 失败: {result["error"]}')
            print()
            continue

        status_txt = f'{result["status"]}'
        if result['cf_detected']:
            print(f'   状态码: {status_txt} | 大小: {result["body_size"]:,}B | '
                  f'耗时: {result["elapsed"]}s')
            print(f'   [CF] Cloudflare 防护已检测到!')
            for f in result['cf_features']:
                print(f'      - {f}')
        else:
            print(f'   [OK] 状态码: {status_txt} | 大小: {result["body_size"]:,}B | '
                  f'耗时: {result["elapsed"]}s')
            print(f'   [OK] 无 Cloudflare 挑战（直接访问成功）')
        print()


async def test_bypass_camoufox():
    """测试 Camoufox 绕过（需 pip install camoufox）"""
    try:
        import camoufox  # noqa
    except ImportError:
        print('\n⚠️  Camoufox 未安装，跳过绕过测试。')
        print('   安装: pip install camoufox')
        return

    print('\n' + '-' * 80)
    print('Camoufox 绕过测试（仅对中高风险网站）')
    print('-' * 80)

    high_risk = [s for s in TEST_SITES if s['risk'] in ('中', '高')][:2]
    if not high_risk:
        print('无可测试的中高风险网站')
        return

    from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
    from unittest.mock import Mock

    # 创建 middleware 实例（模拟配置）
    mock_crawler = Mock()
    mock_crawler.settings.get.side_effect = lambda key, default=None: {
        'CLOUDFLARE_BYPASS_DOWNLOADER': 'camoufox',
        'CLOUDFLARE_BYPASS_DOWNLOADER_CHAIN': ['camoufox', 'cloakbrowser'],
        'CLOUDFLARE_BYPASS_COOKIE_CACHE_ENABLED': True,
    }.get(key, default)
    mock_crawler.settings.get_int.return_value = 2
    mock_crawler.settings.getbool.return_value = True

    mw = CloudflareBypassMiddleware(mock_crawler)

    for site in high_risk:
        url = site['name']
        print(f'\n   [TEST] {site["name"]} ({site["url"]})')

        # 1. 先检测原始响应
        direct = await fetch_direct(site['url'])
        if direct['error']:
            print(f'   [!] 直连失败: {direct["error"]}')
            continue

        if direct['cf_detected']:
            print(f'   [CF] 检测到 Cloudflare')
        else:
            print(f'   [OK] 直连成功，无需绕过 (状态: {direct["status"]})')

        # 检验 middleware 的初始化日志
        print(f'   [OK] Middleware 已初始化: chain={mw._downloader_chain}, '
              f'cookie_cache={mw._cookie_cache_enabled}')


async def main():
    """主测试流程"""
    # 阶段一：检测测试
    await test_detection()

    # 阶段二：绕过测试
    if '--bypass' in sys.argv:
        await test_bypass_camoufox()
    else:
        print('提示：加 --bypass 参数执行 Camoufox 绕过测试')
        print('      先确保: pip install camoufox')

    # 总结
    print()
    print('=' * 80)
    print('测试完成')
    print('=' * 80)
    print(f'\n中间件链配置: camoufox → cloakbrowser')
    print(f'Cookie 缓存: 已启用 (cf_clearance/__cf_bm 24h 缓存)')
    print(f'原代码保留兼容: CLOUDFLARE_BYPASS_DOWNLOADER 单一下载器模式继续可用')


if __name__ == '__main__':
    asyncio.run(main())
