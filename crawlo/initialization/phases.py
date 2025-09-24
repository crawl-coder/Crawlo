#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化阶段定义
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class InitializationPhase(Enum):
    """初始化阶段枚举"""
    
    # 阶段0：准备阶段
    PREPARING = "preparing"
    
    # 阶段1：日志系统初始化
    LOGGING = "logging"
    
    # 阶段2：配置系统初始化  
    SETTINGS = "settings"
    
    # 阶段3：核心组件初始化
    CORE_COMPONENTS = "core_components"
    
    # 阶段4：扩展组件初始化
    EXTENSIONS = "extensions"
    
    # 阶段5：框架启动日志记录
    FRAMEWORK_STARTUP_LOG = "framework_startup_log"
    
    # 阶段6：完成
    COMPLETED = "completed"
    
    # 错误状态
    ERROR = "error"


@dataclass
class PhaseResult:
    """阶段执行结果"""
    phase: InitializationPhase
    success: bool
    duration: float = 0.0
    error: Optional[Exception] = None
    artifacts: dict = None  # 阶段产生的工件
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = {}


@dataclass 
class PhaseDefinition:
    """阶段定义"""
    phase: InitializationPhase
    name: str
    description: str
    dependencies: List[InitializationPhase] = None
    optional: bool = False
    timeout: float = 30.0  # 超时时间（秒）
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


# 预定义的初始化阶段
PHASE_DEFINITIONS = [
    PhaseDefinition(
        phase=InitializationPhase.PREPARING,
        name="准备阶段",
        description="初始化基础环境和检查前置条件",
        dependencies=[],
        timeout=5.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.LOGGING,
        name="日志系统",
        description="配置和初始化日志系统",
        dependencies=[],  # 移除对PREPARING的依赖
        timeout=10.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.SETTINGS,
        name="配置系统", 
        description="加载和验证配置",
        dependencies=[InitializationPhase.LOGGING],
        timeout=15.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.CORE_COMPONENTS,
        name="核心组件",
        description="初始化框架核心组件",
        dependencies=[InitializationPhase.SETTINGS],
        timeout=20.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.EXTENSIONS,
        name="扩展组件",
        description="加载和初始化扩展组件",
        dependencies=[InitializationPhase.CORE_COMPONENTS],
        optional=True,
        timeout=15.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.FRAMEWORK_STARTUP_LOG,
        name="框架启动日志",
        description="记录框架启动相关信息",
        dependencies=[InitializationPhase.LOGGING, InitializationPhase.SETTINGS],
        timeout=5.0
    ),
    PhaseDefinition(
        phase=InitializationPhase.COMPLETED,
        name="初始化完成",
        description="框架初始化完成",
        dependencies=[
            InitializationPhase.CORE_COMPONENTS,
            InitializationPhase.FRAMEWORK_STARTUP_LOG
        ],  # Extensions是可选的
        timeout=5.0
    )
]


def get_phase_definition(phase: InitializationPhase) -> Optional[PhaseDefinition]:
    """获取阶段定义"""
    for definition in PHASE_DEFINITIONS:
        if definition.phase == phase:
            return definition
    return None


def get_execution_order() -> List[InitializationPhase]:
    """获取执行顺序"""
    return [definition.phase for definition in PHASE_DEFINITIONS]


def validate_dependencies() -> bool:
    """验证阶段依赖关系的正确性"""
    phases = {definition.phase for definition in PHASE_DEFINITIONS}
    
    for definition in PHASE_DEFINITIONS:
        for dependency in definition.dependencies:
            if dependency not in phases:
                return False
    
    return True