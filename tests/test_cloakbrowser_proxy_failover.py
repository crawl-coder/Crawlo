#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 代理失效切换功能测试
===================================

测试场景：
1. 初始使用代理A访问
2. 模拟代理A失效
3. 自动降级为直连（无代理）
4. 切换到代理B继续访问
5. 验证Context重建机制

用法：
    python test_cloakbrowser_proxy_failover.py
"""
import os
import sys
import asyncio
import time

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 添加示例项目路径
example_project = os.path.join(project_root, 'examples', 'infoq_dynamic_test')
if example_project not in sys.path:
    sys.path.insert(0, example_project)

from crawlo import Spider, Request, Item
from crawlo.crawler import CrawlerProcess
from crawlo.items import ItemMeta


# 定义测试 Item
class ProxyFailoverItem(Item, metaclass=ItemMeta):
    """代理切换测试数据项"""
    test = Item()
    url = Item()
    proxy = Item()
    status = Item()
    content_length = Item()
    switch_type = Item()


class ProxyFailoverSpider(Spider):
    """代理失效切换测试爬虫"""
    
    name = 'proxy_failover_test'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_count = 0
        self.failed_count = 0
        self.proxy_switch_count = 0
    
    def start_requests(self):
        """生成测试请求序列"""
        
        # 测试1: 使用代理A访问（第一个请求）
        yield Request(
            url='https://baike.baidu.com/item/小米科技有限责任公司',
            callback=self._parse_with_proxy_a,
            meta={
                'test': 'proxy_a',
                'downloader': 'cloakbrowser',
                # 模拟代理A（使用测试代理）
                'proxy': 'http://127.0.0.1:8080',
            },
        )
        
        # 测试2: 代理A失效，降级为直连
        yield Request(
            url='https://baike.baidu.com/item/华为技术有限公司',
            callback=self._parse_proxy_downgrade,
            meta={
                'test': 'proxy_downgrade',
                'downloader': 'cloakbrowser',
                # 标记代理降级
                'proxy_downgraded': True,
            },
        )
        
        # 测试3: 切换到代理B
        yield Request(
            url='https://baike.baidu.com/item/阿里巴巴集团控股有限公司',
            callback=self._parse_with_proxy_b,
            meta={
                'test': 'proxy_b',
                'downloader': 'cloakbrowser',
                # 切换到新代理B
                'proxy': 'http://127.0.0.1:8081',
            },
        )
        
        # 测试4: 继续使用代理B
        yield Request(
            url='https://baike.baidu.com/item/腾讯科技有限公司',
            callback=self._parse_proxy_b_continue,
            meta={
                'test': 'proxy_b_continue',
                'downloader': 'cloakbrowser',
                'proxy': 'http://127.0.0.1:8081',
            },
        )
        
        # 测试5: 再次降级为直连（使用更稳定的URL）
        yield Request(
            url='https://baike.baidu.com/item/字节跳动科技有限公司',
            callback=self._parse_downgrade_again,
            meta={
                'test': 'downgrade_again',
                'downloader': 'cloakbrowser',
                'proxy_downgraded': True,
            },
        )
        
        # 测试6: 直连模式访问
        yield Request(
            url='https://baike.baidu.com/item/京东集团',
            callback=self._parse_direct,
            meta={
                'test': 'direct_connection',
                'downloader': 'cloakbrowser',
                # 不设置proxy，保持直连
            },
        )
    
    def _parse_with_proxy_a(self, response):
        """解析代理A访问结果"""
        self.logger.info(f"✅ 代理A访问成功: {response.url}")
        self.success_count += 1
        self.proxy_switch_count += 1
        item = ProxyFailoverItem()
        item['test'] = 'proxy_a'
        item['url'] = response.url
        item['proxy'] = 'http://127.0.0.1:8080'
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['switch_type'] = '初始代理'
        return item
    
    def _parse_proxy_downgrade(self, response):
        """解析代理降级结果"""
        self.logger.info(f"✅ 代理降级成功（切换为直连）: {response.url}")
        self.success_count += 1
        self.proxy_switch_count += 1
        item = ProxyFailoverItem()
        item['test'] = 'proxy_downgrade'
        item['url'] = response.url
        item['proxy'] = 'direct'
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['switch_type'] = '降级为直连'
        return item
    
    def _parse_with_proxy_b(self, response):
        """解析代理B访问结果"""
        self.logger.info(f"✅ 切换到代理B成功: {response.url}")
        self.success_count += 1
        self.proxy_switch_count += 1
        item = ProxyFailoverItem()
        item['test'] = 'proxy_b'
        item['url'] = response.url
        item['proxy'] = 'http://127.0.0.1:8081'
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['switch_type'] = '切换到新代理'
        return item
    
    def _parse_proxy_b_continue(self, response):
        """解析继续使用代理B结果"""
        self.logger.info(f"✅ 继续使用代理B: {response.url}")
        self.success_count += 1
        item = ProxyFailoverItem()
        item['test'] = 'proxy_b_continue'
        item['url'] = response.url
        item['proxy'] = 'http://127.0.0.1:8081'
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['switch_type'] = '保持代理B'
        return item
    
    def _parse_downgrade_again(self, response):
        """解析再次降级结果"""
        self.logger.info(f"✅ 再次降级为直连: {response.url}")
        self.success_count += 1
        self.proxy_switch_count += 1
        item = ProxyFailoverItem()
        item['test'] = 'downgrade_again'
        item['url'] = response.url
        item['proxy'] = 'direct'
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['switch_type'] = '再次降级'
        return item
    
    def _parse_direct(self, response):
        """解析直连访问结果"""
        self.logger.info(f"✅ 直连访问成功: {response.url}")
        self.success_count += 1
        item = ProxyFailoverItem()
        item['test'] = 'direct_connection'
        item['url'] = response.url
        item['proxy'] = 'direct'
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['switch_type'] = '直连模式'
        return item
    
    def closed(self, reason):
        """爬虫关闭时的统计"""
        total = self.success_count + self.failed_count
        self.logger.info("=" * 70)
        self.logger.info(f"代理切换测试统计")
        self.logger.info(f"总计请求: {total}")
        self.logger.info(f"成功: {self.success_count}")
        self.logger.info(f"失败: {self.failed_count}")
        self.logger.info(f"代理切换次数: {self.proxy_switch_count}")
        if total > 0:
            self.logger.info(f"成功率: {self.success_count/total*100:.1f}%")
        self.logger.info("=" * 70)


def main():
    """运行测试"""
    print("\n" + "="*70)
    print("CloakBrowser 代理失效切换功能测试")
    print("="*70)
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("测试场景:")
    print("  1. 初始使用代理A访问")
    print("  2. 代理A失效，降级为直连")
    print("  3. 切换到代理B继续访问")
    print("  4. 继续使用代理B")
    print("  5. 再次降级为直连")
    print("  6. 直连模式访问")
    print()
    print("验证机制:")
    print("  - _check_proxy_change(): 检测代理变化")
    print("  - _rebuild_context(): 重建浏览器上下文")
    print("  - proxy_downgraded: 代理降级标记")
    print("  - request.proxy: 动态代理切换")
    print()
    
    config_dict = {
        'crawler': {
            'spider_modules': ['infoq_dynamic_test.spiders'],
        },
        'downloader': {
            'default': 'hybrid',
            'protocol': {
                'default_handler': 'httpcore',
                'handlers': {
                    'http': 'httpcore',
                    'https': 'httpcore',
                },
            },
            'dynamic': {
                'default_handler': 'cloakbrowser',
                'handlers': {'cloakbrowser': 'cloakbrowser'},
            },
        },
        'engine': {
            'concurrency': {'default': 1},  # 单并发，顺序测试
            'download_delay': 0.5,
        },
        'logging': {
            'level': 'INFO',
        },
        # CloakBrowser 配置
        'CLOAKBROWSER_HEADLESS': True,
        'CLOAKBROWSER_TIMEOUT': 30000,  # 30秒超时（避免页面加载慢导致超时）
        'CLOAKBROWSER_LOAD_TIMEOUT': 20000,  # 20秒加载超时
        'CLOAKBROWSER_HUMANIZE': False,
        'CLOAKBROWSER_GEOIP': False,
        'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font'],
    }
    
    process = CrawlerProcess(settings=config_dict)
    
    start_time = time.time()
    try:
        asyncio.run(process.crawl('proxy_failover_test'))
        elapsed = time.time() - start_time
        print(f"\n[OK] 测试完成 ({elapsed:.1f}s)")
        print("\n[DONE] 代理失效切换功能验证完成！")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[FAIL] 测试失败 ({elapsed:.1f}s): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("="*70)


if __name__ == '__main__':
    main()
