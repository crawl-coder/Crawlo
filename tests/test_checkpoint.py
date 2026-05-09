# -*- coding: utf-8 -*-
"""
===================================
Checkpoint 模块单元测试
===================================

测试检查点管理器的核心功能、存储后端和容错机制。
"""

import unittest
import os
import json
import tempfile
import shutil
import time
import sqlite3
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Set

# 导入被测试模块
from crawlo.checkpoint.manager import CheckpointManager
from crawlo.checkpoint.storage import BaseStorage, JsonStorage, SqliteStorage


class TestJsonStorage(unittest.TestCase):
    """测试 JSON 存储后端"""

    def setUp(self):
        """测试前创建临时目录"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = JsonStorage(
            spider_name='test_spider',
            project_name='test_project',
            checkpoint_dir=self.test_dir
        )

    def tearDown(self):
        """测试后清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_load(self):
        """测试保存和加载"""
        data = {
            'project_name': 'test_project',
            'spider_name': 'test_spider',
            'pending_count': 2,
            'requests': [
                {'url': 'http://example.com/1', 'method': 'GET'},
                {'url': 'http://example.com/2', 'method': 'POST'},
            ],
            'fingerprints': {'fp1', 'fp2', 'fp3'},
            'stats': {'scraped': 100, 'failed': 5}
        }

        # 保存
        result = self.storage.save(data)
        self.assertTrue(result)

        # 验证文件存在
        self.assertTrue(self.storage.exists())

        # 加载
        loaded = self.storage.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['project_name'], 'test_project')
        self.assertEqual(loaded['spider_name'], 'test_spider')
        self.assertEqual(loaded['pending_count'], 2)
        self.assertEqual(len(loaded['requests']), 2)
        self.assertEqual(len(loaded['fingerprints']), 3)
        self.assertEqual(loaded['stats']['scraped'], 100)

    def test_atomic_write(self):
        """测试原子写入（临时文件 + 重命名）"""
        data = {
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 1,
            'requests': [{'url': 'http://example.com'}],
            'fingerprints': set(),
            'stats': {}
        }

        # 保存
        self.storage.save(data)

        # 验证没有临时文件残留
        dir_contents = os.listdir(self.test_dir + '/test_project')
        tmp_files = [f for f in dir_contents if f.endswith('.tmp')]
        self.assertEqual(len(tmp_files), 0, "Should not have temporary files")

        # 验证正式文件存在
        json_files = [f for f in dir_contents if f.endswith('.json')]
        self.assertEqual(len(json_files), 1)

    def test_set_to_list_conversion(self):
        """测试 set 到 list 的转换"""
        data = {
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 0,
            'requests': [],
            'fingerprints': {'fp1', 'fp2'},  # set
            'stats': {}
        }

        self.storage.save(data)
        loaded = self.storage.load()

        # 加载后应该转换回 set
        self.assertIsInstance(loaded['fingerprints'], set)
        self.assertEqual(loaded['fingerprints'], {'fp1', 'fp2'})

    def test_clear(self):
        """测试清除检查点"""
        data = {
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 0,
            'requests': [],
            'fingerprints': set(),
            'stats': {}
        }

        self.storage.save(data)
        self.assertTrue(self.storage.exists())

        # 清除
        result = self.storage.clear()
        self.assertTrue(result)
        self.assertFalse(self.storage.exists())

    def test_load_nonexistent(self):
        """测试加载不存在的检查点"""
        result = self.storage.load()
        self.assertIsNone(result)

    def test_save_error_handling(self):
        """测试保存异常处理"""
        # 模拟 json.dump 抛出异常
        with patch('json.dump', side_effect=IOError("Permission denied")):
            result = self.storage.save({'test': 'data'})
            self.assertFalse(result)


