#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化上下文 - 保存初始化过程中的状态和数据
"""

import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .phases import InitializationPhase, PhaseResult


@dataclass
class InitializationContext:
    """
    初始化上下文
    
    保存初始化过程中的状态、数据和结果
    """
    
    # 基本信息
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # 当前状态
    current_phase: InitializationPhase = InitializationPhase.PREPARING
    completed_phases: List[InitializationPhase] = field(default_factory=list)
    failed_phases: List[InitializationPhase] = field(default_factory=list)
    
    # 阶段结果
    phase_results: Dict[InitializationPhase, PhaseResult] = field(default_factory=dict)
    
    # 共享数据
    shared_data: Dict[str, Any] = field(default_factory=dict)
    
    # 配置信息
    settings: Optional[Any] = None
    custom_settings: Optional[Dict[str, Any]] = None
    
    # 错误信息
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # 线程安全
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    
    def set_current_phase(self, phase: InitializationPhase):
        """设置当前阶段"""
        with self._lock:
            self.current_phase = phase
    
    def mark_phase_completed(self, phase: InitializationPhase, result: PhaseResult):
        """标记阶段完成"""
        with self._lock:
            if result.success:
                self.completed_phases.append(phase)
            else:
                self.failed_phases.append(phase)
            
            self.phase_results[phase] = result
    
    def add_shared_data(self, key: str, value: Any):
        """添加共享数据"""
        with self._lock:
            self.shared_data[key] = value
    
    def get_shared_data(self, key: str, default=None):
        """获取共享数据"""
        with self._lock:
            return self.shared_data.get(key, default)
    
    def add_error(self, message: str):
        """添加错误信息"""
        with self._lock:
            self.errors.append(message)
    
    def add_warning(self, message: str):
        """添加警告信息"""
        with self._lock:
            self.warnings.append(message)
    
    def is_phase_completed(self, phase: InitializationPhase) -> bool:
        """检查阶段是否完成"""
        with self._lock:
            return phase in self.completed_phases
    
    def is_phase_failed(self, phase: InitializationPhase) -> bool:
        """检查阶段是否失败"""
        with self._lock:
            return phase in self.failed_phases
    
    def get_phase_result(self, phase: InitializationPhase) -> Optional[PhaseResult]:
        """获取阶段结果"""
        with self._lock:
            return self.phase_results.get(phase)
    
    def get_total_duration(self) -> float:
        """获取总耗时"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def get_phase_durations(self) -> Dict[InitializationPhase, float]:
        """获取各阶段耗时"""
        with self._lock:
            return {
                phase: result.duration 
                for phase, result in self.phase_results.items()
            }
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        with self._lock:
            total = len(self.completed_phases) + len(self.failed_phases)
            if total == 0:
                return 0.0
            return len(self.completed_phases) / total * 100
    
    def finish(self):
        """标记初始化完成"""
        with self._lock:
            self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        with self._lock:
            return {
                'start_time': self.start_time,
                'end_time': self.end_time,
                'total_duration': self.get_total_duration(),
                'current_phase': self.current_phase.value,
                'completed_phases': [p.value for p in self.completed_phases],
                'failed_phases': [p.value for p in self.failed_phases],
                'success_rate': self.get_success_rate(),
                'error_count': len(self.errors),
                'warning_count': len(self.warnings),
                'phase_durations': {
                    p.value: duration 
                    for p, duration in self.get_phase_durations().items()
                }
            }