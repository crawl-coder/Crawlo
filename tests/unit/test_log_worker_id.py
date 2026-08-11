#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
LOG_FILE_WORKER_ID 动态更新测试
===============================

验证：分布式集群初始化拿到 worker_id 后，日志文件路径自动追加 worker_id
（多机/多进程分布式场景下各 Worker 日志可区分）。

核心依赖：`LogManager.set_file_path()` 动态重建 file handler。

边界场景：
- set_file_path 幂等（不叠加 handler）
- 未配置 / file 禁用时返回 False
- 动态更新保留配置的文件级别（不硬编码 INFO）
- 旧日志文件不被删除（无数据丢失）
- worker_log_path 对无扩展名/多扩展名/特殊字符的处理
- ClusterLifecycleMixin._apply_worker_id_to_log_file 的开启/关闭/无文件/无 worker_id
"""

import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from unittest.mock import MagicMock

import pytest

from crawlo.cluster.coordinator_lifecycle import ClusterLifecycleMixin
from crawlo.logging.config import LogConfig
from crawlo.logging.factory import LoggerFactory
from crawlo.logging.manager import LogManager, worker_log_path


@pytest.fixture(autouse=True)
def _reset_logging_state():
    """每个用例独立：清空单例配置与 logger 缓存，避免跨用例污染。"""
    LogManager().reset()
    LoggerFactory.clear_cache()
    yield
    LogManager().reset()
    LoggerFactory.clear_cache()


class _FakeSettings:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


def test_set_file_path_updates_handler(tmp_path):
    """set_file_path 后，已创建 logger 的 file handler 指向新路径。"""
    old_path = tmp_path / "app.log"
    new_path = tmp_path / "app.worker-1-abc123.log"

    settings = _FakeSettings({
        'LOG_FILE': str(old_path),
        'LOG_FILE_WHEN': 'midnight',
        'LOG_FILE_BACKUP_COUNT': 7,
        'LOG_CONSOLE_ENABLED': False,
    })
    from crawlo.logging import configure_logging
    configure_logging(settings)

    logger = LoggerFactory.get_logger("test_worker_id")
    # 初始 handler 指向旧路径
    assert any(
        isinstance(h, TimedRotatingFileHandler) and h.baseFilename == str(old_path)
        for h in logger.handlers
    )

    # 动态换路径
    ok = LogManager().set_file_path(str(new_path))
    assert ok

    handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert handlers, "动态更新后应存在 file handler"
    assert handlers[0].baseFilename == str(new_path), (
        f"handler 未更新到新路径: {handlers[0].baseFilename}"
    )

    # 新路径可写
    logger.info("worker log line")
    handlers[0].flush()
    assert "worker log line" in new_path.read_text(encoding="utf-8")


def test_worker_id_suffix_build():
    """worker_id 追加进日志文件名的拼接逻辑。"""
    base, ext = os.path.splitext("logs/app.log")
    worker_id = "Oscar-MacPro-1234-abcdef12"
    result = f"{base}.{worker_id}{ext}"
    assert result == "logs/app.Oscar-MacPro-1234-abcdef12.log"


def test_file_worker_id_config_read():
    """LOG_FILE_WORKER_ID 默认开启（跟随分布式模式），可显式关闭。"""
    settings = _FakeSettings({'LOG_FILE_WORKER_ID': True})
    config = LogConfig.from_settings(settings)
    assert config.file_worker_id is True

    config2 = LogConfig.from_settings(_FakeSettings({}))
    assert config2.file_worker_id is True  # 默认 True：切 distributed() 即自动生效

    config3 = LogConfig.from_settings(_FakeSettings({'LOG_FILE_WORKER_ID': False}))
    assert config3.file_worker_id is False  # 显式关闭


def test_set_file_path_idempotent(tmp_path):
    """连续调用 set_file_path 多次：handler 只保留一个、路径为最新值。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "a.log"),
        'LOG_CONSOLE_ENABLED': False,
    }))
    logger = LoggerFactory.get_logger("test_idempotent")
    new_path = str(tmp_path / "b.log")
    for _ in range(3):
        assert LogManager().set_file_path(new_path) is True

    file_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert len(file_handlers) == 1, f"handler 应唯一，实际 {len(file_handlers)}"
    assert file_handlers[0].baseFilename == new_path


def test_set_file_path_not_configured_returns_false():
    """日志系统未配置时 set_file_path 返回 False 且不抛异常。"""
    assert LogManager().set_file_path("/tmp/whatever.log") is False


def test_set_file_path_file_disabled_returns_false(tmp_path):
    """LOG_FILE_ENABLED=False 时 set_file_path 返回 False。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "off.log"),
        'LOG_FILE_ENABLED': False,
        'LOG_CONSOLE_ENABLED': False,
    }))
    assert LogManager().set_file_path(str(tmp_path / "off2.log")) is False


def test_set_file_path_preserves_configured_level(tmp_path):
    """动态换路径不丢失配置的文件级别（DEBUG 必须仍是 DEBUG）。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "lv.log"),
        'LOG_LEVEL': 'DEBUG',
        'LOG_CONSOLE_ENABLED': False,
    }))
    logger = LoggerFactory.get_logger("test_level")
    LogManager().set_file_path(str(tmp_path / "lv2.log"))
    file_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert file_handlers and file_handlers[0].level == logging.DEBUG


