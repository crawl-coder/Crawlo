#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化器注册表 - 管理各种初始化器
"""

import threading
from typing import Dict, List, Callable, Type, Optional, Protocol
from abc import ABC, abstractmethod

from .phases import InitializationPhase, PhaseResult
from .context import InitializationContext


class Initializer(Protocol):
    """初始化器协议"""
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """执行初始化"""
        ...
    
    @property
    def phase(self) -> InitializationPhase:
        """初始化器负责的阶段"""
        ...


class BaseInitializer(ABC):
    """初始化器基类"""
    
    def __init__(self, phase: InitializationPhase):
        self._phase = phase
    
    @property
    def phase(self) -> InitializationPhase:
        return self._phase
    
    @abstractmethod
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """执行初始化 - 子类必须实现"""
        pass
    
    def _create_result(self, success: bool, duration: float = 0.0, 
                      error: Optional[Exception] = None, 
                      artifacts: Optional[dict] = None) -> PhaseResult:
        """创建阶段结果的辅助方法"""
        return PhaseResult(
            phase=self._phase,
            success=success,
            duration=duration,
            error=error,
            artifacts=artifacts or {}
        )


class InitializerRegistry:
    """
    初始化器注册表
    
    管理所有初始化器的注册、查找和执行
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
        
        class FunctionInitializer:
            def __init__(self, phase: InitializationPhase, func: Callable):
                self._phase = phase
                self._func = func
            
            @property  
            def phase(self) -> InitializationPhase:
                return self._phase
            
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