class TestSqliteStorage(unittest.TestCase):
    """测试 SQLite 存储后端"""

    def setUp(self):
        """测试前创建临时目录"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = SqliteStorage(
            spider_name='test_spider',
            project_name='test_project',
            checkpoint_dir=self.test_dir
        )

    def tearDown(self):
        """测试后清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_load(self):
        """测试保存和加载"""
        data = {
            'project_name': 'test_project',
            'spider_name': 'test_spider',
            'pending_count': 2,
            'requests': [
                {'url': 'http://example.com/1', 'method': 'GET', 'priority': 1},
                {'url': 'http://example.com/2', 'method': 'POST', 'priority': 2},
            ],
            'fingerprints': {'fp1', 'fp2', 'fp3'},
            'stats': {'scraped': 100, 'failed': 5}
        }

        # 保存
        result = self.storage.save(data)
        self.assertTrue(result)

        # 验证文件存在
        self.assertTrue(self.storage.exists())

        # 加载
        loaded = self.storage.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['project_name'], 'test_project')
        self.assertEqual(loaded['spider_name'], 'test_spider')
        self.assertEqual(loaded['pending_count'], 2)
        self.assertEqual(len(loaded['requests']), 2)
        self.assertEqual(len(loaded['fingerprints']), 3)
        self.assertEqual(loaded['stats']['scraped'], 100)

    def test_transaction_integrity(self):
        """测试事务完整性"""
        data = {
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 1,
            'requests': [{'url': 'http://example.com'}],
            'fingerprints': {'fp1'},
            'stats': {'scraped': 50}
        }

        # 保存
        self.storage.save(data)

        # 验证数据库连接正确关闭（可以再次打开）
        conn = sqlite3.connect(self.storage._path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM pending_requests')
        count = c.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1)

    def test_requests_priority_ordering(self):
        """测试请求按优先级排序"""
        data = {
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 3,
            'requests': [
                {'url': 'http://low.com', 'priority': 10},
                {'url': 'http://high.com', 'priority': 1},
                {'url': 'http://medium.com', 'priority': 5},
            ],
            'fingerprints': set(),
            'stats': {}
        }

        self.storage.save(data)
        loaded = self.storage.load()

        # 验证按优先级升序排列
        self.assertEqual(loaded['requests'][0]['url'], 'http://high.com')
        self.assertEqual(loaded['requests'][1]['url'], 'http://medium.com')
        self.assertEqual(loaded['requests'][2]['url'], 'http://low.com')

    def test_clear(self):
        """测试清除检查点"""
        data = {
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 0,
            'requests': [],
            'fingerprints': set(),
            'stats': {}
        }

        self.storage.save(data)
        self.assertTrue(self.storage.exists())

        # 清除
        result = self.storage.clear()
        self.assertTrue(result)
        self.assertFalse(self.storage.exists())

    def test_save_error_handling(self):
        """测试保存异常处理"""
        # 使用临时目录，但模拟 sqlite3.connect 抛出异常
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Database error")):
            # 创建存储实例
            storage = SqliteStorage(
                spider_name='test',
                project_name='test',
                checkpoint_dir=self.test_dir
            )
            
            # 应该返回 False 而不是抛出异常
            result = storage.save({'test': 'data'})
            self.assertFalse(result)


