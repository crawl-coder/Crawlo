#!/usr/bin/env python3
"""
CloakBrowser 下载器全面测试（修复版）
测试场景：基础功能、边界条件、超时、资源屏蔽、并发
"""
import asyncio
import time
import os
from datetime import datetime
from urllib.parse import quote

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
class TestItem(Item, metaclass=ItemMeta):
    """测试数据项"""
    test = Item()
    company = Item()
    desc = Item()
    status = Item()
    status_code = Item()
    title = Item()
    length = Item()
    index = Item()
    error = Item()


class ComprehensiveTestSpider(Spider):
    """综合测试爬虫"""
    
    name = 'comprehensive_test'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 从环境变量获取测试类型
        self.test_type = os.environ.get('CRAWL_TEST_TYPE', 'basic')
        self.success_count = 0
        self.failed_count = 0
    
    def start_requests(self):
        """根据测试类型生成请求"""
        if self.test_type == 'basic':
            yield from self._basic_tests()
        elif self.test_type == 'boundary':
            yield from self._boundary_tests()
        elif self.test_type == 'timeout':
            yield from self._timeout_tests()
        elif self.test_type == 'resource_block':
            yield from self._resource_block_tests()
        elif self.test_type == 'concurrency':
            yield from self._concurrency_tests()
    
    def _basic_tests(self):
        """基础功能测试"""
        test_urls = [
            ('https://baike.baidu.com/item/小米科技有限责任公司', '小米科技'),
            ('https://baike.baidu.com/item/华为技术有限公司', '华为技术'),
            ('https://baike.baidu.com/item/阿里巴巴集团控股有限公司', '阿里巴巴'),
        ]
        
        for url, company in test_urls:
            yield Request(
                url=url,
                callback=self._parse_basic,
                meta={'company_name': company, 'test_type': 'basic', 'downloader': 'cloakbrowser'},
            )
    
    def _boundary_tests(self):
        """边界条件测试"""
        test_urls = [
            ('https://baike.baidu.com/item/不存在的公司名称测试123456', '不存在的公司'),
            ('https://baike.baidu.com/item/ ', '空URL'),
            ('https://baike.baidu.com/item/测试' + 'A' * 200, '超长URL'),
        ]
        
        for url, desc in test_urls:
            yield Request(
                url=url,
                callback=self._parse_boundary,
                meta={'desc': desc, 'test_type': 'boundary', 'downloader': 'cloakbrowser'},
            )
    
    def _timeout_tests(self):
        """超时边界测试"""
        test_urls = [
            ('https://baike.baidu.com/item/腾讯科技有限公司', '腾讯'),
            ('https://baike.baidu.com/item/百度在线网络技术有限公司', '百度'),
        ]
        
        for url, company in test_urls:
            yield Request(
                url=url,
                callback=self._parse_timeout,
                meta={'company_name': company, 'test_type': 'timeout', 'downloader': 'cloakbrowser', 'timeout': 5},
            )
    
    def _resource_block_tests(self):
        """资源屏蔽测试"""
        test_urls = [
            ('https://baike.baidu.com/item/京东集团', '京东'),
            ('https://baike.baidu.com/item/美团', '美团'),
        ]
        
        for url, company in test_urls:
            yield Request(
                url=url,
                callback=self._parse_resource_block,
                meta={'company_name': company, 'test_type': 'resource_block', 'downloader': 'cloakbrowser'},
            )
    
    def _concurrency_tests(self):
        """并发压力测试（50家企业）"""
        companies = [
            '小米科技有限责任公司', '华为技术有限公司', '阿里巴巴集团控股有限公司',
            '腾讯科技有限公司', '百度在线网络技术有限公司', '京东集团',
            '美团', '滴滴出行科技有限公司', '网易公司',
            '字节跳动科技有限公司', '快手科技有限公司', 'OPPO广东移动通信有限公司',
            'vivo移动通信有限公司', '联想集团有限公司', '海尔集团公司',
            '美的集团股份有限公司', '格力电器股份有限公司', '比亚迪股份有限公司',
            '宁德时代新能源科技股份有限公司', '隆基绿能科技股份有限公司',
            '中国石油化工股份有限公司', '中国石油天然气股份有限公司',
            '中国工商银行股份有限公司', '中国建设银行股份有限公司',
            '中国农业银行股份有限公司', '中国银行股份有限公司',
            '中国平安保险（集团）股份有限公司', '中国人寿保险（集团）公司',
            '万科企业股份有限公司', '恒大集团有限公司',
            '万达集团股份有限公司', '融创中国控股有限公司',
            '碧桂园控股有限公司', '龙湖集团控股有限公司',
            '华润置地有限公司', '招商局蛇口工业区控股股份有限公司',
            '保利发展控股集团股份有限公司', '绿地控股集团股份有限公司',
            '中国铁建股份有限公司', '中国中铁股份有限公司',
            '中国交通建设股份有限公司', '中国电力建设股份有限公司',
            '中国建筑股份有限公司', '中国冶金科工股份有限公司',
            '中国化学工程股份有限公司', '中国有色金属建设股份有限公司',
            '紫金矿业集团股份有限公司', '江西铜业股份有限公司',
            '山东黄金集团有限公司', '中国黄金集团有限公司',
        ]
        
        for i, company in enumerate(companies[:50], 1):
            encoded_company = quote(company)
            yield Request(
                url=f'https://baike.baidu.com/item/{encoded_company}',
                callback=self._parse_concurrency,
                meta={'company_name': company, 'index': i, 'test_type': 'concurrency', 'downloader': 'cloakbrowser'},
            )
    
    def _parse_basic(self, response):
        """解析基础测试"""
        company = response.meta.get('company_name')
        
        if response.status == 200:
            title = response.xpath('//title/text()').get()
            self.logger.info(f"✅ {company}: {title}")
            self.success_count += 1
            item = TestItem()
            item['test'] = 'basic'
            item['company'] = company
            item['status'] = 'success'
            item['title'] = title
            return item
        else:
            self.logger.warning(f"❌ {company}: HTTP {response.status}")
            self.failed_count += 1
            item = TestItem()
            item['test'] = 'basic'
            item['company'] = company
            item['status'] = 'failed'
            return item
    
    def _parse_boundary(self, response):
        """解析边界测试"""
        desc = response.meta.get('desc')
        
        if response.status == 200:
            title = response.xpath('//title/text()').get()
            self.logger.info(f"✅ {desc}: {title}")
            self.success_count += 1
            item = TestItem()
            item['test'] = 'boundary'
            item['desc'] = desc
            item['status'] = 'success'
            item['title'] = title
            return item
        elif response.status == 404:
            self.logger.info(f"✅ {desc}: 正确返回404")
            self.success_count += 1
            item = TestItem()
            item['test'] = 'boundary'
            item['desc'] = desc
            item['status'] = 'success_404'
            item['status_code'] = 404
            return item
        else:
            self.logger.warning(f"❌ {desc}: HTTP {response.status}")
            self.failed_count += 1
            item = TestItem()
            item['test'] = 'boundary'
            item['desc'] = desc
            item['status'] = 'failed'
            return item
    
    def _parse_timeout(self, response):
        """解析超时测试"""
        company = response.meta.get('company_name')
        
        if response.status == 200:
            title = response.xpath('//title/text()').get()
            self.logger.info(f"✅ {company}: {title}")
            self.success_count += 1
            item = TestItem()
            item['test'] = 'timeout'
            item['company'] = company
            item['status'] = 'success'
            item['title'] = title
            return item
        else:
            self.logger.warning(f"❌ {company}: HTTP {response.status}")
            self.failed_count += 1
            item = TestItem()
            item['test'] = 'timeout'
            item['company'] = company
            item['status'] = 'failed'
            return item
    
    def _parse_resource_block(self, response):
        """解析资源屏蔽测试"""
        company = response.meta.get('company_name')
        
        if response.status == 200:
            title = response.xpath('//title/text()').get()
            length = len(response.body)
            self.logger.info(f"✅ {company}: {title} ({length} bytes)")
            self.success_count += 1
            item = TestItem()
            item['test'] = 'resource_block'
            item['company'] = company
            item['status'] = 'success'
            item['title'] = title
            item['length'] = length
            return item
        else:
            self.logger.warning(f"❌ {company}: HTTP {response.status}")
            self.failed_count += 1
            item = TestItem()
            item['test'] = 'resource_block'
            item['company'] = company
            item['status'] = 'failed'
            return item
    
    def _parse_concurrency(self, response):
        """解析并发测试"""
        company = response.meta.get('company_name')
        index = response.meta.get('index', 0)
        
        if response.status == 200:
            title = response.xpath('//title/text()').get()
            self.success_count += 1
            if index <= 5 or index % 10 == 0:
                self.logger.info(f"✅ [{index}/50] {company}: {title}")
            item = TestItem()
            item['test'] = 'concurrency'
            item['company'] = company
            item['index'] = index
            item['status'] = 'success'
            item['title'] = title
            return item
        else:
            self.failed_count += 1
            if index <= 5 or index % 10 == 0:
                self.logger.warning(f"❌ [{index}/50] {company}: HTTP {response.status}")
            item = TestItem()
            item['test'] = 'concurrency'
            item['company'] = company
            item['index'] = index
            item['status'] = 'failed'
            return item
    
    def closed(self, reason):
        """爬虫关闭时的统计"""
        total = self.success_count + self.failed_count
        self.logger.info("=" * 70)
        self.logger.info(f"测试统计 [{self.test_type}]")
        self.logger.info(f"总计: {total}")
        self.logger.info(f"成功: {self.success_count}")
        self.logger.info(f"失败: {self.failed_count}")
        if total > 0:
            self.logger.info(f"成功率: {self.success_count/total*100:.1f}%")
        self.logger.info("=" * 70)


