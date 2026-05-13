#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Initializer Registry - Manage registration and execution of all initializers
"""

import threading
from typing import Dict, Optional, Callable, List, Any
from .context import InitializationContext
from .phases import InitializationPhase, PhaseResult


class Initializer:
    """Initializer base class"""
    
    def __init__(self, phase: InitializationPhase):
        self._phase = phase
    
    @property
    def phase(self) -> InitializationPhase:
        """Get initialization phase"""
        return self._phase
    
    def initialize(self, context: InitializationContext) -> PhaseResult:
        """Execute initialization - subclasses must implement"""
        raise NotImplementedError("Subclasses must implement initialize method")


class BaseInitializer(Initializer):
    """Base initializer class - retained for backward compatibility"""
    
    def __init__(self, phase: InitializationPhase):
        super().__init__(phase)
    
    def _create_result(self, success: bool, duration: float = 0.0, 
                      artifacts: Optional[Dict[str, Any]] = None, error: Optional[Exception] = None) -> PhaseResult:
        """Create initialization result"""
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
    Initializer Registry - Manage registration and execution of all initializers
    
    Features:
    1. Thread-safe registration and execution
    2. Support for function-based and class-based initializers
    3. Unified result handling
    """
    
    def __init__(self):
        self._initializers: Dict[InitializationPhase, Initializer] = {}
        self._lock = threading.RLock()
    
    def register(self, initializer: Initializer):
        """Register initializer"""
        with self._lock:
            phase = initializer.phase
            if phase in self._initializers:
                raise ValueError(f"Initializer for phase {phase} already registered")
            self._initializers[phase] = initializer
    
    def register_function(self, phase: InitializationPhase, 
                         init_func: Callable[[InitializationContext], PhaseResult]):
        """Register function-based initializer"""
        
        class FunctionInitializer(Initializer):
            def __init__(self, phase: InitializationPhase, func: Callable):
                super().__init__(phase)
                self._func = func
            
            def initialize(self, context: InitializationContext) -> PhaseResult:
                return self._func(context)
        
        self.register(FunctionInitializer(phase, init_func))
    
    def get_initializer(self, phase: InitializationPhase) -> Optional[Initializer]:
        """Get initializer for specified phase"""
        with self._lock:
            return self._initializers.get(phase)
    
    def get_all_phases(self) -> List[InitializationPhase]:
        """Get all registered phases"""
        with self._lock:
            return list(self._initializers.keys())
    
    def has_initializer(self, phase: InitializationPhase) -> bool:
        """Check if initializer exists for specified phase"""
        with self._lock:
            return phase in self._initializers
    
    def clear(self):
        """Clear registry"""
        with self._lock:
            self._initializers.clear()
    
    def execute_phase(self, phase: InitializationPhase, 
                     context: InitializationContext) -> PhaseResult:
        """Execute initialization for specified phase"""
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


def get_global_registry() -> InitializerRegistry:
    """获取全局初始化器注册表（存储于 ApplicationContext）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if ctx.initializer_registry is None:
        ctx.initializer_registry = InitializerRegistry()
    return ctx.initializer_registry


def register_initializer(initializer: Initializer):
    """注册初始化器到全局注册表"""
    get_global_registry().register(initializer)


def register_phase_function(phase: InitializationPhase,
                            init_func: Callable[[InitializationContext], PhaseResult]):
    """注册函数式初始化器到全局注册表"""
    get_global_registry().register_function(phase, init_func)