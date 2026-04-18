#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare 防护真实网站测试爬虫
=================================

使用 Crawlo 框架测试真实 Cloudflare 防护网站的检测和绕过能力。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.network.response import Response


class CloudflareTestSpider(Spider):
    """
    Cloudflare 防护测试爬虫
    
    测试多个已知使用 Cloudflare 的网站，验证框架的自动检测和绕过能力。
    """
    
    name = 'cloudflare_test'
    
    # 测试网站列表
    start_urls = [
        # 低风险网站
        'https://archive.org',
        'https://www.reuters.com',
        
        # 中等风险
        'https://techcrunch.com',
        'https://www.glassdoor.com',
        
        # 高风险网站
        'https://www.crunchbase.com',
        'https://www.bloomberg.com',
    ]
    
    # 爬虫设置
    custom_settings = {
        'CONCURRENT_REQUESTS': 1,  # 并发请求数（避免被封）
        'DOWNLOAD_DELAY': 2,       # 下载延迟（秒）
        'RANDOMNESS': True,        # 启用随机延迟
        'RANDOM_RANGE': [1, 3],    # 随机延迟范围
        
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
        import time
        self.logger.info(f"开始测试 {len(self.start_urls)} 个网站")
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
        print(f"响应大小: {result['response_size']:,} bytes")
        
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
        
        print(f"\n总测试网站数: {total}")
        print(f"成功访问: {success} ({success/total*100:.1f}%)")
        print(f"检测到 Cloudflare: {cf_detected} ({cf_detected/total*100:.1f}%)")
        print(f"成功绕过: {cf_bypassed}")
        
        print(f"\n详细结果:")
        print("-" * 80)
        print(f"{'序号':<5} {'域名':<30} {'状态码':<8} {'Cloudflare':<12} {'绕过':<6}")
        print("-" * 80)
        
        for r in self.results:
            cf_status = '✅ 是' if r['has_cloudflare'] else '❌ 否'
            bypass_status = f"{r['cf_bypass_count']}次" if r['cf_bypass_count'] > 0 else '-'
            print(f"{r['index']:<5} {r['domain']:<30} {r['status_code']:<8} {cf_status:<12} {bypass_status:<6}")
        
        print("=" * 80)
        print(f"爬虫关闭原因: {reason}")
        print("=" * 80)


def main():
    """主函数"""
    import asyncio
    from crawlo.crawler import CrawlerProcess
    
    # 运行爬虫
    print("\n" + "=" * 80)
    print("Crawlo Cloudflare 防护真实网站测试")
    print("=" * 80)
    print("\n⚠️  免责声明：")
    print("   1. 本测试仅用于验证框架功能")
    print("   2. 请遵守目标网站的使用条款")
    print("   3. 已设置合理延迟，避免对服务器造成压力")
    print("   4. 网站防护策略可能随时变化")
    print()
    
    # 使用 CrawlerProcess 运行爬虫
    process = CrawlerProcess()
    asyncio.run(process.crawl(CloudflareTestSpider))


if __name__ == '__main__':
    main()
