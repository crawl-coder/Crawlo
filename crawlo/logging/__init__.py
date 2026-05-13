#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Unified Logging System
=============================

Design Principles:
1. Simple first - avoid over-engineering
2. Performance first - reduce lock contention and complex logic
3. Consistency - unified logging interface
4. Reliability - ensure logs are always available
"""

import logging
from .manager import LogManager
from .factory import LoggerFactory
from .config import LogConfig

# Unified public interface
def get_logger(name: str = 'default') -> logging.Logger:
    """Get logger instance"""
    return LoggerFactory.get_logger(name)


def configure_logging(settings=None, **kwargs):
    """Configure logging system"""
    return LogManager().configure(settings, **kwargs)


def is_configured() -> bool:
    """Check if logging system is configured"""
    return LogManager().is_configured


__all__ = [
    'LogManager',
    'LoggerFactory',
    'LogConfig',
    'get_logger',
    'configure_logging',
    'is_configured'
]
