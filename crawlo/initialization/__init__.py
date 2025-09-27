#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架统一初始化系统
=======================

设计原则：
1. 单一职责 - 每个初始化器负责特定领域
2. 依赖清晰 - 明确的初始化顺序和依赖关系
3. 可测试性 - 支持依赖注入和模拟
4. 健壮性 - 优雅的错误处理和降级策略
"""

from .registry import InitializerRegistry
from .context import InitializationContext
from .core import CoreInitializer
from .phases import InitializationPhase


# 公共接口
def initialize_framework(settings=None, **kwargs):
    """初始化框架的主要入口"""
    return CoreInitializer().initialize(settings, **kwargs)


def is_framework_ready():
    """检查框架是否已准备就绪"""
    return CoreInitializer().is_ready


def get_framework_context():
    """获取框架初始化上下文"""
    return CoreInitializer().context


__all__ = [
    'InitializerRegistry',
    'InitializationContext',
    'CoreInitializer',
    'InitializationPhase',
    'initialize_framework',
    'is_framework_ready',
    'get_framework_context'
]
