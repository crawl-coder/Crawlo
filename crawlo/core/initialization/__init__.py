#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 框架初始化系统（从 crawlo.core.application 迁出）
=======================================================

子包结构：
- phases.py:     阶段定义 + 依赖校验
- context.py:    InitializationContext
- utils.py:      工具函数
- registry.py:   Initializer + InitializerRegistry
- built_in.py:   5 个内置初始化器
- core.py:       CoreInitializer

顶层公共接口：
- initialize_framework: 初始化框架主入口
- is_framework_ready: 检查框架是否就绪
- get_framework_context: 获取初始化上下文
"""
from crawlo.core.initialization.phases import (
    InitializationPhase,
    PhaseResult,
    PhaseDefinition,
    PHASE_DEFINITIONS,
    get_phase_definition,
    get_execution_order,
    validate_dependencies,
    detect_circular_dependencies,
    validate_phase_dependencies,
)
from crawlo.core.initialization.context import InitializationContext
from crawlo.core.initialization.utils import (
    create_initialization_result,
    InitializationTimer,
)
from crawlo.core.initialization.registry import (
    Initializer,
    BaseInitializer,
    InitializerRegistry,
    get_global_registry,
    register_initializer,
    register_phase_function,
)
from crawlo.core.initialization.built_in import (
    LoggingInitializer,
    SettingsInitializer,
    CoreComponentsInitializer,
    ExtensionsInitializer,
    FrameworkStartupLogger,
    register_built_in_initializers,
)
from crawlo.core.initialization.core import CoreInitializer


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
    # phases
    "InitializationPhase",
    "PhaseResult",
    "PhaseDefinition",
    "PHASE_DEFINITIONS",
    "get_phase_definition",
    "get_execution_order",
    "validate_dependencies",
    "detect_circular_dependencies",
    "validate_phase_dependencies",
    # context
    "InitializationContext",
    # utils
    "create_initialization_result",
    "InitializationTimer",
    # registry
    "Initializer",
    "BaseInitializer",
    "InitializerRegistry",
    "get_global_registry",
    "register_initializer",
    "register_phase_function",
    # built_in
    "LoggingInitializer",
    "SettingsInitializer",
    "CoreComponentsInitializer",
    "ExtensionsInitializer",
    "FrameworkStartupLogger",
    "register_built_in_initializers",
    # core
    "CoreInitializer",
    # 顶层公共接口
    "initialize_framework",
    "is_framework_ready",
    "get_framework_context",
]
