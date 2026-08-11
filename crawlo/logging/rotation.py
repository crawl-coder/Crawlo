#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
跨平台安全的日志轮转 Handler
============================

标准库 ``TimedRotatingFileHandler.doRollover`` 在轮转文件重命名失败时
（``rotate`` 内部 ``except OSError: pass``）会**静默失效**：

- Windows：日志文件被其他进程占用（杀毒软件、Windows Search 索引、
  日志查看器、备份工具）时 ``os.rename`` 失败，日志继续写入旧文件且
  无限增长，轮转形同虚设；
- Linux/macOS：rename 通常成功，但极端场景（只读挂载、权限变更）同样
  会静默失败。

本类解决：
1. **失败可见**：轮转失败时记录 WARNING（含平台信息），不再静默；
2. **不崩溃**：轮转失败后继续写当前文件，进程不受影响；
3. **不丢日志**：每次 emit 后 flush，Windows 下 close/reopen 不丢缓冲。
"""

import logging
import os
import platform
import time
from logging.handlers import TimedRotatingFileHandler


# 轮转告警重入保护：告警通过 crawlo.logging.rotation logger 输出，
# 若该 logger 自身挂载了同一个文件 handler，失败告警 -> emit -> doRollover
# -> 再告警会形成递归；此标志防止递归，同时避免同一时刻刷屏。
_in_rollover_warn = False


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """按时间轮转 + Windows 安全处理。"""

    def doRollover(self):
        """执行轮转；失败时告警并继续写当前文件。"""
        # 记录轮转前的文件状态，用于检测 rename 是否真正生效
        try:
            before = os.stat(self.baseFilename)
            before_key = (before.st_size, before.st_mtime_ns)
        except OSError:
            before_key = None

        try:
            super().doRollover()
        except OSError as exc:
            # 标准库 rotate 内部吞掉 rename 错误，但 os.remove(dfn) /
            # getFilesToDelete 的 remove 会抛 OSError —— 这里兜底
            self._warn_rollover_failed(f"轮转异常: {exc}")
            self._reopen_stream()
            return

        # 检测 rename 是否成功：成功后 baseFilename 被新建（size≈0）；
        # 失败则旧文件保持原样（标准库静默 pass）。
        try:
            after = os.stat(self.baseFilename)
            after_key = (after.st_size, after.st_mtime_ns)
        except OSError:
            after_key = None
        if before_key is not None and after_key == before_key:
            self._warn_rollover_failed(
                "轮转文件重命名失败（文件可能被其他进程占用）"
            )

    def emit(self, record):
        """写入后立即 flush，降低 Windows 下缓冲丢失风险。"""
        try:
            super().emit(record)
            self.flush()
        except Exception:
            self.handleError(record)

    def _reopen_stream(self):
        """轮转失败后确保流仍可写。"""
        try:
            if self.stream is None:
                self.stream = self._open()
        except OSError as exc:
            self._warn_rollover_failed(f"重开日志文件失败: {exc}")

    def _warn_rollover_failed(self, reason: str) -> None:
        """记录轮转失败告警（一次性去重，避免刷屏）。"""
        global _in_rollover_warn
        if _in_rollover_warn:
            return
        _in_rollover_warn = True
        now = int(time.time())
        try:
            if getattr(self, "_last_rollover_warn_ts", 0) == now:
                return
            self._last_rollover_warn_ts = now
            logging.getLogger("crawlo.logging.rotation").warning(
                "日志轮转失败（platform=%s, file=%s, reason=%s）—— "
                "日志将继续写入当前文件，建议检查是否有进程占用该文件；"
                "长时间不处理会导致日志文件无限增长。",
                platform.system(),
                self.baseFilename,
                reason,
            )
        finally:
            _in_rollover_warn = False
