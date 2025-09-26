#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
核心初始化器 - 协调整个初始化过程
"""

import time
import threading
from typing import Optional, Any

from .context import InitializationContext  
from .phases import InitializationPhase, PhaseResult, get_execution_order, get_phase_definition
from .registry import get_global_registry, BaseInitializer, register_initializer
from .built_in import register_built_in_initializers


class CoreInitializer:
    """
    核心初始化器 - 协调整个框架的初始化过程
    
    职责：
    1. 管理初始化阶段的执行顺序
    2. 处理阶段间的依赖关系
    3. 提供统一的初始化入口
    4. 错误处理和降级策略
    """
    
    _instance: Optional['CoreInitializer'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'CoreInitializer':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CoreInitializer, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._context: Optional[InitializationContext] = None
        self._is_ready = False
        self._init_lock = threading.RLock()
        
        # 注册内置初始化器
        register_built_in_initializers()
        
        self._initialized = True
    
    @property
    def context(self) -> Optional[InitializationContext]:
        """获取初始化上下文"""
        return self._context
    
    @property  
    def is_ready(self) -> bool:
        """检查框架是否已准备就绪"""
        return self._is_ready
    
    def initialize(self, settings=None, **kwargs) -> Any:
        """
        执行框架初始化
        
        Args:
            settings: 配置对象
            **kwargs: 额外的配置参数
            
        Returns:
            初始化后的配置管理器
        """
        with self._init_lock:
            # 如果已经初始化完成，直接返回
            if self._is_ready and self._context and self._context.settings:
                return self._context.settings
            
            # 创建初始化上下文
            context = InitializationContext()
            context.custom_settings = kwargs
            self._context = context
            
            try:
                # 执行初始化阶段
                self._execute_initialization_phases(context)
                
                # 检查关键阶段是否完成
                if not context.is_phase_completed(InitializationPhase.SETTINGS):
                    raise RuntimeError("Settings initialization failed")
                
                self._is_ready = True
                context.finish()
                
                return context.settings
                
            except Exception as e:
                context.add_error(f"Framework initialization failed: {e}")
                context.finish()
                
                # 降级策略
                return self._fallback_initialization(settings, **kwargs)
    
    def _execute_initialization_phases(self, context: InitializationContext):
        """执行初始化阶段"""
        registry = get_global_registry()
        execution_order = get_execution_order()
        
        # 只执行已注册的阶段
        registered_phases = set(registry.get_all_phases())
        
        for phase in execution_order:
            if phase == InitializationPhase.ERROR:
                continue
                
            # 只执行已注册的阶段
            if phase not in registered_phases:
                continue
                
            context.set_current_phase(phase)
            
            # 检查依赖关系
            if not self._check_dependencies(phase, context):
                phase_def = get_phase_definition(phase)
                if not (phase_def and phase_def.optional):
                    raise RuntimeError(f"Dependencies not satisfied for phase {phase}")
                else:
                    # 可选阶段，跳过
                    continue
            
            # 执行阶段
            start_time = time.time()
            try:
                result = registry.execute_phase(phase, context)
                result.duration = time.time() - start_time
                
                context.mark_phase_completed(phase, result)
                
                if not result.success and not self._is_phase_optional(phase):
                    raise RuntimeError(f"Phase {phase} failed: {result.error}")
                    
            except Exception as e:
                duration = time.time() - start_time
                result = PhaseResult(
                    phase=phase,
                    success=False,
                    duration=duration,
                    error=e
                )
                context.mark_phase_completed(phase, result)
                
                if not self._is_phase_optional(phase):
                    raise
    
    def _check_dependencies(self, phase: InitializationPhase, 
                          context: InitializationContext) -> bool:
        """检查阶段依赖关系"""
        phase_def = get_phase_definition(phase)
        if not phase_def:
            return True
        
        for dependency in phase_def.dependencies:
            if not context.is_phase_completed(dependency):
                return False
        
        return True
    
    def _is_phase_optional(self, phase: InitializationPhase) -> bool:
        """检查阶段是否可选"""
        phase_def = get_phase_definition(phase)
        return phase_def.optional if phase_def else False
    
    def _fallback_initialization(self, settings=None, **kwargs):
        """降级初始化策略"""
        try:
            # 尝试创建基本的配置管理器
            from crawlo.settings.setting_manager import SettingManager
            
            if settings:
                return settings
            else:
                fallback_settings = SettingManager()
                if kwargs:
                    fallback_settings.update_attributes(kwargs)
                return fallback_settings
                
        except Exception:
            # 如果连降级都失败，返回None
            return None
    
    def reset(self):
        """重置初始化状态（主要用于测试）"""
        with self._init_lock:
            self._context = None
            self._is_ready = False