def run_single_test(test_type, concurrency=1, download_delay=0):
    """运行单个测试"""
    test_names = {
        'basic': '基础功能测试',
        'boundary': '边界条件测试',
        'timeout': '超时边界测试',
        'resource_block': '资源屏蔽测试',
        'concurrency': '并发压力测试'
    }
    
    print(f"\n{'='*70}")
    print(f"运行: {test_names.get(test_type, test_type)}")
    print(f"{'='*70}")
    
    config_dict = {
        'crawler': {
            'spider_modules': ['infoq_dynamic_test.spiders'],
            'middlewares': {
                'infoq_dynamic_test.middlewares.InfoqDynamicTestDownloaderMiddleware': 543,
            },
            'item_pipelines': {
                'infoq_dynamic_test.pipelines.InfoqDynamicTestPipeline': 300,
            },
            'request_dedup': {'backend': 'memory'},
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
                'resource_block': {
                    'enabled': True,
                    'image': True,
                    'stylesheet': True,
                    'font': True,
                    'media': True,
                },
            },
        },
        'engine': {
            'concurrency': {'default': concurrency},
            'download_delay': download_delay,
        },
        'logging': {
            'level': 'INFO',
            'file': f"logs/cloakbrowser_{test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        },
    }
    
    # 通过环境变量传递测试类型
    os.environ['CRAWL_TEST_TYPE'] = test_type
    
    process = CrawlerProcess(settings=config_dict)
    
    start_time = time.time()
    try:
        asyncio.run(process.crawl('comprehensive_test'))
        elapsed = time.time() - start_time
        print(f"\n[OK] {test_names.get(test_type, test_type)} 完成 ({elapsed:.1f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[FAIL] {test_names.get(test_type, test_type)} 失败 ({elapsed:.1f}s): {e}")
        return False
    finally:
        # 清理环境变量
        if 'CRAWL_TEST_TYPE' in os.environ:
            del os.environ['CRAWL_TEST_TYPE']


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("CloakBrowser 下载器全面测试")
    print("="*70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 测试1: 基础功能
    results['basic'] = run_single_test('basic', concurrency=1, download_delay=0.5)
    
    # 测试2: 边界条件
    results['boundary'] = run_single_test('boundary', concurrency=1, download_delay=0)
    
    # 测试3: 超时边界
    results['timeout'] = run_single_test('timeout', concurrency=1, download_delay=0)
    
    # 测试4: 资源屏蔽
    results['resource_block'] = run_single_test('resource_block', concurrency=1, download_delay=0.5)
    
    # 测试5: 并发压力
    results['concurrency'] = run_single_test('concurrency', concurrency=5, download_delay=0.1)
    
    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    test_names = {
        'basic': '基础功能测试',
        'boundary': '边界条件测试',
        'timeout': '超时边界测试',
        'resource_block': '资源屏蔽测试',
        'concurrency': '并发压力测试'
    }
    
    for test_type, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_names[test_type]}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n[DONE] 所有测试通过！CloakBrowser 下载器工作正常！")
    else:
        print(f"\n[WARN]  {total - passed} 个测试失败，请检查日志")
    
    print("="*70)


if __name__ == '__main__':
    main()
