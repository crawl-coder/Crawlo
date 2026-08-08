# -*- coding: UTF-8 -*-
"""
事件循环清理工具
================

解决 Windows 平台 asyncio ProactorEventLoop 的资源泄漏警告问题。

在 crawlo/__init__.py 中自动调用 apply_windows_patches()，
无需用户手动干预。
"""
import asyncio
import sys
import warnings


def apply_windows_patches():
    """
    自动应用 Windows 平台的 asyncio 补丁（在 crawlo 包导入时调用）。

    解决的问题：
    ProactorEventLoop 的 pipe transport 在 __del__ 析构时，
    __repr__ 会调用 self._sock.fileno()，但此时 socket 已关闭，
    导致 ValueError("I/O operation on closed pipe")。

    这个异常由 Python 解释器直接输出到 stderr，不经过 warnings 模块，
    所以 warnings.filterwarnings 无法拦截，只能通过猴子补丁修复。
    """
    if sys.platform != 'win32':
        return

    _patch_proactor_pipe_transport()
    _patch_base_subprocess_transport()

    warnings.filterwarnings('ignore', message='unclosed transport', category=ResourceWarning)


def _patch_proactor_pipe_transport():
    """修补 _ProactorBasePipeTransport.__del__ 以捕获析构时的 ValueError"""
    try:
        import asyncio.proactor_events
        _cls = asyncio.proactor_events._ProactorBasePipeTransport
        _original_del = _cls.__del__

        def _patched_del(self):
            try:
                _original_del(self)
            except (ValueError, OSError):
                pass

        _cls.__del__ = _patched_del
    except Exception:
        pass


def _patch_base_subprocess_transport():
    """修补 BaseSubprocessTransport.__del__ 以捕获析构时的 ValueError"""
    try:
        import asyncio.base_subprocess
        _cls = asyncio.base_subprocess.BaseSubprocessTransport
        _original_del = _cls.__del__

        def _patched_del(self):
            try:
                _original_del(self)
            except (ValueError, OSError):
                pass

        _cls.__del__ = _patched_del
    except Exception:
        pass


def run_with_cleanup(coro):
    """
    运行协程。asyncio.run() 的直接替代。

    注意: 只能在主程序中使用，不能在已运行的事件循环中调用。
    """
    return asyncio.run(coro)
