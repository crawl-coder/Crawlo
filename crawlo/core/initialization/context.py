#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
初始化上下文
============
InitializationContext — 保存初始化过程中的状态和数据。

线程安全（RLock 保护），记录阶段进度、共享数据、错误/警告等。
"""
import threading
import time as _time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from crawlo.core.initialization.phases import InitializationPhase, PhaseResult


@dataclass
class InitializationContext:
    """初始化上下文 — 保存初始化过程中的状态和数据"""

    start_time: float = field(default_factory=_time.time)
    end_time: Optional[float] = None
    current_phase: InitializationPhase = InitializationPhase.PREPARING
    completed_phases: List[InitializationPhase] = field(default_factory=list)
    failed_phases: List[InitializationPhase] = field(default_factory=list)
    phase_results: Dict[InitializationPhase, PhaseResult] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    settings: Optional[Any] = None
    custom_settings: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def set_current_phase(self, phase: InitializationPhase):
        with self._lock:
            self.current_phase = phase

    def mark_phase_completed(self, phase: InitializationPhase, result: PhaseResult):
        with self._lock:
            if result.success:
                self.completed_phases.append(phase)
            else:
                self.failed_phases.append(phase)
            self.phase_results[phase] = result

    def add_shared_data(self, key: str, value: Any):
        with self._lock:
            self.shared_data[key] = value

    def get_shared_data(self, key: str, default=None):
        with self._lock:
            return self.shared_data.get(key, default)

    def add_error(self, message: str):
        with self._lock:
            self.errors.append(message)

    def add_warning(self, message: str):
        with self._lock:
            self.warnings.append(message)

    def is_phase_completed(self, phase: InitializationPhase) -> bool:
        with self._lock:
            return phase in self.completed_phases

    def is_phase_failed(self, phase: InitializationPhase) -> bool:
        with self._lock:
            return phase in self.failed_phases

    def get_phase_result(self, phase: InitializationPhase) -> Optional[PhaseResult]:
        with self._lock:
            return self.phase_results.get(phase)

    def get_total_duration(self) -> float:
        end = self.end_time or _time.time()
        return end - self.start_time

    def get_phase_durations(self) -> Dict[InitializationPhase, float]:
        with self._lock:
            return {
                phase: result.duration
                for phase, result in self.phase_results.items()
            }

    def get_success_rate(self) -> float:
        with self._lock:
            total = len(self.completed_phases) + len(self.failed_phases)
            if total == 0:
                return 0.0
            return len(self.completed_phases) / total * 100

    def finish(self):
        with self._lock:
            self.end_time = _time.time()

    def to_dict(self) -> Dict[str, Any]:
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


__all__ = ["InitializationContext"]
