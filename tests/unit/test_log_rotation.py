#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日志轮转测试（P0-稳定化：固定文件名 + 按天轮转）
=================================================

验证：
1. LogConfig 正确读取 LOG_FILE_WHEN / LOG_FILE_BACKUP_COUNT / LOG_FILE_UTF8_BACKUP；
2. LoggerFactory 创建 TimedRotatingFileHandler（when/backupCount/encoding 正确）；
3. 默认值：midnight / 7 / utf-8。
4. 边界/极端场景：全部 when 取值、backupCount=0/负数、UTF-8 轮转、目录自动创建、
   非法配置早失败、权限拒绝降级、轮转失败告警去重/递归防护、子进程真实轮转。
"""

import logging
import os
import subprocess
import sys
import textwrap
import time
from logging.handlers import TimedRotatingFileHandler
from unittest.mock import patch

import pytest

from crawlo.logging.config import LogConfig
from crawlo.logging.factory import LoggerFactory, _create_file_handler
from crawlo.logging.manager import LogManager
from crawlo.logging.rotation import SafeTimedRotatingFileHandler


class _FakeSettings:
    """模拟 settings 对象（get 方法返回配置）。"""

    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


@pytest.fixture(autouse=True)
def _reset_logging_state():
    """每个用例独立：清空单例配置与 logger 缓存，避免跨用例污染。"""
    LogManager().reset()
    LoggerFactory.clear_cache()
    yield
    LogManager().reset()
    LoggerFactory.clear_cache()


def test_log_config_reads_rotation_settings():
    """LogConfig 从 settings 读取轮转配置。"""
    settings = _FakeSettings({
        'LOG_FILE': 'logs/demo.log',
        'LOG_FILE_WHEN': 'midnight',
        'LOG_FILE_BACKUP_COUNT': 14,
        'LOG_FILE_UTF8_BACKUP': True,
    })
    config = LogConfig.from_settings(settings)
    assert config.file_when == 'midnight'
    assert config.file_backup_count == 14
    assert config.file_utf8_backup is True


def test_log_config_defaults():
    """无配置时轮转默认值：midnight / 7 / utf-8。"""
    config = LogConfig.from_settings(_FakeSettings({}))
    assert config.file_when == 'midnight'
    assert config.file_backup_count == 7
    assert config.file_utf8_backup is True


def test_logger_uses_timed_rotating_handler(tmp_path):
    """LoggerFactory 创建的 file handler 必须是 TimedRotatingFileHandler。"""
    log_file = tmp_path / "demo.log"
    settings = _FakeSettings({
        'LOG_FILE': str(log_file),
        'LOG_FILE_WHEN': 'midnight',
        'LOG_FILE_BACKUP_COUNT': 7,
        'LOG_FILE_UTF8_BACKUP': True,
        'LOG_CONSOLE_ENABLED': False,   # 只测文件 handler
    })

    # 走真实配置路径
    from crawlo.logging import configure_logging
    from crawlo.logging.factory import LoggerFactory
    configure_logging(settings)
    logger = LoggerFactory.get_logger("test_rotation_real")

    handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert handlers, f"未找到 TimedRotatingFileHandler，实际 handlers: {logger.handlers}"
    handler = handlers[0]
    assert handler.when == 'MIDNIGHT'  # TimedRotatingFileHandler 内部规范化为大写
    assert handler.backupCount == 7
    assert handler.encoding == 'utf-8'
    # 验证日志真的写入
    logger.info("rotation test log line")
    handler.flush()
    assert log_file.exists(), "日志文件未创建"
    assert "rotation test log line" in log_file.read_text(encoding='utf-8')


def test_rotation_backup_count_limits(tmp_path):
    """backupCount 生效：超过后旧轮转文件被清理。"""
    from logging.handlers import TimedRotatingFileHandler
    import time

    log_file = tmp_path / "rotate.log"
    handler = TimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    base = int(time.time()) - 10
    try:
        # 直接推进 rolloverAt 使每次轮转后缀不同（确定性，不依赖 sleep）
        for i in range(6):
            handler.rolloverAt = base + i + 1
            handler.doRollover()
        backup_files = [p for p in tmp_path.iterdir() if p.name.startswith("rotate.log.")]
        # backupCount=2 → 恰保留 2 份轮转文件（+1 当前文件）
        assert len(backup_files) == 2, f"轮转文件数 {len(backup_files)} != backupCount=2"
    finally:
        handler.close()


def test_rollover_rename_failure_is_visible_not_silent(tmp_path, caplog):
    """Windows 场景：rename 失败必须告警且不崩溃（不静默失效）。"""
    import logging

    log_file = tmp_path / "win.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    try:
        # 模拟 Windows：rename 被占用文件失败
        with patch(
            "crawlo.logging.rotation.os.rename",
            side_effect=PermissionError(13, "Permission denied"),
        ):
            with caplog.at_level(logging.WARNING, logger="crawlo.logging.rotation"):
                handler.doRollover()
                # 触发一次告警
                handler.doRollover()

        # 不崩溃，且告警记录了轮转失败
        assert any("轮转失败" in r.message for r in caplog.records), caplog.text
        # 日志文件仍可写（降级继续）
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "still writing", (), None))
        assert "still writing" in log_file.read_text(encoding="utf-8")
    finally:
        handler.close()


@pytest.mark.parametrize("when", ["S", "M", "H", "D", "W0", "W3", "W6", "midnight"])
def test_all_when_values_rotate_without_error(tmp_path, when):
    """全部支持轮转周期都能创建 handler 并完成一次轮转。"""
    log_file = tmp_path / f"r_{when}.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when=when, backupCount=1, encoding="utf-8"
    )
    try:
        handler.doRollover()
        backups = [p for p in tmp_path.iterdir() if p.name.startswith(f"r_{when}.log.")]
        assert backups, f"when={when} 轮转后未生成备份文件"
        # 备份文件非空目录条目（由轮转产生）
        assert all(p.is_file() for p in backups)
    finally:
        handler.close()


def test_backup_count_zero_keeps_all(tmp_path):
    """backupCount=0 表示不限制：轮转文件全部保留。"""
    log_file = tmp_path / "keep_all.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=0, encoding="utf-8"
    )
    base = int(time.time()) - 10
    try:
        for _ in range(3):
            handler.rolloverAt = base + _ + 1
            handler.doRollover()
        backups = [p for p in tmp_path.iterdir() if p.name.startswith("keep_all.log.")]
        assert len(backups) == 3, f"backupCount=0 应保留全部轮转文件，实际 {len(backups)}"
    finally:
        handler.close()


def test_backup_count_negative_keeps_all(tmp_path):
    """backupCount<0 同样不限制（标准库约定仅 >0 时清理）。"""
    log_file = tmp_path / "neg.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=-1, encoding="utf-8"
    )
    base = int(time.time()) - 10
    try:
        for _ in range(3):
            handler.rolloverAt = base + _ + 1
            handler.doRollover()
        backups = [p for p in tmp_path.iterdir() if p.name.startswith("neg.log.")]
        assert len(backups) == 3
    finally:
        handler.close()


def test_utf8_content_survives_rotation(tmp_path):
    """中文日志在真实轮转后 UTF-8 不乱码。"""
    log_file = tmp_path / "utf8.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    try:
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "第一行中文日志", (), None))
        time.sleep(1.1)
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "第二行中文日志", (), None))
        handler.flush()
    finally:
        handler.close()

    all_text = ""
    for p in tmp_path.iterdir():
        if p.name.startswith("utf8.log"):
            all_text += p.read_text(encoding="utf-8")
    assert "第一行中文日志" in all_text
    assert "第二行中文日志" in all_text


def test_nested_log_dir_auto_created(tmp_path):
    """日志目录不存在时自动递归创建。"""
    log_file = tmp_path / "a" / "b" / "c" / "demo.log"
    config = LogConfig(file_path=str(log_file), file_enabled=True)
    handler = _create_file_handler(config)
    try:
        assert log_file.parent.exists(), "未自动创建嵌套日志目录"
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "nested dir", (), None))
        handler.flush()
        assert log_file.exists()
    finally:
        handler.close()


def test_invalid_when_rejected_early(tmp_path):
    """非法 LOG_FILE_WHEN 在配置阶段即失败，给出明确错误而非深层 traceback。"""
    config = LogConfig(file_when="X")
    ok, msg = config.validate()
    assert not ok and "LOG_FILE_WHEN" in msg

    from crawlo.logging import configure_logging
    with pytest.raises(ValueError, match="LOG_FILE_WHEN"):
        configure_logging(_FakeSettings({
            'LOG_FILE': str(tmp_path / "bad.log"),
            'LOG_FILE_WHEN': 'X',
        }))


def test_file_utf8_backup_flag_controls_encoding(tmp_path):
    """LOG_FILE_UTF8_BACKUP=True 强制 UTF-8；False 时跟随 LOG_ENCODING。"""
    log_file = tmp_path / "enc.log"
    utf8_handler = _create_file_handler(LogConfig(
        file_path=str(log_file), encoding="gbk", file_utf8_backup=True,
    ))
    try:
        assert utf8_handler.encoding == "utf-8"
    finally:
        utf8_handler.close()

    gbk_handler = _create_file_handler(LogConfig(
        file_path=str(log_file), encoding="gbk", file_utf8_backup=False,
    ))
    try:
        assert gbk_handler.encoding == "gbk"
    finally:
        gbk_handler.close()


def test_rollover_warning_deduped_within_second(tmp_path, caplog):
    """同一秒内重复失败只告警一次；跨秒后允许再次告警（防刷屏但不永久沉默）。"""
    log_file = tmp_path / "dedup.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    try:
        with patch(
            "crawlo.logging.rotation.os.rename",
            side_effect=PermissionError(13, "Permission denied"),
        ):
            with caplog.at_level(logging.WARNING, logger="crawlo.logging.rotation"):
                handler.doRollover()
                handler.doRollover()
                handler.doRollover()
                first_batch = [r for r in caplog.records if "轮转失败" in r.message]
                assert len(first_batch) == 1, f"同一秒应只告警 1 次，实际 {len(first_batch)}"
            time.sleep(1.1)
            with caplog.at_level(logging.WARNING, logger="crawlo.logging.rotation"):
                handler.doRollover()
                second_batch = [r for r in caplog.records if "轮转失败" in r.message]
                assert len(second_batch) == 2, "跨秒后应产生新的告警"
    finally:
        handler.close()


def test_successful_rollover_no_false_warning(tmp_path, caplog):
    """轮转成功时不得误报失败。"""
    log_file = tmp_path / "ok.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    try:
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "before", (), None))
        time.sleep(1.1)
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "after", (), None))
        handler.flush()
    finally:
        handler.close()
    assert not any("轮转失败" in r.message for r in caplog.records), caplog.text
    backups = [p for p in tmp_path.iterdir() if p.name.startswith("ok.log.")]
    assert backups, "成功轮转应生成备份文件"


def test_emit_write_failure_does_not_crash(tmp_path):
    """底层写入异常交给 handleError，不向上抛、不影响调用方。"""
    log_file = tmp_path / "emit.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    handled = []
    try:
        with patch.object(handler, "handleError", side_effect=lambda r: handled.append(r)):
            with patch.object(handler.stream, "write", side_effect=OSError(28, "No space left")):
                handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "boom", (), None))
        assert handled, "写入失败应进入 handleError"
    finally:
        handler.close()


def test_rollover_backup_removal_failure_warns_and_continues(tmp_path, caplog):
    """备份文件同名清理失败（Windows 占用）→ 告警且进程继续可写。"""
    import time as _time

    log_file = tmp_path / "rm.log"
    handler = SafeTimedRotatingFileHandler(
        str(log_file), when="S", interval=1, backupCount=2, encoding="utf-8"
    )
    # 预置一个与本次轮转目标同名的备份文件，让 doRollover 走到 os.remove
    t = handler.rolloverAt - handler.interval
    target = str(log_file) + "." + _time.strftime(handler.suffix, _time.localtime(t))
    with open(target, "w", encoding="utf-8") as f:
        f.write("old backup")

    try:
        with patch("crawlo.logging.rotation.os.remove", side_effect=PermissionError(13, "denied")):
            with caplog.at_level(logging.WARNING, logger="crawlo.logging.rotation"):
                handler.doRollover()
        assert any("轮转失败" in r.message for r in caplog.records), caplog.text
        handler.emit(logging.LogRecord("t", logging.INFO, __file__, 1, "still alive", (), None))
        handler.flush()
        assert "still alive" in log_file.read_text(encoding="utf-8")
    finally:
        handler.close()


def test_permission_denied_dir_falls_back_to_console(tmp_path, caplog):
    """日志目录只读时：文件 handler 创建失败 → 降级 console，不崩溃。"""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root 下无法模拟权限拒绝")

    ro_dir = tmp_path / "ro"
    ro_dir.mkdir()
    os.chmod(ro_dir, 0o555)
    try:
        settings = _FakeSettings({
            'LOG_FILE': str(ro_dir / "app.log"),
            'LOG_CONSOLE_ENABLED': False,
            'LOG_FILE_ENABLED': True,
        })
        from crawlo.logging import configure_logging
        configure_logging(settings)
        logger = LoggerFactory.get_logger("test_permission_fallback")
        file_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
        assert not file_handlers, "只读目录不应创建文件 handler"
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers), \
            "应降级为 console handler"
    finally:
        os.chmod(ro_dir, 0o755)


def test_subprocess_real_time_rotation(tmp_path):
    """跨进程真实时间轮转：子进程按 S 轮转，父进程校验备份数量与内容。"""
    log_file = tmp_path / "sub.log"
    script = textwrap.dedent(f"""
        import logging, sys, time
        from logging.handlers import TimedRotatingFileHandler
        path = {str(log_file)!r}
        h = TimedRotatingFileHandler(path, when="S", interval=1, backupCount=2, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("subrot")
        logger.setLevel(logging.INFO)
        logger.addHandler(h)
        logger.info("轮转前-第一秒")
        time.sleep(3.3)
        logger.info("轮转后-第四秒")
        time.sleep(1.1)
        logger.info("轮转后-第五秒")
        h.flush()
        h.close()
        print("DONE")
    """)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=30, check=False,
        cwd=os.getcwd(),
    )
    assert proc.returncode == 0, proc.stderr
    assert "DONE" in proc.stdout
    backups = sorted(p for p in tmp_path.iterdir() if p.name.startswith("sub.log."))
    # backupCount=2：任意时刻最多 2 个轮转备份
    assert len(backups) <= 2, f"轮转文件数 {len(backups)} > backupCount=2"
    all_text = ""
    for p in [log_file] + backups:
        all_text += p.read_text(encoding="utf-8")
    assert "轮转前-第一秒" in all_text
    assert "轮转后-第四秒" in all_text
    assert "轮转后-第五秒" in all_text