@pytest.mark.parametrize("file_path,worker_id,expected", [
    ("logs/app.log", "w1", "logs/app.w1.log"),
    ("logs/app", "w1", "logs/app.w1"),
    ("logs/a.b.c.log", "w-x", "logs/a.b.c.w-x.log"),
    ("logs/app.log", "host name-123-abc.def", "logs/app.host name-123-abc.def.log"),
    ("/abs/path/app.log", "w1", "/abs/path/app.w1.log"),
])
def test_worker_log_path_helper(file_path, worker_id, expected):
    """worker 日志路径拼接：只改文件名、保留目录与扩展名。"""
    assert worker_log_path(file_path, worker_id) == expected


def test_old_file_preserved_after_set_file_path(tmp_path):
    """动态换路径后旧日志文件保留（不删除、不覆盖），无数据丢失。"""
    from crawlo.logging import configure_logging
    old_path = tmp_path / "old.log"
    configure_logging(_FakeSettings({
        'LOG_FILE': str(old_path),
        'LOG_CONSOLE_ENABLED': False,
    }))
    logger = LoggerFactory.get_logger("test_old_preserve")
    logger.info("old content")
    for h in logger.handlers:
        if isinstance(h, TimedRotatingFileHandler):
            h.flush()

    new_path = tmp_path / "new.log"
    LogManager().set_file_path(str(new_path))
    logger.info("new content")
    for h in logger.handlers:
        if isinstance(h, TimedRotatingFileHandler):
            h.flush()

    assert old_path.exists(), "旧日志文件不应被删除"
    assert "old content" in old_path.read_text(encoding="utf-8")
    assert "new content" in new_path.read_text(encoding="utf-8")


def _make_mixin_stub(settings_data, worker_id="w-1-abc", logger=None):
    """构造 ClusterLifecycleMixin 桩：settings / _cluster_state / logger。"""
    stub = object.__new__(ClusterLifecycleMixin)
    stub.settings = _FakeSettings(settings_data)
    stub._cluster_state = MagicMock()
    stub._cluster_state.worker_id = worker_id
    stub.logger = logger or MagicMock()
    return stub


def test_apply_worker_id_updates_file_path(tmp_path):
    """进集群后 LOG_FILE 自动追加 worker_id（跟随模式默认开启）。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "app.log"),
        'LOG_CONSOLE_ENABLED': False,
    }))
    stub = _make_mixin_stub({}, worker_id="host-123-abc12345")
    stub._apply_worker_id_to_log_file()

    config = LogManager().config
    assert config.file_path == str(tmp_path / "app.host-123-abc12345.log")


def test_apply_worker_id_disabled_noop(tmp_path):
    """显式 LOG_FILE_WORKER_ID=False 时不修改日志路径。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "app.log"),
        'LOG_CONSOLE_ENABLED': False,
    }))
    stub = _make_mixin_stub({'LOG_FILE_WORKER_ID': False}, worker_id="w-1")
    stub._apply_worker_id_to_log_file()
    assert LogManager().config.file_path == str(tmp_path / "app.log")


def test_apply_worker_id_no_file_configured_noop():
    """日志系统未配置 / 无文件日志时静默跳过，不抛异常。"""
    LogManager().reset()
    stub = _make_mixin_stub({}, worker_id="w-1")
    stub._apply_worker_id_to_log_file()  # 不应抛异常


def test_apply_worker_id_no_worker_id_noop(tmp_path):
    """没有拿到 worker_id 时不改路径。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "app.log"),
        'LOG_CONSOLE_ENABLED': False,
    }))
    stub = _make_mixin_stub({}, worker_id=None)
    stub._apply_worker_id_to_log_file()
    assert LogManager().config.file_path == str(tmp_path / "app.log")


def test_apply_worker_id_special_chars(tmp_path):
    """worker_id 含空格/点号等特殊字符时路径仍正确拼接。"""
    from crawlo.logging import configure_logging
    configure_logging(_FakeSettings({
        'LOG_FILE': str(tmp_path / "app.log"),
        'LOG_CONSOLE_ENABLED': False,
    }))
    stub = _make_mixin_stub({}, worker_id="host name-123-abc.def")
    stub._apply_worker_id_to_log_file()
    assert LogManager().config.file_path == str(tmp_path / "app.host name-123-abc.def.log")


def test_log_manager_api_integrity():
    """LogManager 类 API 完整性：set_file_path/cleanup_old_logs 必须存在。

    防止重构时把后续方法误嵌套进新增模块级函数（曾导致 cleanup_old_logs
    从类中消失、引擎关闭时报 AttributeError）。
    """
    m = LogManager()
    assert callable(m.set_file_path)
    assert callable(m.cleanup_old_logs)
    assert callable(m.reset)


def test_cleanup_old_logs_removes_expired_only(tmp_path):
    """cleanup_old_logs 只清理过期文件，保留新文件（引擎关闭路径）。"""
    old = tmp_path / "old_20260505_171709.log"
    recent = tmp_path / "recent_20260811_120000.log"
    old.write_text("old", encoding="utf-8")
    recent.write_text("recent", encoding="utf-8")
    old_mtime = time.time() - 3 * 86400
    os.utime(old, (old_mtime, old_mtime))

    deleted = LogManager().cleanup_old_logs(log_dir=str(tmp_path), days=1)
    assert deleted == 1
    assert not old.exists(), "过期文件应被清理"
    assert recent.exists(), "新文件不应被清理"
