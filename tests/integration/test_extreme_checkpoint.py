"""
Checkpoint 极限测试
测试断点续爬、Checkpoint 损坏、版本迁移等边界场景
"""

import json
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from crawlo.checkpoint.manager import CheckpointManager
from crawlo.items import Item
from crawlo.settings.setting_manager import SettingManager


class TestCheckpointExtremeScenarios:
    """Checkpoint 极限场景测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        # 创建设置管理器
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

    def test_checkpoint_massive_urls(self):
        """测试: 超大量 URL 断点保存 (100,000 条)"""
        import asyncio
        manager = CheckpointManager('test_spider', self.settings)

        # Mock scheduler 和 stats
        class MockScheduler:
            def __init__(self):
                self.pending_requests = []
                self.dupe_filter = None
        
        scheduler = MockScheduler()
        
        # 模拟 10 万条 URL
        for i in range(100000):
            scheduler.pending_requests.append({
                'url': f'http://example.com/page/{i}',
                'method': 'GET',
                'priority': 0,
            })
        
        # 保存检查点
        result = asyncio.run(manager.save(scheduler))
        assert result == True

        # 验证文件存在
        assert manager.storage.exists()

        # 重新加载并验证
        manager2 = CheckpointManager('test_spider', self.settings)
        data = asyncio.run(manager2.load())
        assert data is not None
        assert data['pending_count'] == 100000

    def test_checkpoint_corrupted_json(self):
        """测试: 损坏的 JSON 文件恢复"""
        import asyncio
        # 手动写入损坏的 JSON
        checkpoint_path = os.path.join(self.test_dir, 'test_spider.json')
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            f.write("{invalid json content!!!")
            f.write("\x00\x01\x02")  # 二进制噪声

        manager = CheckpointManager('test_spider', self.settings)

        # 应该能优雅地处理损坏文件
        try:
            data = asyncio.run(manager.load())
            # 如果加载成功,数据应该为 None 或空
            assert data is None or data.get('pending_count', 0) == 0
        except Exception as e:
            # 或者抛出明确的异常
            assert "corrupted" in str(e).lower() or "invalid" in str(e).lower() or "JSON" in str(e)

    def test_checkpoint_truncated_file(self):
        """测试: 截断的文件 (写入中断)"""
        valid_data = {
            "version": "1.0",
            "urls": {
                "http://example.com/1": {"status": "pending"},
                "http://example.com/2": {"status": "success"},
            },
            "stats": {"total": 2},
        }

        # 写入部分数据后截断
        json_str = json.dumps(valid_data, ensure_ascii=False)
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            f.write(json_str[:50])  # 只写前 50 字符

        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 应该能处理截断文件
        try:
            manager.load()
            assert manager.get_pending_count() == 0
        except json.JSONDecodeError:
            # 或者抛出 JSON 解析错误
            pass

    def test_checkpoint_empty_file(self):
        """测试: 空文件"""
        # 创建空文件
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            pass

        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager.load()

        # 应该正常处理空文件
        assert manager.get_pending_count() == 0

    def test_checkpoint_version_migration(self):
        """测试: 版本迁移 (v1 -> v2)"""
        # 旧版本格式
        old_format = {
            "version": "1.0",
            "urls": [
                "http://example.com/1",
                "http://example.com/2",
            ],
        }

        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(old_format, f)

        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 应该能自动迁移或兼容旧版本
        try:
            manager.load()
            # 迁移后应该能正常工作
            assert manager.get_pending_count() >= 0
        except Exception as e:
            # 或者给出明确的版本不兼容提示
            assert "version" in str(e).lower()

    def test_checkpoint_very_large_metadata(self):
        """测试: 超大元数据 (10MB+)"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 添加带有大元数据的 URL
        large_metadata = {
            "status": "pending",
            "data": "x" * 1024 * 1024,  # 1MB 数据
        }

        for i in range(10):
            manager.add_url(f"http://example.com/{i}", large_metadata)

        manager.save()

        # 验证能正常保存和加载
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()
        assert manager2.get_pending_count() == 10

    def test_checkpoint_special_characters_in_urls(self):
        """测试: URL 中包含特殊字符"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        special_urls = [
            "http://example.com/page?query=中文测试",
            "http://example.com/page?query=<script>alert('xss')</script>",
            "http://example.com/page?query='; DROP TABLE urls; --",
            "http://example.com/page/path/../../../etc/passwd",
            "http://example.com/page?query=" + "x" * 10000,  # 超长参数
        ]

        for url in special_urls:
            manager.add_url(url, {"status": "pending"})

        manager.save()

        # 重新加载验证
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()
        assert manager2.get_pending_count() == len(special_urls)

    def test_checkpoint_concurrent_access(self):
        """测试: 并发读写压力"""
        import threading

        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)
        errors = []

        def writer_thread(thread_id):
            try:
                for i in range(100):
                    url = f"http://example.com/{thread_id}/{i}"
                    manager.add_url(url, {"status": "pending"})
                    if i % 10 == 0:
                        manager.save()
            except Exception as e:
                errors.append(str(e))

        # 启动 5 个写线程
        threads = []
        for i in range(5):
            t = threading.Thread(target=writer_thread, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证没有错误
        assert len(errors) == 0, f"并发错误: {errors}"

    def test_checkpoint_disk_full_simulation(self):
        """测试: 磁盘空间不足模拟"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 添加一些数据
        for i in range(100):
            manager.add_url(f"http://example.com/{i}", {"status": "pending"})

        # Mock 磁盘满的情况
        with patch("builtins.open", side_effect=OSError("[Errno 28] No space left on device")):
            try:
                manager.save()
                assert False, "应该抛出磁盘满异常"
            except OSError as e:
                assert "No space left on device" in str(e) or "磁盘" in str(e)

    def test_checkpoint_permission_denied(self):
        """测试: 权限拒绝"""
        # 创建无权限的文件
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump({"version": "1.0"}, f)

        os.chmod(self.checkpoint_file, 0o000)

        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        try:
            manager.load()
            # 在某些系统上可能仍能读取
        except PermissionError:
            # 应该有权限错误
            pass
        finally:
            # 恢复权限以便清理
            os.chmod(self.checkpoint_file, 0o644)

    def test_checkpoint_rapid_save_load_cycle(self):
        """测试: 快速保存/加载循环 (100 次)"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        for cycle in range(100):
            manager.add_url(f"http://example.com/cycle{cycle}", {"status": "pending"})
            manager.save()

            # 重新加载
            manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
            manager2.load()
            assert manager2.get_pending_count() == cycle + 1

    def test_checkpoint_url_deduplication_pressure(self):
        """测试: 海量 URL 去重压力"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 添加 10000 条 URL,其中 50% 重复
        urls = [f"http://example.com/page/{i % 5000}" for i in range(10000)]

        for url in urls:
            manager.add_url(url, {"status": "pending"})

        manager.save()

        # 应该只有 5000 条唯一 URL
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()
        assert manager2.get_pending_count() == 5000

    def test_checkpoint_invalid_url_types(self):
        """测试: 非法 URL 类型"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        invalid_urls = [
            None,
            12345,
            ["http://example.com"],
            {"url": "http://example.com"},
            "",
            "   ",
        ]

        for url in invalid_urls:
            try:
                manager.add_url(url, {"status": "pending"})
            except (TypeError, ValueError):
                # 应该拒绝非法类型
                pass

    def test_checkpoint_statistics_integrity(self):
        """测试: 统计数据完整性"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 添加不同状态的 URL
        for i in range(100):
            status = "pending" if i < 50 else "success" if i < 80 else "failed"
            manager.add_url(f"http://example.com/{i}", {"status": status})

        manager.save()

        # 加载并验证统计
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()

        assert manager2.get_pending_count() == 50
        assert manager2.get_success_count() == 30
        assert manager2.get_failed_count() == 20

    def test_checkpoint_backup_and_restore(self):
        """测试: 备份与恢复"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 添加数据
        for i in range(100):
            manager.add_url(f"http://example.com/{i}", {"status": "pending"})

        manager.save()

        # 创建备份
        backup_file = os.path.join(self.test_dir, "checkpoint_backup.json")
        shutil.copy2(self.checkpoint_file, backup_file)

        # 删除原文件
        os.remove(self.checkpoint_file)

        # 从备份恢复
        shutil.copy2(backup_file, self.checkpoint_file)

        # 验证数据完整性
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()
        assert manager2.get_pending_count() == 100


class TestCheckpointItemState:
    """Checkpoint 中 Item 状态管理测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        # 创建设置管理器
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

    def test_checkpoint_large_items(self):
        """测试: 超大 Item 保存"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        # 创建大 Item
        large_item = Item()
        large_item["url"] = "http://example.com"
        large_item["content"] = "x" * 1024 * 1024  # 1MB 内容
        large_item["metadata"] = {"key": "value" * 10000}

        manager.add_item(large_item)
        manager.save()

        # 验证能正常加载
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()
        assert manager2.get_item_count() == 1

    def test_checkpoint_item_special_fields(self):
        """测试: Item 特殊字段"""
        manager = CheckpointManager(checkpoint_file=self.checkpoint_file)

        item = Item()
        item["url"] = "http://example.com"
        item["title"] = "测试标题<>\"'&"
        item["content"] = "<script>alert('xss')</script>"
        item["binary_data"] = b"\x00\x01\x02\x03"

        manager.add_item(item)
        manager.save()

        # 应该能正确处理特殊字符
        manager2 = CheckpointManager(checkpoint_file=self.checkpoint_file)
        manager2.load()
        assert manager2.get_item_count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