class TestCheckpointManager(unittest.TestCase):
    """测试检查点管理器"""

    def setUp(self):
        """测试前创建临时目录和模拟设置"""
        self.test_dir = tempfile.mkdtemp()
        self.settings = Mock()
        self.settings.get = Mock(side_effect=lambda key, default=None: {
            'CHECKPOINT_ENABLED': True,
            'CHECKPOINT_STORAGE': 'json',
            'CHECKPOINT_DIR': self.test_dir,
            'PROJECT_NAME': 'test_project',
        }.get(key, default))

        self.manager = CheckpointManager(
            spider_name='test_spider',
            settings=self.settings
        )

    def tearDown(self):
        """测试后清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_enabled(self):
        """测试 enabled 属性"""
        self.assertTrue(self.manager.enabled)

    def test_disabled(self):
        """测试禁用状态"""
        self.settings.get = Mock(side_effect=lambda key, default=None: {
            'CHECKPOINT_ENABLED': False,
        }.get(key, default))

        manager = CheckpointManager(
            spider_name='test_spider',
            settings=self.settings
        )
        self.assertFalse(manager.enabled)

    def test_save_and_load(self):
        """测试保存和加载检查点"""
        # 创建模拟调度器和统计
        mock_scheduler = Mock()
        mock_queue_manager = AsyncMock()
        mock_queue_manager.size.return_value = 0  # 空队列
        mock_scheduler.queue_manager = mock_queue_manager
        mock_scheduler.dupe_filter = Mock()
        mock_scheduler.dupe_filter.fingerprints = {'fp1', 'fp2'}

        mock_stats = Mock()
        mock_stats.get_stats.return_value = {'scraped': 100, 'failed': 5}

        # 保存
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            self.manager.save(scheduler=mock_scheduler, stats=mock_stats)
        )
        self.assertTrue(result)

        # 验证文件存在
        self.assertTrue(self.manager.storage.exists())

        # 加载
        loaded = asyncio.get_event_loop().run_until_complete(
            self.manager.load()
        )
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['pending_count'], 0)
        self.assertEqual(len(loaded['fingerprints']), 2)
        self.assertEqual(loaded['stats']['scraped'], 100)

    def test_has_checkpoint(self):
        """测试检查点存在性"""
        import asyncio

        # 初始状态：不存在
        result = asyncio.get_event_loop().run_until_complete(
            self.manager.has_checkpoint()
        )
        self.assertFalse(result)

        # 保存后：存在
        self.manager.storage.save({
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 0,
            'requests': [],
            'fingerprints': set(),
            'stats': {}
        })

        result = asyncio.get_event_loop().run_until_complete(
            self.manager.has_checkpoint()
        )
        self.assertTrue(result)

    def test_clear(self):
        """测试清除检查点"""
        import asyncio

        # 先保存
        self.manager.storage.save({
            'project_name': 'test',
            'spider_name': 'test',
            'pending_count': 0,
            'requests': [],
            'fingerprints': set(),
            'stats': {}
        })

        # 清除
        result = asyncio.get_event_loop().run_until_complete(
            self.manager.clear()
        )
        self.assertTrue(result)
        self.assertFalse(self.manager.storage.exists())

    def test_extract_pending_requests_empty_queue(self):
        """测试提取空队列请求"""
        import asyncio

        mock_scheduler = Mock()
        mock_queue_manager = AsyncMock()
        mock_queue_manager.size.return_value = 0
        mock_scheduler.queue_manager = mock_queue_manager

        result = asyncio.get_event_loop().run_until_complete(
            self.manager._extract_pending_requests(mock_scheduler)
        )
        self.assertEqual(result, [])

    def test_extract_pending_requests_with_items(self):
        """测试提取队列中的请求"""
        import asyncio

        # 创建模拟请求
        mock_request = Mock()
        mock_request.url = 'http://example.com'
        mock_request.method = 'GET'
        mock_request.priority = 1
        mock_request.headers = {}
        mock_request.meta = {}
        mock_request.dont_filter = False
        mock_request.encoding = 'utf-8'

        mock_scheduler = Mock()
        mock_queue_manager = AsyncMock()
        mock_queue_manager.size.return_value = 1
        mock_queue_manager.get.return_value = mock_request
        mock_scheduler.queue_manager = mock_queue_manager
        mock_scheduler.request_serializer = None

        result = asyncio.get_event_loop().run_until_complete(
            self.manager._extract_pending_requests(mock_scheduler)
        )

        # 应该提取到 1 个请求
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['url'], 'http://example.com')

        # 验证请求被放回队列
        mock_queue_manager.put.assert_called_once()

    def test_serialize_request(self):
        """测试请求序列化"""
        from crawlo.network.request import Request

        request = Request(
            url='http://example.com',
            method='POST',
            headers={'Content-Type': 'application/json'},
            meta={'key': 'value'},
            priority=5,
            dont_filter=True,
        )

        result = self.manager._serialize_request(request)

        self.assertIsNotNone(result)
        self.assertEqual(result['url'], 'http://example.com')
        self.assertEqual(result['method'], 'POST')
        # request_to_dict 不包含 priority，需要手动添加
        # 验证基本字段即可
        self.assertIn('headers', result)

    def test_restore_request(self):
        """测试请求恢复"""
        request_data = {
            'url': 'http://example.com',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'meta': {'key': 'value'},
            'priority': 5,
            'dont_filter': True,
            'cookies': {'session': 'abc123'},
        }

        result = self.manager.restore_request(request_data)

        self.assertIsNotNone(result)
        self.assertEqual(result.url, 'http://example.com')
        self.assertEqual(result.method, 'POST')
        self.assertEqual(result.priority, 5)
        self.assertTrue(result.dont_filter)

    def test_restore_fingerprints(self):
        """测试指纹恢复"""
        mock_scheduler = Mock()
        mock_dupe_filter = Mock()
        mock_dupe_filter.fingerprints = set()
        mock_scheduler.dupe_filter = mock_dupe_filter

        fingerprints = {'fp1', 'fp2', 'fp3'}
        result = self.manager.restore_fingerprints(fingerprints, mock_scheduler)

        self.assertTrue(result)
        self.assertEqual(mock_dupe_filter.fingerprints, {'fp1', 'fp2', 'fp3'})

    def test_restore_fingerprints_empty(self):
        """测试空指纹恢复"""
        mock_scheduler = Mock()
        result = self.manager.restore_fingerprints(set(), mock_scheduler)
        self.assertFalse(result)

    def test_extract_fingerprints_memory_filter(self):
        """测试从 Memory 过滤器提取指纹"""
        mock_scheduler = Mock()
        mock_dupe_filter = Mock()
        mock_dupe_filter.fingerprints = {'fp1', 'fp2', 'fp3'}
        mock_scheduler.dupe_filter = mock_dupe_filter

        result = self.manager._extract_fingerprints(mock_scheduler)

        self.assertEqual(result, {'fp1', 'fp2', 'fp3'})

    def test_extract_fingerprints_redis_filter_warning(self):
        """测试 Redis 过滤器警告"""
        mock_scheduler = Mock()
        mock_dupe_filter = Mock()
        # 模拟 Redis 过滤器（有 redis_client 属性）
        mock_dupe_filter.redis_client = Mock()
        del mock_dupe_filter.fingerprints  # Redis 过滤器没有 fingerprints 属性
        mock_scheduler.dupe_filter = mock_dupe_filter

        # 应该返回空集并记录警告
        result = self.manager._extract_fingerprints(mock_scheduler)

        self.assertEqual(result, set())


class TestCheckpointStorageSelection(unittest.TestCase):
    """测试存储后端选择"""

    def setUp(self):
        """测试前创建临时目录"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_json_storage_selection(self):
        """测试选择 JSON 存储"""
        settings = Mock()
        settings.get = Mock(side_effect=lambda key, default=None: {
            'CHECKPOINT_STORAGE': 'json',
            'CHECKPOINT_DIR': self.test_dir,
            'PROJECT_NAME': 'test',
        }.get(key, default))

        manager = CheckpointManager(spider_name='test', settings=settings)
        self.assertIsInstance(manager.storage, JsonStorage)

    def test_sqlite_storage_selection(self):
        """测试选择 SQLite 存储"""
        settings = Mock()
        settings.get = Mock(side_effect=lambda key, default=None: {
            'CHECKPOINT_STORAGE': 'sqlite',
            'CHECKPOINT_DIR': self.test_dir,
            'PROJECT_NAME': 'test',
        }.get(key, default))

        manager = CheckpointManager(spider_name='test', settings=settings)
        self.assertIsInstance(manager.storage, SqliteStorage)

    def test_default_storage_selection(self):
        """测试默认存储（JSON）"""
        settings = Mock()
        settings.get = Mock(side_effect=lambda key, default=None: {
            'CHECKPOINT_DIR': self.test_dir,
            'PROJECT_NAME': 'test',
        }.get(key, default))

        manager = CheckpointManager(spider_name='test', settings=settings)
        self.assertIsInstance(manager.storage, JsonStorage)


if __name__ == '__main__':
    unittest.main()
