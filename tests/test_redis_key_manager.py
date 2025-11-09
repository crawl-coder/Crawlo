#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis Key 管理器测试
==================
测试 RedisKeyManager 类的功能
"""
import unittest
from unittest.mock import MagicMock
from crawlo.utils.redis_manager import RedisKeyManager


class TestRedisKeyManager(unittest.TestCase):
    """Redis Key 管理器测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.project_name = "test_project"
        self.spider_name = "test_spider"
        self.key_manager = RedisKeyManager(self.project_name, self.spider_name)
    
    def test_init_with_project_and_spider(self):
        """测试使用项目名和爬虫名初始化"""
        self.assertEqual(self.key_manager.project_name, self.project_name)
        self.assertEqual(self.key_manager.spider_name, self.spider_name)
        self.assertEqual(self.key_manager.namespace, f"{self.project_name}:{self.spider_name}")
    
    def test_init_with_project_only(self):
        """测试仅使用项目名初始化"""
        key_manager = RedisKeyManager(self.project_name)
        self.assertEqual(key_manager.project_name, self.project_name)
        self.assertIsNone(key_manager.spider_name)
        self.assertEqual(key_manager.namespace, self.project_name)
    
    def test_set_spider_name(self):
        """测试设置爬虫名称"""
        key_manager = RedisKeyManager(self.project_name)
        self.assertIsNone(key_manager.spider_name)
        self.assertEqual(key_manager.namespace, self.project_name)
        
        # 设置爬虫名称
        key_manager.set_spider_name(self.spider_name)
        self.assertEqual(key_manager.spider_name, self.spider_name)
        self.assertEqual(key_manager.namespace, f"{self.project_name}:{self.spider_name}")
        
        # 清除爬虫名称
        key_manager.set_spider_name("")
        self.assertIsNone(key_manager.spider_name)
        self.assertEqual(key_manager.namespace, self.project_name)
    
    def test_queue_keys(self):
        """测试队列相关 Key 生成"""
        # 测试请求队列 Key
        requests_queue_key = self.key_manager.get_requests_queue_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:queue:requests"
        self.assertEqual(requests_queue_key, expected)
        
        # 测试处理中队列 Key
        processing_queue_key = self.key_manager.get_processing_queue_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:queue:processing"
        self.assertEqual(processing_queue_key, expected)
        
        # 测试失败队列 Key
        failed_queue_key = self.key_manager.get_failed_queue_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:queue:failed"
        self.assertEqual(failed_queue_key, expected)
        
        # 测试请求数据 Hash Key
        requests_data_key = self.key_manager.get_requests_data_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:queue:requests:data"
        self.assertEqual(requests_data_key, expected)
        
        # 测试处理中数据 Hash Key
        processing_data_key = self.key_manager.get_processing_data_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:queue:processing:data"
        self.assertEqual(processing_data_key, expected)
    
    def test_filter_keys(self):
        """测试过滤器相关 Key 生成"""
        # 测试过滤器指纹 Key
        filter_key = self.key_manager.get_filter_fingerprint_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:filter:fingerprint"
        self.assertEqual(filter_key, expected)
    
    def test_item_keys(self):
        """测试数据项相关 Key 生成"""
        # 测试数据项指纹 Key
        item_key = self.key_manager.get_item_fingerprint_key()
        expected = f"crawlo:{self.project_name}:{self.spider_name}:item:fingerprint"
        self.assertEqual(item_key, expected)
    
    def test_from_settings(self):
        """测试从配置创建实例"""
        # 创建模拟配置对象
        settings = MagicMock()
        settings.get.side_effect = lambda key, default: {
            'PROJECT_NAME': self.project_name,
            'SPIDER_NAME': None
        }.get(key, default)
        
        key_manager = RedisKeyManager.from_settings(settings)
        self.assertEqual(key_manager.project_name, self.project_name)
        self.assertIsNone(key_manager.spider_name)
    
    def test_key_extraction(self):
        """测试 Key 信息提取"""
        # 测试提取项目名称
        key = f"crawlo:{self.project_name}:{self.spider_name}:queue:requests"
        extracted_project = RedisKeyManager.extract_project_name_from_key(key)
        self.assertEqual(extracted_project, self.project_name)
        
        # 测试提取爬虫名称
        extracted_spider = RedisKeyManager.extract_spider_name_from_key(key)
        self.assertEqual(extracted_spider, self.spider_name)
        
        # 测试无效 Key
        invalid_key = "invalid:key"
        extracted_project = RedisKeyManager.extract_project_name_from_key(invalid_key)
        self.assertIsNone(extracted_project)
        
        extracted_spider = RedisKeyManager.extract_spider_name_from_key(invalid_key)
        self.assertIsNone(extracted_spider)


if __name__ == '__main__':
    unittest.main()