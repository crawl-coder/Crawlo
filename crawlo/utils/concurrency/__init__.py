#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
并发工具子包
=============
提供线程安全的异步锁、事件循环清理、进程信号处理等并发原语。
"""
from .async_lock import (
    AsyncRLock,
    AsyncLock,
    AsyncSemaphore,
    AsyncEvent,
    AsyncCondition,
)
from .asyncio_utils import (
    apply_windows_patches,
    run_with_cleanup,
)
from .process_utils import (
    ProcessSignalHandler,
    SpiderDiscoveryUtils,
    SettingsUtils,
)

__all__ = [
    # async_lock
    'AsyncRLock',
    'AsyncLock',
    'AsyncSemaphore',
    'AsyncEvent',
    'AsyncCondition',
    # asyncio_utils
    'apply_windows_patches',
    'run_with_cleanup',
    # process_utils
    'ProcessSignalHandler',
    'SpiderDiscoveryUtils',
    'SettingsUtils',
]
