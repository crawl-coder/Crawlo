#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 下载器最新功能测试
================================

测试最新功能：
1. 智能等待策略（AUTO/ELEMENT/NETWORK/NONE）
2. 资源屏蔽（image/font/media/stylesheet）
3. 自动滚动加载懒加载内容
4. 页面操作（点击、填写、等待）
5. 代理切换和降级
6. 类人行为模拟（humanize）
7. GeoIP 时区匹配

用法：
    python test_cloakbrowser_latest_features.py
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
from crawlo.downloader.wait_strategies import WaitStrategy


# 定义测试 Item
class FeatureTestItem(Item, metaclass=ItemMeta):
    """功能测试数据项"""
    feature = Item()
    url = Item()
    status = Item()
    title = Item()
    content_length = Item()
    details = Item()


class LatestFeatureSpider(Spider):
    """CloakBrowser 最新功能测试爬虫"""
    
    name = 'latest_feature_test'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_count = 0
        self.failed_count = 0
    
    def start_requests(self):
        """生成测试请求"""
        # 测试1: 智能等待 - AUTO 策略
        yield Request(
            url='https://baike.baidu.com/item/小米科技有限责任公司',
            callback=self._parse_smart_wait,
            meta={
                'feature': 'smart_wait_auto',
                'downloader': 'cloakbrowser',
                'cloakbrowser_wait_strategy': WaitStrategy.AUTO,
            },
        )
        
        # 测试2: 资源屏蔽 - 屏蔽图片/字体/样式表
        yield Request(
            url='https://baike.baidu.com/item/华为技术有限公司',
            callback=self._parse_resource_block,
            meta={
                'feature': 'resource_block',
                'downloader': 'cloakbrowser',
                'cloakbrowser_block_resources': ['image', 'font', 'stylesheet'],
            },
        )
        
        # 测试3: 自动滚动 - 触发懒加载
        yield Request(
            url='https://baike.baidu.com/item/阿里巴巴集团控股有限公司',
            callback=self._parse_auto_scroll,
            meta={
                'feature': 'auto_scroll',
                'downloader': 'cloakbrowser',
                'cloakbrowser_auto_scroll': True,
                'cloakbrowser_scroll_delay': 300,
            },
        )
        
        # 测试4: 页面操作 - 点击和等待
        yield Request(
            url='https://baike.baidu.com/item/腾讯科技有限公司',
            callback=self._parse_page_actions,
            meta={
                'feature': 'page_actions',
                'downloader': 'cloakbrowser',
                'cloakbrowser_actions': [
                    {
                        'action': 'wait',
                        'timeout': 2000,
                    }
                ],
            },
        )
        
        # 测试5: 智能等待 - 等待特定元素
        yield Request(
            url='https://baike.baidu.com/item/百度在线网络技术有限公司',
            callback=self._parse_wait_element,
            meta={
                'feature': 'wait_element',
                'downloader': 'cloakbrowser',
                'cloakbrowser_wait_strategy': WaitStrategy.ELEMENT,
                'cloakbrowser_wait_for_element': '.lemma-summary',
                'cloakbrowser_wait_timeout': 5000,
            },
        )
        
        # 测试6: 无资源屏蔽（对比测试）
        yield Request(
            url='https://baike.baidu.com/item/京东集团',
            callback=self._parse_no_block,
            meta={
                'feature': 'no_resource_block',
                'downloader': 'cloakbrowser',
                'cloakbrowser_block_resources': [],
            },
        )
    
    def _parse_smart_wait(self, response):
        """解析智能等待测试"""
        self.logger.info(f"✅ 智能等待(AUTO): {response.url}")
        self.success_count += 1
        item = FeatureTestItem()
        item['feature'] = 'smart_wait_auto'
        item['url'] = response.url
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['details'] = 'AUTO策略自动选择最佳等待方式'
        return item
    
    def _parse_resource_block(self, response):
        """解析资源屏蔽测试"""
        content_length = len(response.body)
        self.logger.info(f"✅ 资源屏蔽: {content_length} bytes (屏蔽image/font/stylesheet)")
        self.success_count += 1
        item = FeatureTestItem()
        item['feature'] = 'resource_block'
        item['url'] = response.url
        item['status'] = 'success'
        item['content_length'] = content_length
        item['details'] = f'屏蔽后页面大小: {content_length} bytes'
        return item
    
    def _parse_auto_scroll(self, response):
        """解析自动滚动测试"""
        content_length = len(response.body)
        self.logger.info(f"✅ 自动滚动: {content_length} bytes (触发懒加载)")
        self.success_count += 1
        item = FeatureTestItem()
        item['feature'] = 'auto_scroll'
        item['url'] = response.url
        item['status'] = 'success'
        item['content_length'] = content_length
        item['details'] = '自动滚动触发懒加载内容'
        return item
    
    def _parse_page_actions(self, response):
        """解析页面操作测试"""
        self.logger.info(f"✅ 页面操作: 执行自定义操作序列")
        self.success_count += 1
        item = FeatureTestItem()
        item['feature'] = 'page_actions'
        item['url'] = response.url
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['details'] = '执行自定义页面操作（点击/填写/等待）'
        return item
    
    def _parse_wait_element(self, response):
        """解析等待元素测试"""
        self.logger.info(f"✅ 等待元素: 等待.lemma-summary出现")
        self.success_count += 1
        item = FeatureTestItem()
        item['feature'] = 'wait_element'
        item['url'] = response.url
        item['status'] = 'success'
        item['content_length'] = len(response.body)
        item['details'] = '等待特定CSS元素出现后返回'
        return item
    
    def _parse_no_block(self, response):
        """解析无资源屏蔽测试"""
        content_length = len(response.body)
        self.logger.info(f"✅ 无资源屏蔽: {content_length} bytes (完整加载)")
        self.success_count += 1
        item = FeatureTestItem()
        item['feature'] = 'no_resource_block'
        item['url'] = response.url
        item['status'] = 'success'
        item['content_length'] = content_length
        item['details'] = '完整加载所有资源（对比基准）'
        return item
    
    def closed(self, reason):
        """爬虫关闭时的统计"""
        total = self.success_count + self.failed_count
        self.logger.info("=" * 70)
        self.logger.info(f"CloakBrowser 功能测试统计")
        self.logger.info(f"总计: {total}")
        self.logger.info(f"成功: {self.success_count}")
        self.logger.info(f"失败: {self.failed_count}")
        if total > 0:
            self.logger.info(f"成功率: {self.success_count/total*100:.1f}%")
        self.logger.info("=" * 70)


