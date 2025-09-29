#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo统一日志系统
=================

设计原则：
1. 简单优先 - 避免过度设计
2. 性能优先 - 减少锁竞争和复杂逻辑  
3. 一致性 - 统一的日志接口
4. 可靠性 - 确保日志始终可用
"""

from .manager import LogManager
from .factory import LoggerFactory
from .config import LogConfig
from .monitor import LogPerformanceMonitor

# 统一的公共接口
def get_logger(name: str = 'default'):
    """获取logger实例"""
    return LoggerFactory.get_logger(name)

def configure_logging(settings=None, **kwargs):
    """配置日志系统"""
    return LogManager().configure(settings, **kwargs)

def is_configured() -> bool:
    """检查日志系统是否已配置"""
    return LogManager().is_configured

def get_monitor() -> LogPerformanceMonitor:
    """获取日志性能监控器"""
    from .monitor import get_monitor as _get_monitor
    return _get_monitor()

__all__ = [
    'LogManager',
    'LoggerFactory', 
    'LogConfig',
    'LogPerformanceMonitor',
    'get_logger',
    'configure_logging',
    'is_configured',
    'get_monitor'
]