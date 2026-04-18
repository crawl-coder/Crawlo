#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare 防护真实网站测试
============================

测试 Crawlo 框架对真实 Cloudflare 防护网站的处理能力。

注意：
1. 本测试仅检测是否遇到 Cloudflare 挑战，不实际绕过
2. 测试网站可能会改变防护策略
3. 请遵守网站的 robots.txt 和使用条款
"""

import sys
import os
import asyncio
from unittest.mock import Mock

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# 测试网站列表（已知使用 Cloudflare 的网站）
TEST_SITES = [
    # 低风险 - 基础 Cloudflare 防护
    {
        'url': 'https://archive.org',
        'name': 'Internet Archive',
        'expected_cf': False,  # 通常不会有挑战
        'category': '档案馆'
    },
    {
        'url': 'https://www.reuters.com',
        'name': 'Reuters（路透社）',
        'expected_cf': False,
        'category': '新闻媒体'
    },
    
    # 中风险 - 可能有挑战
    {
        'url': 'https://techcrunch.com',
        'name': 'TechCrunch',
        'expected_cf': False,
        'category': '科技媒体'
    },
    {
        'url': 'https://www.glassdoor.com',
        'name': 'Glassdoor',
        'expected_cf': True,  # 可能有挑战
        'category': '职场信息'
    },
    
    # 高风险 - 强 Cloudflare 防护
    {
        'url': 'https://www.crunchbase.com',
        'name': 'Crunchbase',
        'expected_cf': True,  # 很可能有挑战
        'category': '商业数据'
    },
    {
        'url': 'https://www.bloomberg.com',
        'name': 'Bloomberg（彭博社）',
        'expected_cf': True,
        'category': '金融新闻'
    },
]


async def test_cloudflare_detection():
    """测试 Cloudflare 检测能力"""
    from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
    from crawlo.network.response import Response
    
    print("=" * 80)
    print("Cloudflare 防护真实网站测试")
    print("=" * 80)
    print()
    print("⚠️  免责声明：")
    print("   1. 本测试仅用于验证框架功能")
    print("   2. 请遵守目标网站的使用条款")
    print("   3. 不要频繁请求，避免对服务器造成压力")
    print("   4. 网站防护策略可能随时变化")
    print()
    
    # 创建模拟的 middleware
    mock_crawler = Mock()
    mock_crawler.settings.get.return_value = 'camoufox'
    mock_crawler.settings.get_int.return_value = 2
    
    middleware = CloudflareBypassMiddleware(mock_crawler)
    
    results = []
    
    for i, site in enumerate(TEST_SITES, 1):
        print(f"\n[{i}/{len(TEST_SITES)}] 测试: {site['name']}")
        print(f"   URL: {site['url']}")
        print(f"   类别: {site['category']}")
        print(f"   预期防护: {'是' if site['expected_cf'] else '否'}")
        print("-" * 80)
        
        try:
            # 注意：这里需要实际的 HTTP 请求
            # 为了演示，我们使用模拟数据
            # 实际使用时应该用 httpx 或 aiohttp 发起真实请求
            
            print("   ⏳ 正在检测...（需要网络请求）")
            print("   ℹ️  提示: 实际测试需要发起 HTTP 请求")
            print("   ℹ️  建议使用浏览器手动访问验证")
            
            # 模拟测试结果
            result = {
                'site': site['name'],
                'url': site['url'],
                'category': site['category'],
                'expected_cf': site['expected_cf'],
                'status': '需要手动验证',
                'note': '请使用浏览器访问验证'
            }
            results.append(result)
            
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            result = {
                'site': site['name'],
                'url': site['url'],
                'category': site['category'],
                'expected_cf': site['expected_cf'],
                'status': '错误',
                'error': str(e)
            }
            results.append(result)
    
    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    print(f"\n📊 测试网站统计:")
    print(f"   总数量: {len(TEST_SITES)}")
    print(f"   预期有 Cloudflare: {sum(1 for s in TEST_SITES if s['expected_cf'])}")
    print(f"   预期无 Cloudflare: {sum(1 for s in TEST_SITES if not s['expected_cf'])}")
    
    print(f"\n🔍 Cloudflare 特征检测方法:")
    print(f"   - 状态码检查: 403, 503, 520-524")
    print(f"   - 响应头检查: cf-ray, cf-cache-status")
    print(f"   - 响应内容检查: 15+ 种特征签名")
    
    print(f"\n💡 手动验证方法:")
    print(f"   1. 打开无痕/隐私浏览窗口")
    print(f"   2. 访问测试网站")
    print(f"   3. 观察是否出现:")
    print(f"      - 'Checking your browser...'")
    print(f"      - 'Just a moment...'")
    print(f"      - 'Verify you are a human'")
    print(f"   4. 如果出现，说明有 Cloudflare 防护")
    
    print(f"\n🛡️ Crawlo 自动处理:")
    print(f"   - CloudflareBypassMiddleware 自动检测挑战页面")
    print(f"   - 自动降级到 Camoufox 隐身浏览器")
    print(f"   - 自动解决 Turnstile 验证")
    print(f"   - 最大重试次数: 2 次")
    
    return results


def test_cloudflare_signatures():
    """测试 Cloudflare 特征签名检测"""
    print("\n" + "=" * 80)
    print("Cloudflare 特征签名测试")
    print("=" * 80)
    
    from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
    
    mock_crawler = Mock()
    mock_crawler.settings.get.return_value = 'camoufox'
    mock_crawler.settings.get_int.return_value = 2
    
    middleware = CloudflareBypassMiddleware(mock_crawler)
    
    # 测试不同的 Cloudflare 特征
    test_cases = [
        {
            'name': 'cf-ray 特征',
            'status': 503,
            'body': b'<html><body>cf-ray: 12345abcdef</body></html>',
            'headers': {'cf-ray': '12345abcdef'},
            'should_detect': True
        },
        {
            'name': 'Just a moment 特征',
            'status': 503,
            'body': b'<html><title>Just a moment...</title></html>',
            'headers': {},
            'should_detect': True
        },
        {
            'name': 'challenge-platform 特征',
            'status': 503,
            'body': b'<div class="challenge-platform">h/b</div>',
            'headers': {},
            'should_detect': True
        },
        {
            'name': 'cf_chl_opt 特征',
            'status': 503,
            'body': b'<script>var cf_chl_opt = {};</script>',
            'headers': {},
            'should_detect': True
        },
        {
            'name': '正常页面（无 Cloudflare）',
            'status': 200,
            'body': b'<html><body><h1>Welcome</h1></body></html>',
            'headers': {},
            'should_detect': False
        },
    ]
    
    print("\n🧪 特征检测测试:")
    print("-" * 80)
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        mock_response = Mock()
        mock_response.status_code = case['status']
        mock_response.body = case['body']
        mock_response.headers = case['headers']
        
        detected = middleware._is_cloudflare_challenge(mock_response)
        expected = case['should_detect']
        
        if detected == expected:
            status = "✅ 通过"
            passed += 1
        else:
            status = "❌ 失败"
            failed += 1
        
        print(f"\n测试: {case['name']}")
        print(f"   状态码: {case['status']}")
        print(f"   预期检测: {'是' if expected else '否'}")
        print(f"   实际检测: {'是' if detected else '否'}")
        print(f"   结果: {status}")
    
    print("\n" + "-" * 80)
    print(f"\n📊 特征检测统计:")
    print(f"   总测试数: {len(test_cases)}")
    print(f"   通过: {passed}")
    print(f"   失败: {failed}")
    print(f"   成功率: {passed/len(test_cases)*100:.1f}%")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Crawlo Cloudflare 防护检测能力测试")
    print("=" * 80)
    print()
    
    # 测试 1: Cloudflare 特征签名检测
    test_cloudflare_signatures()
    
    # 测试 2: 真实网站检测（需要网络）
    print("\n\n")
    asyncio.run(test_cloudflare_detection())
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    print()
    print("📝 建议:")
    print("   1. 使用浏览器手动访问测试网站，验证 Cloudflare 防护")
    print("   2. 在 Crawlo 爬虫中启用 CloudflareBypassMiddleware")
    print("   3. 安装 Camoufox: pip install camoufox")
    print("   4. 配置 CLOUDFLARE_BYPASS_DOWNLOADER = 'camoufox'")
    print()


if __name__ == '__main__':
    main()