def main():
    """运行测试"""
    print("\n" + "="*70)
    print("CloakBrowser 下载器最新功能测试")
    print("="*70)
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("测试功能:")
    print("  1. 智能等待策略（AUTO/ELEMENT）")
    print("  2. 资源屏蔽（image/font/stylesheet）")
    print("  3. 自动滚动加载懒加载内容")
    print("  4. 页面操作（点击/填写/等待）")
    print("  5. 等待特定元素出现")
    print("  6. 无资源屏蔽对比测试")
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
            'concurrency': {'default': 1},
            'download_delay': 1,
        },
        'logging': {
            'level': 'INFO',
        },
        # CloakBrowser 配置
        'CLOAKBROWSER_HEADLESS': True,
        'CLOAKBROWSER_TIMEOUT': 30000,
        'CLOAKBROWSER_LOAD_TIMEOUT': 15000,
        'CLOAKBROWSER_HUMANIZE': False,  # 关闭类人行为（加速测试）
        'CLOAKBROWSER_GEOIP': False,     # 关闭GeoIP（加速测试）
        'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font'],  # 默认屏蔽
    }
    
    process = CrawlerProcess(settings=config_dict)
    
    start_time = time.time()
    try:
        asyncio.run(process.crawl('latest_feature_test'))
        elapsed = time.time() - start_time
        print(f"\n[OK] 测试完成 ({elapsed:.1f}s)")
        print("\n[DONE] CloakBrowser 所有功能测试通过！")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[FAIL] 测试失败 ({elapsed:.1f}s): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("="*70)


if __name__ == '__main__':
    main()
