#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis Key 管理器与验证器集成测试
==============================
测试 RedisKeyManager 和 RedisKeyValidator 的集成功能
"""
import unittest
from unittest.mock import MagicMock
from crawlo.utils.redis_manager import RedisKeyManager, validate_redis_key_naming, get_redis_key_info


class TestRedisKeyIntegration(unittest.TestCase):
    """Redis Key 管理器与验证器集成测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.project_name = "test_project"
        self.spider_name = "test_spider"
        self.key_manager = RedisKeyManager(self.project_name, self.spider_name)
    
    def test_queue_keys_validation(self):
        """测试队列相关 Key 生成和验证"""
        # 测试请求队列 Key
        requests_queue_key = self.key_manager.get_requests_queue_key()
        self.assertTrue(validate_redis_key_naming(requests_queue_key, self.project_name))
        
        # 测试处理中队列 Key
        processing_queue_key = self.key_manager.get_processing_queue_key()
        self.assertTrue(validate_redis_key_naming(processing_queue_key, self.project_name))
        
        # 测试失败队列 Key
        failed_queue_key = self.key_manager.get_failed_queue_key()
        self.assertTrue(validate_redis_key_naming(failed_queue_key, self.project_name))
        
        # 测试请求数据 Hash Key
        requests_data_key = self.key_manager.get_requests_data_key()
        self.assertTrue(validate_redis_key_naming(requests_data_key, self.project_name))
        
        # 测试处理中数据 Hash Key
        processing_data_key = self.key_manager.get_processing_data_key()
        self.assertTrue(validate_redis_key_naming(processing_data_key, self.project_name))
    
    def test_filter_keys_validation(self):
        """测试过滤器相关 Key 生成和验证"""
        # 测试过滤器指纹 Key
        filter_key = self.key_manager.get_filter_fingerprint_key()
        self.assertTrue(validate_redis_key_naming(filter_key, self.project_name))
    
    def test_item_keys_validation(self):
        """测试数据项相关 Key 生成和验证"""
        # 测试数据项指纹 Key
        item_key = self.key_manager.get_item_fingerprint_key()
        self.assertTrue(validate_redis_key_naming(item_key, self.project_name))
    
    def test_key_info_extraction(self):
        """测试 Key 信息提取"""
        # 测试请求队列 Key 信息
        requests_queue_key = self.key_manager.get_requests_queue_key()
        info = get_redis_key_info(requests_queue_key)
        self.assertTrue(info['valid'])
        self.assertEqual(info['framework'], 'crawlo')
        self.assertEqual(info['project'], self.project_name)
        self.assertEqual(info['spider'], self.spider_name)
        self.assertEqual(info['component'], 'queue')
        self.assertEqual(info['sub_component'], 'requests')
        
        # 测试过滤器指纹 Key 信息
        filter_key = self.key_manager.get_filter_fingerprint_key()
        info = get_redis_key_info(filter_key)
        self.assertTrue(info['valid'])
        self.assertEqual(info['framework'], 'crawlo')
        self.assertEqual(info['project'], self.project_name)
        self.assertEqual(info['spider'], self.spider_name)
        self.assertEqual(info['component'], 'filter')
        self.assertEqual(info['sub_component'], 'fingerprint')
        
        # 测试数据项指纹 Key 信息
        item_key = self.key_manager.get_item_fingerprint_key()
        info = get_redis_key_info(item_key)
        self.assertTrue(info['valid'])
        self.assertEqual(info['framework'], 'crawlo')
        self.assertEqual(info['project'], self.project_name)
        self.assertEqual(info['spider'], self.spider_name)
        self.assertEqual(info['component'], 'item')
        self.assertEqual(info['sub_component'], 'fingerprint')
    
    def test_without_spider_name(self):
        """测试不包含爬虫名称的 Key"""
        key_manager = RedisKeyManager(self.project_name)
        
        # 测试请求队列 Key
        requests_queue_key = key_manager.get_requests_queue_key()
        self.assertTrue(validate_redis_key_naming(requests_queue_key, self.project_name))
        
        # 验证 Key 信息
        info = get_redis_key_info(requests_queue_key)
        self.assertTrue(info['valid'])
        self.assertEqual(info['framework'], 'crawlo')
        self.assertEqual(info['project'], self.project_name)
        self.assertEqual(info['component'], 'queue')
        self.assertEqual(info['sub_component'], 'requests')
        self.assertNotIn('spider', info)


if __name__ == '__main__':
    unittest.main()