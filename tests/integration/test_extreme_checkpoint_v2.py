"""
Checkpoint 极限测试 - 简化版
测试断点续爬、Checkpoint 损坏、版本迁移等边界场景
"""

import json
import os
import shutil
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from crawlo.checkpoint.manager import CheckpointManager
from crawlo.checkpoint.storage import JsonStorage, SqliteStorage
from crawlo.settings.setting_manager import SettingManager


class TestCheckpointExtremeScenarios:
    """Checkpoint 极限场景测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        try:
            self.settings = SettingManager()
            self.settings.attributes['CHECKPOINT_DIR'] = self.test_dir
            self.settings.attributes['CHECKPOINT_STORAGE'] = 'json'
            self.settings.attributes['CHECKPOINT_ENABLED'] = True
        except ImportError:
            self.settings = {
                'CHECKPOINT_DIR': self.test_dir,
                'CHECKPOINT_STORAGE': 'json',
                'CHECKPOINT_ENABLED': True,
            }

    def teardown_method(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_mock_scheduler(self, num_requests=0):
        """创建 Mock Scheduler"""
        class MockQueue:
            def __init__(self):
                self._queue = []
            
            def qsize(self):
                return len(self._queue)
            
            def get_nowait(self):
                if self._queue:
                    return self._queue.pop(0)
                raise Exception("Queue empty")
        
        class MockDupeFilter:
            def __init__(self):
                self.fingerprints = set()
        
        class MockScheduler:
            def __init__(self):
                self.queue = MockQueue()
                self.dupe_filter = MockDupeFilter()
        
        scheduler = MockScheduler()
        for i in range(num_requests):
            scheduler.queue._queue.append({
                'url': f'http://example.com/page/{i}',
                'method': 'GET',
                'priority': 0,
            })
            scheduler.dupe_filter.fingerprints.add(f'fp_{i}')
        
        return scheduler

    def test_checkpoint_massive_urls(self):
        """测试: 超大量 URL 断点保存 (10,000 条)"""
        manager = CheckpointManager('test_spider', self.settings)
        scheduler = self._create_mock_scheduler(10000)

        # 保存检查点
        result = asyncio.run(manager.save(scheduler))
        assert result == True

        # 验证文件存在
        assert manager.storage.exists()

        # 重新加载并验证
        manager2 = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager2.load())
        assert data is not None
        assert data['pending_count'] == 10000

    def test_checkpoint_corrupted_json(self):
        """测试: 损坏的 JSON 文件恢复"""
        # 手动写入损坏的 JSON
        checkpoint_path = os.path.join(self.test_dir, 'test_spider.json')
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            f.write("{invalid json content!!!")
            f.write("\x00\x01\x02")  # 二进制噪声

        manager = CheckpointManager('test_spider', self.settings)

        # 应该能优雅地处理损坏文件
        try:
            data = asyncio.run(manager.load())
            # 如果加载成功,数据应该为 None
            assert data is None
        except json.JSONDecodeError:
            # 或者抛出 JSON 解析错误
            pass

    def test_checkpoint_truncated_file(self):
        """测试: 截断的文件 (写入中断)"""
        valid_data = {
            'project_name': 'test',
            'spider_name': 'test_spider',
            'pending_count': 2,
            'requests': [
                {'url': 'http://example.com/1', 'method': 'GET'},
                {'url': 'http://example.com/2', 'method': 'GET'},
            ],
            'fingerprints': {'fp1', 'fp2'},
            'stats': {},
        }

        checkpoint_path = os.path.join(self.test_dir, 'test_spider.json')
        # 写入部分数据后截断
        json_str = json.dumps(valid_data, ensure_ascii=False)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            f.write(json_str[:50])  # 只写前 50 字符

        manager = CheckpointManager('test_spider', self.settings)

        # 应该能处理截断文件
        try:
            data = asyncio.run(manager.load())
            assert data is None
        except json.JSONDecodeError:
            pass

    def test_checkpoint_empty_file(self):
        """测试: 空文件"""
        checkpoint_path = os.path.join(self.test_dir, 'test_spider.json')
        # 创建空文件
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            pass

        manager = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager.load())

        # 应该正常处理空文件
        assert data is None

    def test_checkpoint_special_characters(self):
        """测试: URL 中包含特殊字符"""
        manager = CheckpointManager('test_spider', self.settings)
        
        class MockScheduler:
            def __init__(self):
                self.queue = MockQueue()
                self.dupe_filter = None
        
        class MockQueue:
            def __init__(self):
                self._queue = [
                    {'url': 'http://example.com/page?query=中文测试', 'method': 'GET'},
                    {'url': "http://example.com/page?query=<script>alert('xss')</script>", 'method': 'GET'},
                    {'url': "http://example.com/page?query='; DROP TABLE urls; --", 'method': 'GET'},
                    {'url': 'http://example.com/page/path/../../../etc/passwd', 'method': 'GET'},
                ]
            
            def qsize(self):
                return len(self._queue)
            
            def get_nowait(self):
                if self._queue:
                    return self._queue.pop(0)
                raise Exception("Queue empty")
        
        scheduler = MockScheduler()
        result = asyncio.run(manager.save(scheduler))
        assert result == True

        # 重新加载验证
        manager2 = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager2.load())
        assert data is not None
        assert data['pending_count'] == 4

    def test_checkpoint_rapid_save_load_cycle(self):
        """测试: 快速保存/加载循环 (50 次)"""
        for cycle in range(50):
            manager = CheckpointManager('test_spider', self.settings)
            scheduler = self._create_mock_scheduler(cycle + 1)
            
            asyncio.run(manager.save(scheduler))

            # 重新加载
            manager2 = CheckpointManager('test_spider', self.settings)
            data = asyncio.run(manager2.load())
            assert data is not None
            assert data['pending_count'] == cycle + 1

    def test_checkpoint_statistics_integrity(self):
        """测试: 统计数据完整性"""
        manager = CheckpointManager('test_spider', self.settings)
        
        class MockScheduler:
            def __init__(self):
                self.queue = MockQueue()
                self.dupe_filter = None
        
        class MockQueue:
            def __init__(self):
                self._queue = []
            
            def qsize(self):
                return len(self._queue)
            
            def get_nowait(self):
                if self._queue:
                    return self._queue.pop(0)
                raise Exception("Queue empty")
        
        class MockStats:
            def get_stats(self):
                return {
                    'downloaded': 100,
                    'failed': 20,
                    'errors': 5,
                }
        
        scheduler = MockScheduler()
        stats = MockStats()
        
        result = asyncio.run(manager.save(scheduler, stats))
        assert result == True

        # 加载并验证统计
        manager2 = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager2.load())
        assert data is not None
        assert data['stats']['downloaded'] == 100
        assert data['stats']['failed'] == 20

    def test_checkpoint_clear_and_recreate(self):
        """测试: 清除后重建"""
        manager = CheckpointManager('test_spider', self.settings)
        scheduler = self._create_mock_scheduler(100)
        
        asyncio.run(manager.save(scheduler))
        assert asyncio.run(manager.has_checkpoint()) == True

        # 清除
        asyncio.run(manager.clear())
        assert asyncio.run(manager.has_checkpoint()) == False

        # 重建
        scheduler2 = self._create_mock_scheduler(50)
        asyncio.run(manager.save(scheduler2))
        assert asyncio.run(manager.has_checkpoint()) == True

        # 验证新数据
        manager2 = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager2.load())
        assert data is not None
        assert data['pending_count'] == 50

    def test_checkpoint_multiple_spiders(self):
        """测试: 多爬虫检查点隔离"""
        settings1 = self.settings
        settings2 = self.settings.copy() if hasattr(self.settings, 'copy') else {
            'CHECKPOINT_DIR': self.test_dir,
            'CHECKPOINT_STORAGE': 'json',
            'CHECKPOINT_ENABLED': True,
        }

        manager1 = CheckpointManager('spider_a', settings1)
        manager2 = CheckpointManager('spider_b', settings2)

        scheduler_a = self._create_mock_scheduler(100)
        scheduler_b = self._create_mock_scheduler(200)

        asyncio.run(manager1.save(scheduler_a))
        asyncio.run(manager2.save(scheduler_b))

        # 验证隔离
        data_a = asyncio.run(manager1.load())
        data_b = asyncio.run(manager2.load())

        assert data_a['pending_count'] == 100
        assert data_b['pending_count'] == 200

    def test_checkpoint_sqlite_storage(self):
        """测试: SQLite 存储后端"""
        try:
            settings = SettingManager()
            settings.attributes['CHECKPOINT_DIR'] = self.test_dir
            settings.attributes['CHECKPOINT_STORAGE'] = 'sqlite'
            settings.attributes['CHECKPOINT_ENABLED'] = True
        except ImportError:
            settings = {
                'CHECKPOINT_DIR': self.test_dir,
                'CHECKPOINT_STORAGE': 'sqlite',
                'CHECKPOINT_ENABLED': True,
            }

        manager = CheckpointManager('test_spider', settings)
        scheduler = self._create_mock_scheduler(1000)

        result = asyncio.run(manager.save(scheduler))
        assert result == True

        # 重新加载
        manager2 = CheckpointManager('test_spider', settings)
        data = asyncio.run(manager2.load())
        assert data is not None
        assert data['pending_count'] == 1000


class TestCheckpointStorageExtreme:
    """Checkpoint 存储层极限测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_json_storage_large_data(self):
        """测试: JSON 存储大数据 (5MB+)"""
        storage = JsonStorage(
            spider_name='test_spider',
            project_name='test_project',
            checkpoint_dir=self.test_dir
        )

        # 创建大数据
        large_data = {
            'project_name': 'test',
            'spider_name': 'test_spider',
            'pending_count': 1000,
            'requests': [
                {
                    'url': f'http://example.com/{i}',
                    'method': 'GET',
                    'meta': {'data': 'x' * 5000},  # 每个请求 5KB 元数据
                }
                for i in range(1000)
            ],
            'fingerprints': set([f'fp_{i}' for i in range(1000)]),
            'stats': {},
        }

        # 保存
        result = storage.save(large_data)
        assert result == True

        # 加载
        loaded = storage.load()
        assert loaded is not None
        assert loaded['pending_count'] == 1000

    def test_json_storage_invalid_path(self):
        """测试: JSON 存储非法路径"""
        with pytest.raises((OSError, PermissionError)):
            JsonStorage(
                spider_name='test_spider',
                project_name='test_project',
                checkpoint_dir='/root/invalid/path'
            )

    def test_sqlite_storage_large_data(self):
        """测试: SQLite 存储大数据"""
        storage = SqliteStorage(
            spider_name='test_spider',
            project_name='test_project',
            checkpoint_dir=self.test_dir
        )

        large_data = {
            'project_name': 'test',
            'spider_name': 'test_spider',
            'pending_count': 5000,
            'requests': [
                {'url': f'http://example.com/{i}', 'method': 'GET', 'priority': i}
                for i in range(5000)
            ],
            'fingerprints': set([f'fp_{i}' for i in range(5000)]),
            'stats': {'downloaded': 10000},
        }

        result = storage.save(large_data)
        assert result == True

        loaded = storage.load()
        assert loaded is not None
        assert loaded['pending_count'] == 5000

    def test_storage_concurrent_access(self):
        """测试: 存储并发访问"""
        import threading

        storage = JsonStorage(
            spider_name='test_spider',
            project_name='test_project',
            checkpoint_dir=self.test_dir
        )

        errors = []

        def writer_thread(thread_id):
            try:
                for i in range(50):
                    data = {
                        'project_name': 'test',
                        'spider_name': 'test_spider',
                        'pending_count': thread_id * 50 + i,
                        'requests': [],
                        'fingerprints': set(),
                        'stats': {},
                    }
                    storage.save(data)
            except Exception as e:
                errors.append(str(e))

        # 启动 5 个写线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=writer_thread, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证没有错误
        assert len(errors) == 0, f"并发错误: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
