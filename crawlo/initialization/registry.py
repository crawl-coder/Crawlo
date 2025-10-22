#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化器注册表 - 管理所有初始化器的注册和执行
"""

import threading
from typing import Dict, Optional, Callable, List
from .context import InitializationContext
from .phases import InitializationPhase, PhaseResult


class Initializer:
    """初始化器基类"""
    
    def __init__(self, phase: InitializationPhase):
        self._phase = phase
    
    @property
    def phase(self) -> InitializationPhase:
        """获取初始化阶段"""
        return self._phase
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """执行初始化 - 子类必须实现"""
        raise NotImplementedError("Subclasses must implement initialize method")


class BaseInitializer(Initializer):
    """基础初始化器类 - 为向后兼容保留"""
    
    def __init__(self, phase: InitializationPhase):
        super().__init__(phase)
    
    def _create_result(self, success: bool, duration: float = 0.0, 
                      artifacts: Optional[Dict] = None, error: Optional[Exception] = None) -> PhaseResult:
        """创建初始化结果"""
        from .utils import create_initialization_result
        return create_initialization_result(
            phase=self.phase,
            success=success,
            duration=duration,
            artifacts=artifacts,
            error=error
        )


class InitializerRegistry:
    """
    初始化器注册表 - 管理所有初始化器的注册和执行
    
    特点：
    1. 线程安全的注册和执行
    2. 支持函数式和类式初始化器
    3. 统一的结果处理
    """
    
    def __init__(self):
        self._initializers: Dict[InitializationPhase, Initializer] = {}
        self._lock = threading.RLock()
    
    def register(self, initializer: Initializer):
        """注册初始化器"""
        with self._lock:
            phase = initializer.phase
            if phase in self._initializers:
                raise ValueError(f"Initializer for phase {phase} already registered")
            self._initializers[phase] = initializer
    
    def register_function(self, phase: InitializationPhase, 
                         init_func: Callable[[InitializationContext], PhaseResult]):
        """注册函数式初始化器"""
        
        class FunctionInitializer(Initializer):
            def __init__(self, phase: InitializationPhase, func: Callable):
                super().__init__(phase)
                self._phase = phase
                self._func = func
            
            def initialize(self, context: InitializationContext) -> PhaseResult:
                return self._func(context)
        
        self.register(FunctionInitializer(phase, init_func))
    
    def get_initializer(self, phase: InitializationPhase) -> Optional[Initializer]:
        """获取指定阶段的初始化器"""
        with self._lock:
            return self._initializers.get(phase)
    
    def get_all_phases(self) -> List[InitializationPhase]:
        """获取所有已注册的阶段"""
        with self._lock:
            return list(self._initializers.keys())
    
    def has_initializer(self, phase: InitializationPhase) -> bool:
        """检查是否有指定阶段的初始化器"""
        with self._lock:
            return phase in self._initializers
    
    def clear(self):
        """清空注册表"""
        with self._lock:
            self._initializers.clear()
    
    def execute_phase(self, phase: InitializationPhase, 
                     context: InitializationContext) -> PhaseResult:
        """执行指定阶段的初始化"""
        initializer = self.get_initializer(phase)
        if not initializer:
            error = ValueError(f"No initializer registered for phase {phase}")
            return PhaseResult(
                phase=phase,
                success=False,
                error=error
            )
        
        try:
            return initializer.initialize(context)
        except Exception as e:
            return PhaseResult(
                phase=phase,
                success=False,
                error=e
            )


# 全局注册表实例
_global_registry = InitializerRegistry()


def get_global_registry() -> InitializerRegistry:
    """获取全局注册表"""
    return _global_registry


def register_initializer(initializer: Initializer):
    """注册初始化器到全局注册表"""
    _global_registry.register(initializer)


def register_phase_function(phase: InitializationPhase, 
                           init_func: Callable[[InitializationContext], PhaseResult]):
    """注册函数式初始化器到全局注册表"""
    _global_registry.register_function(phase, init_func)