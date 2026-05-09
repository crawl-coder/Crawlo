#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spider 模块修复验证测试
"""
import unittest
from unittest.mock import Mock, patch
from crawlo.spider import Spider, SpiderLoader, SpiderResolver, SpiderDiscoveryState


class TestSpiderMetaFix(unittest.TestCase):
    """测试 SpiderMeta 裸 except 修复"""

    def test_exception_is_not_bare(self):
        """验证 except 不再是裸 except"""
        import inspect
        from crawlo.spider.spider import SpiderMeta
        
        # 获取 __new__ 方法的源代码
        source = inspect.getsource(SpiderMeta.__new__)
        
        # 检查应该使用 except Exception 而不是 except:
        self.assertIn('except Exception:', source)
        self.assertNotRegex(source, r'except\s*:')


class TestSpiderDiscoveryStateFix(unittest.TestCase):
    """测试 SpiderDiscoveryState 状态管理"""

    def setUp(self):
        """测试前重置状态"""
        SpiderDiscoveryState.clear()

    def tearDown(self):
        """测试后清理"""
        SpiderDiscoveryState.clear()

    def test_reset_method_exists(self):
        """测试 reset 方法存在"""
        self.assertTrue(hasattr(SpiderDiscoveryState, 'reset'))

    def test_clear_isolates_state(self):
        """测试 clear 方法隔离状态"""
        SpiderDiscoveryState.add_discovery_error("error1")
        self.assertEqual(len(SpiderDiscoveryState.get_discovery_errors()), 1)
        
        SpiderDiscoveryState.clear()
        self.assertEqual(len(SpiderDiscoveryState.get_discovery_errors()), 0)

    def test_reset_calls_clear(self):
        """测试 reset 调用 clear"""
        SpiderDiscoveryState.add_discovery_error("error1")
        SpiderDiscoveryState.reset()
        self.assertEqual(len(SpiderDiscoveryState.get_discovery_errors()), 0)


class TestSpiderLoaderFix(unittest.TestCase):
    """测试 SpiderLoader 优化"""

    def test_discover_default_modules_method_exists(self):
        """测试 _discover_default_modules 方法存在"""
        loader = SpiderLoader(settings=None)
        self.assertTrue(hasattr(loader, '_discover_default_modules'))

    def test_load_all_spiders_uses_discover(self):
        """测试 _load_all_spiders 使用 _discover_default_modules"""
        import inspect
        source = inspect.getsource(SpiderLoader._load_all_spiders)
        self.assertIn('_discover_default_modules', source)

    def test_find_by_request_implementation(self):
        """测试 find_by_request 已实现"""
        loader = SpiderLoader(settings=None)
        
        # 创建 mock request
        mock_request = Mock()
        mock_request.url = 'http://example.com/page'
        
        # 应该返回匹配的爬虫列表（不再返回所有）
        result = loader.find_by_request(mock_request)
        self.assertIsInstance(result, list)


class TestSpiderInitFix(unittest.TestCase):
    """测试 Spider.__init__ 优化"""

    def test_name_from_class_attribute(self):
        """测试使用类属性 name"""
        class TestSpider1(Spider):
            name = 'test_spider_1'
            
            def parse(self, response):
                pass
        
        # 实例化时不传 name
        spider = TestSpider1()
        self.assertEqual(spider.name, 'test_spider_1')

    def test_name_can_be_overridden(self):
        """测试可以运行时覆盖 name"""
        class TestSpider2(Spider):
            name = 'test_spider_2'
            
            def parse(self, response):
                pass
        
        # 实例化时传入 name
        spider = TestSpider2(name='overridden_name')
        self.assertEqual(spider.name, 'overridden_name')


class TestLoggerDelayFix(unittest.TestCase):
    """测试 logger 延迟初始化注释"""

    def test_logger_docstring_explains_delay(self):
        """测试 logger 属性的 docstring 解释了延迟原因"""
        import inspect
        from crawlo.spider.spider import Spider
        
        docstring = Spider.logger.__doc__
        self.assertIsNotNone(docstring)
        self.assertIn('延迟', docstring.lower() if docstring else '')


class TestSpiderResolverFix(unittest.TestCase):
    """测试 SpiderResolver 简化"""

    def test_extracted_methods_exist(self):
        """测试提取的方法存在"""
        self.assertTrue(hasattr(SpiderResolver, '_import_modules'))
        self.assertTrue(hasattr(SpiderResolver, '_auto_discover_spiders'))
        self.assertTrue(hasattr(SpiderResolver, '_try_direct_import'))

    def test_resolve_spider_class_uses_extracted_methods(self):
        """测试 resolve_spider_class 使用提取的方法"""
        import inspect
        source = inspect.getsource(SpiderResolver.resolve_spider_class)
        
        # 应该调用提取的方法
        self.assertIn('_import_modules', source)
        self.assertIn('_auto_discover_spiders', source)
        self.assertIn('_try_direct_import', source)

    def test_resolve_with_class_directly(self):
        """测试直接传入类对象"""
        class TestSpider3(Spider):
            name = 'direct_test_spider'
            
            def parse(self, response):
                pass
        
        # 直接传入类应该返回该类
        result = SpiderResolver.resolve_spider_class(TestSpider3)
        self.assertEqual(result, TestSpider3)


if __name__ == '__main__':
    unittest.main()
