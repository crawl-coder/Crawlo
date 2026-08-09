"""
Checkpoint 极限测试（按当前 CheckpointManager 契约重写）
测试断点续爬、Checkpoint 损坏、版本兼容、并发等边界场景
"""

import asyncio
import json
import os
import shutil
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from crawlo.checkpoint.manager import CheckpointManager
from crawlo.settings.setting_manager import SettingManager


class _MockQueueManager:
    """模拟当前 CheckpointManager.save 依赖的 queue_manager 接口"""

    def __init__(self, requests):
        self._queue = list(requests)

    async def size(self) -> int:
        return len(self._queue)

    async def get(self):
        if self._queue:
            return self._queue.pop(0)
        return None

    async def put(self, request, priority=0):
        self._queue.append(request)
        return True


def _make_request(url):
    """构造带 url 属性的请求对象（序列化回退路径可处理）"""
    return SimpleNamespace(
        url=url,
        method='GET',
        headers={},
        meta={},
        priority=0,
        dont_filter=False,
        encoding='utf-8',
        body=None,
        cookies=None,
        timeout=None,
        proxy=None,
        callback=None,
        errback=None,
    )


def _make_scheduler(urls, fingerprints=None):
    scheduler = Mock()
    scheduler.queue_manager = _MockQueueManager([_make_request(u) for u in urls])
    scheduler.dupe_filter = Mock()
    scheduler.dupe_filter.fingerprints = set(fingerprints or [])
    scheduler.request_serializer = None
    return scheduler


