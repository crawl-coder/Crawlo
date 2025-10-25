#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化阶段定义
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict


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


def detect_circular_dependencies() -> Optional[List[InitializationPhase]]:
    """
    检测循环依赖
    
    使用DFS（深度优先搜索）算法检测初始化阶段的循环依赖。
    
    Returns:
        Optional[List[InitializationPhase]]: 如果存在循环，返回循环路径；否则返回None
    
    算法说明：
        使用三色标记法：
        - 白色(0)：未访问
        - 灰色(1)：正在访问（在当前DFS路径中）
        - 黑色(2)：已完成访问
        
        如果在DFS过程中遇到灰色节点，说明存在循环依赖。
    """
    # 构建依赖图
    dependency_graph: Dict[InitializationPhase, List[InitializationPhase]] = {}
    for definition in PHASE_DEFINITIONS:
        dependency_graph[definition.phase] = definition.dependencies.copy()
    
    # 三色标记：0-白色(未访问)，1-灰色(访问中)，2-黑色(已完成)
    color: Dict[InitializationPhase, int] = {phase: 0 for phase in dependency_graph}
    parent: Dict[InitializationPhase, Optional[InitializationPhase]] = {phase: None for phase in dependency_graph}
    
    def dfs(node: InitializationPhase) -> Optional[List[InitializationPhase]]:
        """DFS遍历检测循环"""
        color[node] = 1  # 标记为灰色（访问中）
        
        for neighbor in dependency_graph.get(node, []):
            if color[neighbor] == 1:  # 遇到灰色节点，发现循环
                # 重建循环路径
                cycle = [neighbor]
                current: Optional[InitializationPhase] = node
                while current is not None and current != neighbor:
                    cycle.append(current)
                    current = parent.get(current)
                cycle.append(neighbor)
                cycle.reverse()
                return cycle
            
            if color[neighbor] == 0:  # 未访问的节点
                parent[neighbor] = node
                result = dfs(neighbor)
                if result:
                    return result
        
        color[node] = 2  # 标记为黑色（已完成）
        return None
    
    # 对所有未访问的节点执行DFS
    for phase in dependency_graph:
        if color[phase] == 0:
            cycle = dfs(phase)
            if cycle:
                return cycle
    
    return None


def validate_phase_dependencies() -> tuple[bool, Optional[str]]:
    """
    全面验证阶段依赖关系
    
    Returns:
        tuple[bool, Optional[str]]: (是否有效, 错误信息)
    """
    # 1. 检查依赖是否存在
    if not validate_dependencies():
        return False, "存在未定义的依赖阶段"
    
    # 2. 检查循环依赖
    cycle = detect_circular_dependencies()
    if cycle:
        cycle_path = ' -> '.join([phase.value for phase in cycle])
        return False, f"检测到循环依赖: {cycle_path}"
    
    return True, None