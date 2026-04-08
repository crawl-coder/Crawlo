#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare 防护国内网站测试
=============================

测试 Crawlo 框架对国内 Cloudflare 防护网站的处理能力。
所有网站均可在中国大陆正常访问。
"""

import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.network.response import Response


class ChinaCloudflareTestSpider(Spider):
    """
    国内 Cloudflare 防护测试爬虫
    
    测试中国大陆可访问的使用 Cloudflare 防护的网站。
    """
    
    name = 'china_cloudflare_test'
    
    # 国内测试网站列表（按防护强度排序）
    start_urls = [
        # 低风险 - 基础 Cloudflare CDN
        'https://www.oschina.net',          # 开源中国
        'https://www.v2ex.com',             # V2EX
        
        # 中等风险 - 可能有基础防护
        'https://juejin.cn',                # 掘金
        'https://segmentfault.com',         # SegmentFault
        'https://sspai.com',                # 少数派
        
        # 中高风险 - 较强防护
        'https://36kr.com',                 # 36氪
        'https://www.smzdm.com',            # 什么值得买
        'https://www.coolapk.com',          # 酷安
        
        # 高风险 - 强防护（可能需要绕过）
        'https://www.tianyancha.com',       # 天眼查
        'https://www.qcc.com',              # 企查查
        'https://www.xiaohongshu.com',      # 小红书
    ]
    
    # 爬虫设置
    custom_settings = {
        'CONCURRENT_REQUESTS': 1,  # 并发请求数（避免被封）
        'DOWNLOAD_DELAY': 3,       # 下载延迟（秒）
        'RANDOMNESS': True,        # 启用随机延迟
        'RANDOM_RANGE': [2, 5],    # 随机延迟范围
        
        # Cloudflare 绕过配置
        'CLOUDFLARE_BYPASS_MAX_RETRIES': 2,
        'CLOUDFLARE_BYPASS_DOWNLOADER': 'camoufox',
        
        # 日志设置
        'LOG_LEVEL': 'INFO',
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results = []
        self.test_count = 0
    
    def start_requests(self):
        """生成初始请求"""
        self.logger.info(f"开始测试 {len(self.start_urls)} 个国内网站")
        self.logger.info("=" * 80)
        self.logger.info("⚠️  所有网站均可在中国大陆正常访问")
        self.logger.info("=" * 80)
        
        for url in self.start_urls:
            self.test_count += 1
            # 添加时间戳避免去重
            timestamp = int(time.time() * 1000) + self.test_count
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    'test_index': self.test_count,
                    'test_url': url,
                    'dont_filter': True,
                    '_timestamp': timestamp,  # 唯一标识
                },
                dont_filter=True,  # 在 Request 级别也设置
            )
    
    async def parse(self, response: Response):
        """解析响应"""
        test_index = response.meta.get('test_index', 0)
        test_url = response.meta.get('test_url', response.url)
        
        # 提取域名
        from urllib.parse import urlparse
        domain = urlparse(test_url).netloc
        
        # 检测 Cloudflare 特征
        cf_indicators = self._detect_cloudflare(response)
        
        # 记录结果
        result = {
            'index': test_index,
            'url': test_url,
            'domain': domain,
            'status_code': response.status_code,
            'has_cloudflare': cf_indicators['has_cloudflare'],
            'cf_features': cf_indicators['features'],
            'response_size': len(response.body) if response.body else 0,
            'cf_bypass_count': response.meta.get('cloudflare_bypass_count', 0),
        }
        
        self.results.append(result)
        
        # 打印测试结果
        self._print_test_result(result)
    
    def _detect_cloudflare(self, response: Response) -> dict:
        """检测 Cloudflare 特征"""
        features = []
        
        # 1. 检查状态码
        if response.status_code in [403, 503, 520, 521, 522, 523, 524]:
            features.append(f'状态码: {response.status_code}')
        
        # 2. 检查响应头
        headers = response.headers if response.headers else {}
        if 'cf-ray' in headers:
            features.append('cf-ray 头')
        if 'cf-cache-status' in headers:
            features.append('cf-cache-status 头')
        if headers.get('server', '').lower() == 'cloudflare':
            features.append('server: cloudflare')
        
        # 3. 检查响应内容
        body_text = ''
        if response.body:
            if isinstance(response.body, bytes):
                body_text = response.body.decode('utf-8', errors='ignore').lower()
            else:
                body_text = str(response.body).lower()
        
        cf_keywords = [
            'cf_chl_opt',
            'challenge-platform',
            'just a moment',
            'checking your browser',
            'cf_clearance',
            'turnstile',
            'verify you are a human',
        ]
        
        for keyword in cf_keywords:
            if keyword in body_text:
                features.append(f'内容特征: {keyword}')
        
        return {
            'has_cloudflare': len(features) > 0,
            'features': features
        }
    
    def _print_test_result(self, result: dict):
        """打印测试结果"""
        print("\n" + "=" * 80)
        print(f"测试 [{result['index']}] 结果")
        print("=" * 80)
        print(f"URL: {result['url']}")
        print(f"域名: {result['domain']}")
        print(f"状态码: {result['status_code']}")
        print(f"响应大小: {result['response_size']:,} bytes ({result['response_size']/1024:.1f} KB)")
        
        if result['has_cloudflare']:
            print(f"Cloudflare: ✅ 检测到")
            print(f"特征列表:")
            for feature in result['cf_features']:
                print(f"  - {feature}")
            
            if result['cf_bypass_count'] > 0:
                print(f"绕过次数: {result['cf_bypass_count']}")
        else:
            print(f"Cloudflare: ❌ 未检测到挑战页面")
        
        print("-" * 80)
    
    async def closed(self, reason):
        """爬虫关闭时的处理"""
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        
        if not self.results:
            print("⚠️  没有测试结果")
            return
        
        # 统计
        total = len(self.results)
        cf_detected = sum(1 for r in self.results if r['has_cloudflare'])
        cf_bypassed = sum(1 for r in self.results if r['cf_bypass_count'] > 0)
        success = sum(1 for r in self.results if r['status_code'] == 200)
        failed = sum(1 for r in self.results if r['status_code'] >= 400)
        
        print(f"\n📈 总体统计:")
        print(f"   总测试网站数: {total}")
        print(f"   成功访问: {success} ({success/total*100:.1f}%)")
        print(f"   访问失败: {failed} ({failed/total*100:.1f}%)")
        print(f"   检测到 Cloudflare: {cf_detected} ({cf_detected/total*100:.1f}%)")
        print(f"   成功绕过: {cf_bypassed}")
        
        print(f"\n📋 详细结果:")
        print("-" * 100)
        print(f"{'序号':<5} {'域名':<25} {'状态码':<8} {'Cloudflare':<12} {'绕过':<8} {'响应大小':<12}")
        print("-" * 100)
        
        for r in self.results:
            cf_status = '✅ 是' if r['has_cloudflare'] else '❌ 否'
            bypass_status = f"{r['cf_bypass_count']}次" if r['cf_bypass_count'] > 0 else '-'
            size_str = f"{r['response_size']/1024:.1f} KB"
            print(f"{r['index']:<5} {r['domain']:<25} {r['status_code']:<8} {cf_status:<12} {bypass_status:<8} {size_str:<12}")
        
        print("=" * 100)
        
        # 分类统计
        print(f"\n🔍 按防护强度分类:")
        
        # 无 Cloudflare
        no_cf = [r for r in self.results if not r['has_cloudflare'] and r['status_code'] == 200]
        if no_cf:
            print(f"\n   ✅ 无 Cloudflare 防护（可直接访问）:")
            for r in no_cf:
                print(f"      - {r['domain']}")
        
        # 有 Cloudflare 但未触发挑战
        cf_no_challenge = [r for r in self.results if r['has_cloudflare'] and r['cf_bypass_count'] == 0 and r['status_code'] == 200]
        if cf_no_challenge:
            print(f"\n   ⚡ 有 Cloudflare CDN（未触发挑战）:")
            for r in cf_no_challenge:
                print(f"      - {r['domain']} ({', '.join(r['cf_features'][:2])})")
        
        # 成功绕过
        cf_bypassed = [r for r in self.results if r['cf_bypass_count'] > 0]
        if cf_bypassed:
            print(f"\n   🛡️  Cloudflare 挑战（已成功绕过）:")
            for r in cf_bypassed:
                print(f"      - {r['domain']} (绕过 {r['cf_bypass_count']} 次)")
        
        print("\n" + "=" * 80)
        print(f"爬虫关闭原因: {reason}")
        print("=" * 80)


def main():
    """主函数"""
    import asyncio
    from crawlo.crawler import CrawlerProcess
    
    # 运行爬虫
    print("\n" + "=" * 80)
    print("Crawlo Cloudflare 防护国内网站测试")
    print("=" * 80)
    print("\n✅ 测试说明:")
    print("   1. 所有测试网站均可在中国大陆正常访问")
    print("   2. 测试 Cloudflare 检测和绕过能力")
    print("   3. 已设置合理延迟，避免对服务器造成压力")
    print("   4. 测试 CloudflareBypassMiddleware 的自动绕过功能")
    print()
    
    # 使用 CrawlerProcess 运行爬虫
    process = CrawlerProcess()
    asyncio.run(process.crawl(ChinaCloudflareTestSpider))


if __name__ == '__main__':
    main()