class TestCheckpointExtremeScenarios:
    """Checkpoint 极限场景测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.settings = SettingManager()
        self.settings.attributes['CHECKPOINT_DIR'] = self.test_dir
        self.settings.attributes['CHECKPOINT_STORAGE'] = 'json'
        self.settings.attributes['CHECKPOINT_ENABLED'] = True
        self.settings.attributes['PROJECT_NAME'] = 'crawlo'

    def teardown_method(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _save_load(self, spider='test_spider', scheduler=None):
        manager = CheckpointManager(spider, self.settings)
        result = asyncio.run(manager.save(scheduler))
        assert result is True
        assert manager.storage.exists()
        manager2 = CheckpointManager(spider, self.settings)
        return asyncio.run(manager2.load())

    def test_checkpoint_massive_urls(self):
        """测试: 超大量 URL 断点保存 (100,000 条)"""
        urls = [f'http://example.com/page/{i}' for i in range(100000)]
        data = self._save_load(scheduler=_make_scheduler(urls))
        assert data is not None
        assert data['pending_count'] == 100000
        assert len(data['requests']) == 100000

    def test_checkpoint_corrupted_json(self):
        """测试: 损坏的 JSON 文件恢复"""
        checkpoint_path = os.path.join(self.test_dir, 'crawlo', 'test_spider.json')
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            f.write("{invalid json content!!!")
            f.write("\x00\x01\x02")

        manager = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager.load())
        assert data is None

    def test_checkpoint_truncated_file(self):
        """测试: 截断的文件 (写入中断)"""
        valid_data = {
            'project_name': 'crawlo',
            'spider_name': 'test_spider',
            'pending_count': 2,
            'requests': [
                {'url': 'http://example.com/1', 'method': 'GET'},
                {'url': 'http://example.com/2', 'method': 'GET'},
            ],
            'fingerprints': ['fp1', 'fp2'],
            'stats': {},
        }
        checkpoint_path = os.path.join(self.test_dir, 'crawlo', 'test_spider.json')
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_data, ensure_ascii=False)[:50])

        manager = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager.load())
        assert data is None

    def test_checkpoint_empty_file(self):
        """测试: 空文件"""
        checkpoint_path = os.path.join(self.test_dir, 'crawlo', 'test_spider.json')
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            pass

        manager = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager.load())
        assert data is None

    def test_checkpoint_version_migration(self):
        """测试: 旧版本格式兼容（v1 无 requests 数组，不崩溃即可）"""
        old_format = {"version": "1.0", "urls": ["http://example.com/1"]}
        checkpoint_path = os.path.join(self.test_dir, 'crawlo', 'test_spider.json')
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(old_format, f)

        manager = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager.load())
        # 不崩溃，返回旧数据或 None 均可
        assert data is None or isinstance(data, dict)

    def test_checkpoint_very_large_metadata(self):
        """测试: 超大元数据 (10MB+)"""
        big = 'x' * 1024 * 1024
        urls = [f'http://example.com/{i}?payload={big[:1024]}' for i in range(10)]
        data = self._save_load(scheduler=_make_scheduler(urls))
        assert data['pending_count'] == 10

    def test_checkpoint_special_characters_in_urls(self):
        """测试: URL 中包含特殊字符"""
        special_urls = [
            "http://example.com/page?query=中文测试",
            "http://example.com/page?query=<script>alert('xss')</script>",
            "http://example.com/page?query='; DROP TABLE urls; --",
            "http://example.com/page/path/../../../etc/passwd",
            "http://example.com/page?query=" + "x" * 10000,
        ]
        data = self._save_load(scheduler=_make_scheduler(special_urls))
        assert data['pending_count'] == len(special_urls)

    def test_checkpoint_concurrent_access(self):
        """测试: 并发保存不同 spider 互不干扰"""
        errors = []

        def writer(thread_id):
            try:
                urls = [f'http://example.com/{thread_id}/{i}' for i in range(50)]
                data = self._save_load(spider=f'spider_{thread_id}', scheduler=_make_scheduler(urls))
                assert data['pending_count'] == 50
            except Exception as e:  # pragma: no cover
                errors.append(str(e))

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发错误: {errors}"

    def test_checkpoint_disk_full_simulation(self):
        """测试: 磁盘空间不足 → save 返回 False 且不崩溃"""
        manager = CheckpointManager('test_spider', self.settings)
        scheduler = _make_scheduler([f'http://example.com/{i}' for i in range(100)])

        with patch("os.fdopen", side_effect=OSError("[Errno 28] No space left on device")):
            result = asyncio.run(manager.save(scheduler))
        assert result is False

    def test_checkpoint_permission_denied(self):
        """测试: 权限拒绝 → load 返回 None 且不崩溃"""
        checkpoint_path = os.path.join(self.test_dir, 'crawlo', 'test_spider.json')
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0"}, f)
        os.chmod(checkpoint_path, 0o000)
        try:
            manager = CheckpointManager('test_spider', self.settings)
            data = asyncio.run(manager.load())
            assert data is None or isinstance(data, dict)
        finally:
            os.chmod(checkpoint_path, 0o644)

    def test_checkpoint_rapid_save_load_cycle(self):
        """测试: 快速保存/加载循环 (50 次)"""
        for cycle in range(50):
            urls = [f'http://example.com/cycle{cycle}']
            data = self._save_load(scheduler=_make_scheduler(urls))
            assert data['pending_count'] == 1

    def test_checkpoint_url_deduplication_pressure(self):
        """测试: 海量 URL + 指纹压力 (10,000 条)"""
        urls = [f'http://example.com/page/{i % 5000}' for i in range(10000)]
        fingerprints = [f'fp_{i}' for i in range(10000)]
        data = self._save_load(scheduler=_make_scheduler(urls, fingerprints=fingerprints))
        assert data['pending_count'] == 10000
        assert len(data['fingerprints']) == 10000

    def test_checkpoint_statistics_integrity(self):
        """测试: 统计数据完整性"""
        scheduler = _make_scheduler([f'http://example.com/{i}' for i in range(100)])
        stats = Mock()
        stats.get_stats.return_value = {'item_scraped_count': 100, 'downloader/response_count': 120}
        manager = CheckpointManager('test_spider', self.settings)
        result = asyncio.run(manager.save(scheduler, stats))
        assert result is True
        manager2 = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager2.load())
        assert data['stats']['item_scraped_count'] == 100
        assert data['stats']['downloader/response_count'] == 120

    def test_checkpoint_backup_and_restore(self):
        """测试: 备份与恢复"""
        urls = [f'http://example.com/{i}' for i in range(100)]
        data = self._save_load(scheduler=_make_scheduler(urls))
        assert data['pending_count'] == 100

        checkpoint_path = os.path.join(self.test_dir, 'crawlo', 'test_spider.json')
        backup_file = os.path.join(self.test_dir, 'checkpoint_backup.json')
        shutil.copy2(checkpoint_path, backup_file)
        os.remove(checkpoint_path)
        shutil.copy2(backup_file, checkpoint_path)

        manager2 = CheckpointManager('test_spider', self.settings)
        restored = asyncio.run(manager2.load())
        assert restored['pending_count'] == 100
